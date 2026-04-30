from __future__ import annotations

from datetime import datetime

from services.config import config
from services.image_tags_service import load_tags
from services.thumbnail_service import cleanup_orphaned_thumbnails, get_image_dimensions


def _image_items(start_date: str = "", end_date: str = "") -> list[dict[str, object]]:
    items = []
    root = config.images_dir
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/")
        day = "-".join(parts[:3]) if len(parts) >= 4 else datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        if start_date and day < start_date:
            continue
        if end_date and day > end_date:
            continue
        items.append({"path": rel, "name": path.name, "date": day, "size": path.stat().st_size, "created_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")})
    items.sort(key=lambda item: str(item["created_at"]), reverse=True)
    return items


def list_images(base_url: str, start_date: str = "", end_date: str = "") -> dict[str, object]:
    config.cleanup_old_images()
    cleanup_orphaned_thumbnails()
    all_tags = load_tags()
    items = []
    root = config.images_dir
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/")
        day = "-".join(parts[:3]) if len(parts) >= 4 else datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        if start_date and day < start_date:
            continue
        if end_date and day > end_date:
            continue
        dims = get_image_dimensions(rel)
        items.append({
            "rel": rel,
            "name": path.name,
            "date": day,
            "size": path.stat().st_size,
            "url": f"{base_url.rstrip('/')}/images/{rel}",
            "thumbnail_url": f"{base_url.rstrip('/')}/image-thumbnails/{rel}",
            "width": dims[0] if dims else None,
            "height": dims[1] if dims else None,
            "tags": all_tags.get(rel, []),
            "created_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    items.sort(key=lambda item: str(item["created_at"]), reverse=True)
    groups: dict[str, list[dict[str, object]]] = {}
    for item in items:
        groups.setdefault(str(item["date"]), []).append(item)
    return {"items": items, "groups": [{"date": key, "items": value} for key, value in groups.items()]}


def delete_images(paths: list[str] | None = None, start_date: str = "", end_date: str = "", all_matching: bool = False) -> dict[str, int]:
    root = config.images_dir.resolve()
    targets = [str(item["path"]) for item in _image_items(start_date, end_date)] if all_matching else (paths or [])
    removed = 0
    for item in targets:
        path = (root / item).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.is_file():
            path.unlink()
            removed += 1
    for path in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()
    return {"removed": removed}
