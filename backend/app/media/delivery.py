"""HTTP delivery for stable /media paths backed by local files or S3 redirects."""

from __future__ import annotations

import logging
from pathlib import Path

import anyio
from fastapi import HTTPException, Response, status
from fastapi.responses import FileResponse, RedirectResponse

from app.config import Settings
from app.media.object_keys import MediaObjectKeyError, public_object_key
from app.media.storage import ObjectStorage, ObjectStorageError

logger = logging.getLogger(__name__)
LOCAL_FALLBACK_HEADER = "X-Fitician-Media-Fallback"


def local_public_media_path(settings: Settings, media_path: str) -> Path:
    try:
        key = public_object_key(f"{settings.media_public_path.rstrip('/')}/{media_path}")
    except MediaObjectKeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    path = (settings.media_root / key.removeprefix("public/")).resolve()
    root = settings.media_root.resolve()
    if not path.is_relative_to(root):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return path


async def deliver_public_media(
    media_path: str,
    *,
    settings: Settings,
    storage: ObjectStorage | None,
) -> Response:
    try:
        key = public_object_key(f"{settings.media_public_path.rstrip('/')}/{media_path}")
    except MediaObjectKeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    storage_error: ObjectStorageError | None = None
    if settings.media_storage_backend == "s3":
        if storage is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            remote = await anyio.to_thread.run_sync(storage.head, key)
            if remote is not None:
                return RedirectResponse(
                    storage.public_url(key), status_code=status.HTTP_307_TEMPORARY_REDIRECT
                )
        except ObjectStorageError as error:
            storage_error = error
        logger.warning(
            "Public media S3 delivery fell back to local storage",
            extra={
                "object_key": key,
                "error_type": type(storage_error).__name__ if storage_error else "NotFound",
            },
        )

    local_path = local_public_media_path(settings, media_path)
    if local_path.is_file():
        headers = (
            {LOCAL_FALLBACK_HEADER: "local"} if settings.media_storage_backend == "s3" else None
        )
        return FileResponse(local_path, headers=headers)
    if storage_error is not None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
