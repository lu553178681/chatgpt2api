from __future__ import annotations

import abc
from pathlib import Path
from typing import Any


class ImageStorageBackend(abc.ABC):
    """Abstract base class for image storage backends."""

    @abc.abstractmethod
    def save(self, image_data: bytes, relative_path: str) -> str:
        """Save image data and return the public URL.

        Args:
            image_data: Raw image bytes.
            relative_path: Relative path like "2026/05/01/1714521234_abc.png".

        Returns:
            Public URL for accessing the image.
        """

    @abc.abstractmethod
    def delete(self, relative_path: str) -> bool:
        """Delete an image by relative path. Returns True if deleted."""

    @abc.abstractmethod
    def list_images(self) -> list[dict[str, Any]]:
        """List all images. Returns list of dicts with at least 'rel' and 'size' keys."""

    @abc.abstractmethod
    def read_bytes(self, relative_path: str) -> bytes | None:
        """Read image bytes by relative path. Returns None if not found."""

    @abc.abstractmethod
    def get_url(self, relative_path: str) -> str:
        """Get the public URL for a relative path."""

    @abc.abstractmethod
    def get_backend_info(self) -> dict[str, Any]:
        """Return backend info for diagnostics."""
