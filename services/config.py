from __future__ import annotations

from dataclasses import dataclass
import json
import os
import sys
from pathlib import Path
import time

from services.image_storage.base import ImageStorageBackend
from services.storage.base import StorageBackend

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = BASE_DIR / "config.json"
VERSION_FILE = BASE_DIR / "VERSION"


@dataclass(frozen=True)
class LoadedSettings:
    auth_key: str
    refresh_account_interval_minute: int


def _normalize_auth_key(value: object) -> str:
    return str(value or "").strip()


def _is_invalid_auth_key(value: object) -> bool:
    return _normalize_auth_key(value) == ""


def _read_json_object(path: Path, *, name: str) -> dict[str, object]:
    if not path.exists():
        return {}
    if path.is_dir():
        print(
            f"Warning: {name} at '{path}' is a directory, ignoring it and falling back to other configuration sources.",
            file=sys.stderr,
        )
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_settings() -> LoadedSettings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_config = _read_json_object(CONFIG_FILE, name="config.json")
    auth_key = _normalize_auth_key(os.getenv("CHATGPT2API_AUTH_KEY") or raw_config.get("auth-key"))
    if _is_invalid_auth_key(auth_key):
        raise ValueError(
            "❌ auth-key 未设置！\n"
            "请在环境变量 CHATGPT2API_AUTH_KEY 中设置，或者在 config.json 中填写 auth-key。"
        )

    try:
        refresh_interval = int(raw_config.get("refresh_account_interval_minute", 5))
    except (TypeError, ValueError):
        refresh_interval = 5

    return LoadedSettings(
        auth_key=auth_key,
        refresh_account_interval_minute=refresh_interval,
    )


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()
        self._storage_backend: StorageBackend | None = None
        if _is_invalid_auth_key(self.auth_key):
            raise ValueError(
                "❌ auth-key 未设置！\n"
                "请按以下任意一种方式解决：\n"
                "1. 在 Render 的 Environment 变量中添加：\n"
                "   CHATGPT2API_AUTH_KEY = your_real_auth_key\n"
                "2. 或者在 config.json 中填写：\n"
                '   "auth-key": "your_real_auth_key"'
            )

    def _load(self) -> dict[str, object]:
        return _read_json_object(self.path, name="config.json")

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @property
    def auth_key(self) -> str:
        return _normalize_auth_key(os.getenv("CHATGPT2API_AUTH_KEY") or self.data.get("auth-key"))

    @property
    def accounts_file(self) -> Path:
        return DATA_DIR / "accounts.json"

    @property
    def refresh_account_interval_minute(self) -> int:
        try:
            return int(self.data.get("refresh_account_interval_minute", 5))
        except (TypeError, ValueError):
            return 5

    @property
    def image_retention_days(self) -> int:
        try:
            return max(1, int(self.data.get("image_retention_days", 30)))
        except (TypeError, ValueError):
            return 30

    @property
    def auto_remove_invalid_accounts(self) -> bool:
        value = self.data.get("auto_remove_invalid_accounts", False)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def upload_max_file_size_mb(self) -> int:
        try:
            value = self.data.get("upload_max_file_size_mb", 5)
            return max(0, int(value))
        except (TypeError, ValueError):
            return 5

    @property
    def task_timeout_seconds(self) -> int:
        try:
            return max(10, int(self.data.get("task_timeout_seconds", 120)))
        except (TypeError, ValueError):
            return 120

    @property
    def auto_remove_rate_limited_accounts(self) -> bool:
        value = self.data.get("auto_remove_rate_limited_accounts", False)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def log_levels(self) -> list[str]:
        levels = self.data.get("log_levels")
        if not isinstance(levels, list):
            return []
        allowed = {"debug", "info", "warning", "error"}
        return [level for item in levels if (level := str(item or "").strip().lower()) in allowed]

    @property
    def images_dir(self) -> Path:
        path = DATA_DIR / "images"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def thumbnail_dir(self) -> Path:
        path = DATA_DIR / "image-thumbnails"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cleanup_old_images(self) -> int:
        cutoff = time.time() - self.image_retention_days * 86400
        removed = 0
        for path in self.images_dir.rglob("*"):
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        for path in sorted((p for p in self.images_dir.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            try:
                path.rmdir()
            except OSError:
                pass
        if removed:
            from services.thumbnail_service import cleanup_orphaned_thumbnails
            cleanup_orphaned_thumbnails()
        return removed

    @property
    def base_url(self) -> str:
        return str(
            os.getenv("CHATGPT2API_BASE_URL")
            or self.data.get("base_url")
            or ""
        ).strip().rstrip("/")

    @property
    def app_version(self) -> str:
        try:
            value = VERSION_FILE.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return "0.0.0"
        return value or "0.0.0"

    def get(self) -> dict[str, object]:
        data = dict(self.data)
        data["refresh_account_interval_minute"] = self.refresh_account_interval_minute
        data["image_retention_days"] = self.image_retention_days
        data["task_timeout_seconds"] = self.task_timeout_seconds
        data["upload_max_file_size_mb"] = self.upload_max_file_size_mb
        data["image_storage_backend"] = self.image_storage_backend_type
        data["webdav_url"] = self.webdav_url
        data["webdav_public_url"] = self.webdav_public_url
        data["webdav_username"] = self.webdav_username
        data["webdav_base_path"] = self.webdav_base_path
        data["webdav_auth_type"] = self.webdav_auth_type
        data["auto_remove_invalid_accounts"] = self.auto_remove_invalid_accounts
        data["auto_remove_rate_limited_accounts"] = self.auto_remove_rate_limited_accounts
        data["log_levels"] = self.log_levels
        data.pop("auth-key", None)
        data.pop("webdav_password", None)
        return data

    def get_proxy_settings(self) -> str:
        return str(self.data.get("proxy") or "").strip()

    def update(self, data: dict[str, object]) -> dict[str, object]:
        next_data = dict(self.data)
        next_data.update(dict(data or {}))
        self.data = next_data
        self._save()
        self.reset_image_storage()
        return self.get()

    def get_storage_backend(self) -> StorageBackend:
        """获取存储后端实例（单例）"""
        if self._storage_backend is None:
            from services.storage.factory import create_storage_backend
            self._storage_backend = create_storage_backend(DATA_DIR)
        return self._storage_backend

    # ── Image storage backend ──

    @property
    def image_storage_backend_type(self) -> str:
        return str(self.data.get("image_storage_backend") or "local").strip().lower()

    @property
    def webdav_url(self) -> str:
        return str(self.data.get("webdav_url") or "").strip()

    @property
    def webdav_public_url(self) -> str:
        return str(self.data.get("webdav_public_url") or "").strip()

    @property
    def webdav_username(self) -> str:
        return str(self.data.get("webdav_username") or "").strip()

    @property
    def webdav_password(self) -> str:
        return str(self.data.get("webdav_password") or "").strip()

    @property
    def webdav_base_path(self) -> str:
        return str(self.data.get("webdav_base_path") or "/images").strip()

    @property
    def webdav_auth_type(self) -> str:
        return str(self.data.get("webdav_auth_type") or "basic").strip().lower()

    _image_storage: ImageStorageBackend | None = None

    def get_image_storage(self) -> ImageStorageBackend:
        """获取图片存储后端实例（单例），配置变更后需重启"""
        if self._image_storage is None:
            from services.image_storage.factory import create_image_storage
            self._image_storage = create_image_storage(
                config_data=self.data,
                images_dir_str=str(self.images_dir),
                base_url=self.base_url,
                retention_days=self.image_retention_days,
            )
        return self._image_storage

    def reset_image_storage(self) -> None:
        """重置图片存储后端实例（配置变更后调用）"""
        self._image_storage = None


config = ConfigStore(CONFIG_FILE)
