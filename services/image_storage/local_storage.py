from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from services.image_storage.base import ImageStorageBackend


class LocalStorageBackend(ImageStorageBackend):
    """Local filesystem image storage (original behavior)."""

    def __init__(self, images_dir: Path, base_url: str, retention_days: int = 30):
        self.images_dir = images_dir
        self.base_url = base_url.rstrip("/")
        self.retention_days = retention_days
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def save(self, image_data: bytes, relative_path: str) -> str:
        file_path = self.images_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(image_data)
        return self.get_url(relative_path)

    def delete(self, relative_path: str) -> bool:
        file_path = (self.images_dir / relative_path).resolve()
        try:
            file_path.relative_to(self.images_dir.resolve())
        except ValueError:
            return False
        if file_path.is_file():
            file_path.unlink()
            return True
        return False

    def list_images(self) -> list[dict[str, Any]]:
        items = []
        for path in self.images_dir.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(self.images_dir).as_posix()
            items.append({
                "rel": rel,
                "name": path.name,
                "size": path.stat().st_size,
                "created_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
        return items

    def read_bytes(self, relative_path: str) -> bytes | None:
        file_path = self.images_dir / relative_path
        if file_path.is_file():
            return file_path.read_bytes()
        return None

    def get_url(self, relative_path: str) -> str:
        return f"{self.base_url}/images/{relative_path}"

    def cleanup_old(self) -> int:
        cutoff = time.time() - self.retention_days * 86400
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
        return removed

    def get_backend_info(self) -> dict[str, Any]:
        return {"type": "local", "path": str(self.images_dir), "base_url": self.base_url}
