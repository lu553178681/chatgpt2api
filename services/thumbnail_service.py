from __future__ import annotations

import io
import time
from pathlib import Path

from PIL import Image

from services.config import config

THUMBNAIL_MAX_SIZE = (320, 320)


def _thumbnail_path(original_rel: str) -> Path:
    """根据原图相对路径（如 2026/04/30/foo.png）返回缩略图缓存路径。"""
    return config.thumbnail_dir / original_rel


def _read_image_bytes(original_rel: str) -> bytes | None:
    """读取原图字节，支持本地和远程存储后端。"""
    from services.image_storage.local_storage import LocalStorageBackend

    storage = config.get_image_storage()
    if isinstance(storage, LocalStorageBackend):
        original = config.images_dir / original_rel
        if original.is_file():
            return original.read_bytes()
        return None
    return storage.read_bytes(original_rel)


def _get_source_mtime(original_rel: str) -> float:
    """获取原图 mtime，本地文件用文件系统 mtime，远程用缩略图 mtime 作为基准。"""
    from services.image_storage.local_storage import LocalStorageBackend

    storage = config.get_image_storage()
    if isinstance(storage, LocalStorageBackend):
        original = config.images_dir / original_rel
        return original.stat().st_mtime if original.is_file() else 0
    # 远程文件：如果缩略图已存在则认为缓存有效
    thumb = _thumbnail_path(original_rel)
    return thumb.stat().st_mtime if thumb.is_file() else 0


def get_thumbnail(original_rel: str) -> Path | None:
    """懒生成缩略图，返回缩略图文件路径。

    原图不存在时返回 None。
    缓存命中条件：缩略图文件存在且 mtime >= 原图 mtime（本地）或缩略图已存在（远程）。
    """
    source_mtime = _get_source_mtime(original_rel)
    thumb = _thumbnail_path(original_rel)

    # 本地文件：检查原图是否存在
    from services.image_storage.local_storage import LocalStorageBackend
    storage = config.get_image_storage()
    if isinstance(storage, LocalStorageBackend):
        original = config.images_dir / original_rel
        if not original.is_file():
            return None
        if thumb.is_file() and thumb.stat().st_mtime >= source_mtime:
            return thumb

    # 远程文件：缩略图已存在则直接返回
    if thumb.is_file():
        return thumb

    # 读取原图字节
    image_bytes = _read_image_bytes(original_rel)
    if not image_bytes:
        return None

    thumb.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.thumbnail(THUMBNAIL_MAX_SIZE, Image.LANCZOS)
            img.save(thumb, "PNG")
    except Exception:
        return None
    return thumb


def get_image_dimensions(original_rel: str) -> tuple[int, int] | None:
    """读取原图尺寸，失败时返回 None。支持本地和远程存储。"""
    image_bytes = _read_image_bytes(original_rel)
    if not image_bytes:
        return None
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            return img.size
    except Exception:
        return None


def delete_thumbnail(original_rel: str) -> None:
    """删除单个缩略图缓存。"""
    thumb = _thumbnail_path(original_rel)
    if thumb.is_file():
        thumb.unlink(missing_ok=True)


def cleanup_orphaned_thumbnails() -> int:
    """删除没有对应原图的缩略图，返回删除数量。"""
    thumb_dir = config.thumbnail_dir
    if not thumb_dir.exists():
        return 0

    # 获取当前存储后端中的所有图片列表
    try:
        storage = config.get_image_storage()
        existing_rels = {str(item["rel"]) for item in storage.list_images()}
    except Exception:
        existing_rels = set()

    removed = 0
    for thumb in thumb_dir.rglob("*"):
        if not thumb.is_file():
            continue
        rel = thumb.relative_to(thumb_dir).as_posix()
        if rel not in existing_rels:
            thumb.unlink(missing_ok=True)
            removed += 1
    for d in sorted(
        (p for p in thumb_dir.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        try:
            d.rmdir()
        except OSError:
            pass
    return removed
