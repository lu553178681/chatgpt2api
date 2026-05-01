from __future__ import annotations

from datetime import datetime
from pathlib import Path

from services.config import config
from services.image_tags_service import load_tags
from services.image_storage.local_storage import LocalStorageBackend
from services.thumbnail_service import cleanup_orphaned_thumbnails, get_image_dimensions


def _extract_date(rel: str, created_at: str = "") -> str:
    parts = rel.split("/")
    if len(parts) >= 4:
        return "-".join(parts[:3])
    if created_at:
        return created_at[:10]
    return ""


def list_images(base_url: str, start_date: str = "", end_date: str = "") -> dict[str, object]:
    storage = config.get_image_storage()
    if isinstance(storage, LocalStorageBackend):
        storage.cleanup_old()
    cleanup_orphaned_thumbnails()

    all_tags = load_tags()
    raw_items = storage.list_images()
    items = []
    for entry in raw_items:
        rel = str(entry.get("rel", ""))
        name = str(entry.get("name", ""))
        size = int(entry.get("size", 0))
        created_at = str(entry.get("created_at", ""))
        day = _extract_date(rel, created_at)
        if start_date and day < start_date:
            continue
        if end_date and day > end_date:
            continue
        dims = get_image_dimensions(rel)
        items.append({
            "rel": rel,
            "name": name,
            "date": day,
            "size": size,
            "url": storage.get_url(rel),
            "thumbnail_url": f"{base_url.rstrip('/')}/image-thumbnails/{rel}",
            "width": dims[0] if dims else None,
            "height": dims[1] if dims else None,
            "tags": all_tags.get(rel, []),
            "created_at": created_at,
        })
    items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    groups: dict[str, list[dict[str, object]]] = {}
    for item in items:
        groups.setdefault(str(item["date"]), []).append(item)
    return {"items": items, "groups": [{"date": key, "items": value} for key, value in groups.items()]}


def delete_images(paths: list[str] | None = None, start_date: str = "", end_date: str = "", all_matching: bool = False) -> dict[str, int]:
    storage = config.get_image_storage()
    if all_matching:
        raw_items = storage.list_images()
        targets = [
            str(item["rel"]) for item in raw_items
            if _extract_date(str(item.get("rel", "")), str(item.get("created_at", ""))) >= start_date
            and _extract_date(str(item.get("rel", "")), str(item.get("created_at", ""))) <= end_date
        ] if start_date or end_date else [str(item["rel"]) for item in raw_items]
    else:
        targets = paths or []

    removed = 0
    for rel in targets:
        rel = rel.strip().lstrip("/")
        if not rel:
            continue
        if storage.delete(rel):
            from services.thumbnail_service import delete_thumbnail
            from services.image_tags_service import remove_tags
            delete_thumbnail(rel)
            remove_tags(rel)
            removed += 1
    return {"removed": removed}
