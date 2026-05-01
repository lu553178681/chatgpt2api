from __future__ import annotations

from typing import Any

from services.image_storage.base import ImageStorageBackend


def create_image_storage(config_data: dict[str, Any], images_dir_str: str, base_url: str, retention_days: int) -> ImageStorageBackend:
    backend_type = str(config_data.get("image_storage_backend") or "local").strip().lower()

    if backend_type == "webdav":
        from services.image_storage.webdav_storage import WebDAVStorageBackend

        webdav_url = str(config_data.get("webdav_url") or "").strip()
        if not webdav_url:
            raise ValueError("webdav_url is required when image_storage_backend is 'webdav'")

        return WebDAVStorageBackend(
            webdav_url=webdav_url,
            public_url=str(config_data.get("webdav_public_url") or "").strip() or None,
            username=str(config_data.get("webdav_username") or "").strip(),
            password=str(config_data.get("webdav_password") or "").strip(),
            base_path=str(config_data.get("webdav_base_path") or "/images").strip(),
            auth_type=str(config_data.get("webdav_auth_type") or "basic").strip().lower(),
        )

    from pathlib import Path
    from services.image_storage.local_storage import LocalStorageBackend

    return LocalStorageBackend(
        images_dir=Path(images_dir_str),
        base_url=base_url,
        retention_days=retention_days,
    )
