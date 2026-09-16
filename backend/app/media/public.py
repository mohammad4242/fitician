"""Public media resolution with observable local fallback."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings
from app.media.object_keys import public_object_key
from app.media.storage import ObjectNotFoundError, ObjectStorage, ObjectStorageError

logger = logging.getLogger(__name__)


class PublicMediaReader:
    def __init__(self, settings: Settings, storage: ObjectStorage | None = None) -> None:
        self._settings = settings
        self._storage = storage
        self._cache: dict[str, bytes | None] = {}

    def _local_path(self, key: str) -> Path:
        relative = key.removeprefix("public/")
        path = (self._settings.media_root / relative).resolve()
        root = self._settings.media_root.resolve()
        if not path.is_relative_to(root):
            raise ObjectStorageError("Public media path escapes local storage")
        return path

    def _read_local(self, key: str) -> bytes | None:
        path = self._local_path(key)
        try:
            return path.read_bytes() if path.is_file() else None
        except OSError as error:
            raise ObjectStorageError("Local public media read failed") from error

    def read_public_path(self, public_path: str) -> bytes | None:
        key = public_object_key(public_path)
        if key in self._cache:
            return self._cache[key]
        content: bytes | None = None
        if self._settings.media_storage_backend == "s3":
            if self._storage is None:
                raise ObjectStorageError("S3 public media storage is not configured")
            try:
                content = self._storage.read(key)
            except (ObjectNotFoundError, ObjectStorageError) as error:
                logger.warning(
                    "Public media S3 read failed; using local fallback",
                    extra={"object_key": key, "error_type": type(error).__name__},
                )
        if content is None:
            content = self._read_local(key)
        self._cache[key] = content
        return content
