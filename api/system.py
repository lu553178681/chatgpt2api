from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from api.support import require_admin, require_identity, resolve_image_base_url
from services.config import config
from services.image_service import delete_images, list_images
from services.image_tags_service import get_all_tags, remove_tags, set_tags
from services.log_service import log_service
from services.proxy_service import test_proxy
from services.thumbnail_service import delete_thumbnail, get_thumbnail


class SettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")


class ProxyTestRequest(BaseModel):
    url: str = ""


class ImageDeleteRequest(BaseModel):
    paths: list[str] = []
    start_date: str = ""
    end_date: str = ""
    all_matching: bool = False


class ImageTagsRequest(BaseModel):
    path: str
    tags: list[str]


def create_router(app_version: str) -> APIRouter:
    router = APIRouter()

    @router.post("/auth/login")
    async def login(authorization: str | None = Header(default=None)):
        identity = require_identity(authorization)
        return {
            "ok": True,
            "version": app_version,
            "role": identity.get("role"),
            "subject_id": identity.get("id"),
            "name": identity.get("name"),
        }

    @router.get("/version")
    async def get_version():
        return {"version": app_version}

    @router.get("/api/settings")
    async def get_settings(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"config": config.get()}

    @router.post("/api/settings")
    async def save_settings(body: SettingsUpdateRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"config": config.update(body.model_dump(mode="python"))}

    @router.get("/api/images")
    async def get_images(request: Request, start_date: str = "", end_date: str = "", authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return list_images(resolve_image_base_url(request), start_date=start_date.strip(), end_date=end_date.strip())

    @router.post("/api/images/delete")
    async def delete_images_endpoint(body: ImageDeleteRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return delete_images(body.paths, start_date=body.start_date.strip(), end_date=end_date.strip(), all_matching=body.all_matching)

    @router.get("/api/logs")
    async def get_logs(type: str = "", start_date: str = "", end_date: str = "", authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"items": log_service.list(type=type.strip(), start_date=start_date.strip(), end_date=end_date.strip())}

    @router.post("/api/proxy/test")
    async def test_proxy_endpoint(body: ProxyTestRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        candidate = (body.url or "").strip() or config.get_proxy_settings()
        if not candidate:
            raise HTTPException(status_code=400, detail={"error": "proxy url is required"})
        return {"result": await run_in_threadpool(test_proxy, candidate)}

    @router.get("/api/storage/info")
    async def get_storage_info(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        storage = config.get_storage_backend()
        return {
            "backend": storage.get_backend_info(),
            "health": storage.health_check(),
        }

    @router.delete("/api/images")
    async def delete_images_single(body: ImageDeleteRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        image_storage = config.get_image_storage()
        removed = 0
        for rel in body.paths:
            rel = rel.strip().lstrip("/")
            if not rel:
                continue
            if image_storage.delete(rel):
                delete_thumbnail(rel)
                remove_tags(rel)
                removed += 1
        return {"removed": removed}

    @router.get("/api/images/tags")
    async def list_image_tags(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"tags": get_all_tags()}

    @router.post("/api/images/tags")
    async def update_image_tags(body: ImageTagsRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        rel = body.path.strip().lstrip("/")
        if not rel:
            raise HTTPException(status_code=400, detail={"error": "path is required"})
        tags = set_tags(rel, body.tags)
        return {"ok": True, "tags": tags}

    @router.get("/image-thumbnails/{image_path:path}")
    async def get_image_thumbnail(image_path: str):
        thumb = await run_in_threadpool(get_thumbnail, image_path)
        if thumb is None:
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(thumb, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

    return router
