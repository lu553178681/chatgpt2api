from __future__ import annotations

import time
from pathlib import Path

from PIL import Image

from services.config import config

THUMBNAIL_MAX_SIZE = (320, 320)


def _thumbnail_path(original_rel: str) -> Path:
    """根据原图相对路径（如 2026/04/30/foo.png）返回缩略图缓存路径。"""
    return config.thumbnail_dir / original_rel


def get_thumbnail(original_rel: str) -> Path | None:
    """懒生成缩略图，返回缩略图文件路径。

    原图不存在时返回 None。
    缓存命中条件：缩略图文件存在且 mtime >= 原图 mtime。
    """
    original = config.images_dir / original_rel
    if not original.is_file():
        return None

    thumb = _thumbnail_path(original_rel)
    if thumb.is_file() and thumb.stat().st_mtime >= original.stat().st_mtime:
        return thumb

    thumb.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(original) as img:
            img.thumbnail(THUMBNAIL_MAX_SIZE, Image.LANCZOS)
            img.save(thumb, "PNG")
    except Exception:
        return None
    return thumb


def get_image_dimensions(original_rel: str) -> tuple[int, int] | None:
    """读取原图尺寸，失败时返回 None。"""
    original = config.images_dir / original_rel
    if not original.is_file():
        return None
    try:
        with Image.open(original) as img:
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
    images_dir = config.images_dir
    thumb_dir = config.thumbnail_dir
    if not thumb_dir.exists():
        return 0
    removed = 0
    for thumb in thumb_dir.rglob("*"):
        if not thumb.is_file():
            continue
        rel = thumb.relative_to(thumb_dir)
        original = images_dir / rel
        if not original.is_file():
            thumb.unlink(missing_ok=True)
            removed += 1
    # 清理空目录
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
