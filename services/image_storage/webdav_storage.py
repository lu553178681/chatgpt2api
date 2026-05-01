from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from services.image_storage.base import ImageStorageBackend


class WebDAVStorageBackend(ImageStorageBackend):
    """WebDAV image storage backend."""

    def __init__(
        self,
        webdav_url: str,
        public_url: str | None = None,
        username: str = "",
        password: str = "",
        base_path: str = "/images",
        auth_type: str = "basic",
    ):
        self.webdav_url = webdav_url.rstrip("/")
        self.public_url = (public_url or webdav_url).rstrip("/")
        self.base_path = "/" + base_path.strip("/")
        self.username = username
        self.password = password
        self.auth_type = auth_type
        self._session = requests.Session()
        if username:
            if auth_type == "digest":
                self._session.auth = HTTPDigestAuth(username, password)
            else:
                self._session.auth = HTTPBasicAuth(username, password)
        self._session.timeout = 30

    def _webdav_path(self, relative_path: str) -> str:
        return f"{self.base_path}/{relative_path}"

    def _webdav_url(self, relative_path: str) -> str:
        encoded = "/".join(quote(part, safe="") for part in self._webdav_path(relative_path).split("/"))
        return f"{self.webdav_url}{encoded}"

    def _ensure_dirs(self, path: str) -> None:
        parts = path.strip("/").split("/")
        current = ""
        for part in parts[:-1]:
            current += "/" + part
            url = f"{self.webdav_url('/')}".rsplit("/", 1)[0] + current + "/"
            try:
                self._session.request("MKCOL", url)
            except Exception:
                pass

    def save(self, image_data: bytes, relative_path: str) -> str:
        url = self._webdav_url(relative_path)
        self._ensure_dirs(self._webdav_path(relative_path))
        resp = self._session.put(url, data=image_data, headers={"Content-Type": "image/png"})
        resp.raise_for_status()
        return self.get_url(relative_path)

    def delete(self, relative_path: str) -> bool:
        url = self._webdav_url(relative_path)
        resp = self._session.request("DELETE", url)
        return resp.status_code in (200, 201, 204, 404)

    def list_images(self) -> list[dict[str, Any]]:
        items = []
        self._list_recursive(self.base_path + "/", items, depth=0)
        return items

    def _list_recursive(self, path: str, items: list[dict[str, Any]], depth: int) -> None:
        if depth > 10:
            return
        url = f"{self.webdav_url('/')}".rsplit("/", 1)[0] + path
        headers = {"Depth": "1", "Content-Type": "application/xml"}
        body = '<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:allprop/></d:propfind>'
        try:
            resp = self._session.request("PROPFIND", url, headers=headers, data=body)
        except Exception:
            return
        if resp.status_code != 207:
            return
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            return
        ns = {"d": "DAV:"}
        base_path = path.rstrip("/")
        for response in root.findall(".//d:response", ns):
            href_el = response.find("d:href", ns)
            if href_el is None or not href_el.text:
                continue
            href = href_el.text
            if href.endswith("/"):
                continue
            rel_url = href
            if rel_url.startswith(self.webdav_url("/").rsplit("/", 1)[0]):
                rel_url = rel_url[len(self.webdav_url("/").rsplit("/", 1)[0]):]
            if not rel_url.startswith(self.base_path):
                continue
            rel = rel_url[len(self.base_path):].lstrip("/")
            if not rel:
                continue
            name = Path(rel).name
            size_el = response.find(".//d:getcontentlength", ns)
            size = int(size_el.text) if size_el is not None and size_el.text else 0
            mod_el = response.find(".//d:getlastmodified", ns)
            created_at = ""
            if mod_el is not None and mod_el.text:
                try:
                    dt = datetime.strptime(mod_el.text, "%a, %d %b %Y %H:%M:%S %Z")
                    created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    created_at = mod_el.text
            items.append({"rel": rel, "name": name, "size": size, "created_at": created_at})

    def read_bytes(self, relative_path: str) -> bytes | None:
        url = self._webdav_url(relative_path)
        try:
            resp = self._session.get(url)
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
        return None

    def get_url(self, relative_path: str) -> str:
        encoded = "/".join(quote(part, safe="") for part in relative_path.split("/"))
        return f"{self.public_url}{self.base_path}/{encoded}"

    def get_backend_info(self) -> dict[str, Any]:
        return {
            "type": "webdav",
            "webdav_url": self.webdav_url,
            "public_url": self.public_url,
            "base_path": self.base_path,
            "username": self.username or "(anonymous)",
        }
