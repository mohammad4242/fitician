from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings
from app.exercises.enums import MediaType
from app.exercises.media_storage import (
    ExerciseMediaStorageError,
    ensure_exercise_video_poster,
    publish_exercise_media,
)
from app.media.factory import build_s3_storage
from app.media.object_keys import MediaObjectKeyError, public_object_key
from app.media.storage import ObjectStorage, ObjectStorageError, sha256_file

logger = logging.getLogger(__name__)

ALLOWED_MEDIA: dict[str, tuple[str, MediaType]] = {
    ".gif": ("image/gif", MediaType.GIF),
    ".jpg": ("image/jpeg", MediaType.IMAGE),
    ".jpeg": ("image/jpeg", MediaType.IMAGE),
    ".mp4": ("video/mp4", MediaType.VIDEO),
    ".webm": ("video/webm", MediaType.VIDEO),
}

ALLOWED_IMAGE_MEDIA: dict[str, str] = {
    ".gif": "image/gif",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class MediaValidationError(ValueError):
    pass


class MediaStorageError(RuntimeError):
    """Raised when a validated public-media storage operation fails."""


@dataclass(frozen=True)
class StoredMedia:
    public_path: str
    media_type: MediaType
    absolute_path: Path
    created: bool = True
    object_key: str | None = None
    storage: ObjectStorage | None = None
    remote_created: bool = False
    remote_object_keys: tuple[str, ...] = ()


def _validate_filename(filename: str | None) -> tuple[str, str, MediaType]:
    if not filename or "\x00" in filename or "/" in filename or "\\" in filename:
        raise MediaValidationError("Invalid media filename")
    extension = Path(filename).suffix.lower()
    allowed = ALLOWED_MEDIA.get(extension)
    if allowed is None:
        raise MediaValidationError("Only GIF, JPEG, MP4, and WebM files are supported")
    content_type, media_type = allowed
    return extension, content_type, media_type


def _signature_extension(header: bytes) -> str | None:
    if header.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return ".mp4"
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    return None


def _probe_video_duration(path: Path, settings: Settings) -> float:
    try:
        result = subprocess.run(
            [
                settings.ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=settings.ffprobe_timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise MediaValidationError("Video validation is temporarily unavailable") from error
    if result.returncode != 0:
        raise MediaValidationError("Video file could not be validated")
    try:
        duration = float(result.stdout.strip())
    except ValueError as error:
        raise MediaValidationError("Video duration could not be detected") from error
    if duration <= 0:
        raise MediaValidationError("Video duration must be positive")
    return duration


def _write_temporary(
    upload: UploadFile,
    settings: Settings,
    storage_root: Path | None = None,
    max_bytes: int | None = None,
) -> Path:
    target_root = storage_root or settings.media_root
    byte_limit = settings.media_max_bytes if max_bytes is None else max_bytes
    target_root.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target_root,
            prefix=".upload-",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            total = 0
            upload.file.seek(0)
            while chunk := upload.file.read(settings.media_read_chunk_bytes):
                total += len(chunk)
                if total > byte_limit:
                    raise MediaValidationError(f"Media file exceeds the {byte_limit} bytes limit")
                temporary.write(chunk)
        if total == 0:
            raise MediaValidationError("Media file cannot be empty")
        return temporary_path
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _publish_temporary(
    temporary_path: Path,
    extension: str,
    storage_root: Path,
) -> Path:
    for _ in range(10):
        final_path = storage_root / f"{uuid4().hex}{extension}"
        try:
            os.link(temporary_path, final_path)
        except FileExistsError:
            continue
        temporary_path.unlink()
        return final_path
    raise MediaValidationError("Could not allocate a unique media filename")


def _public_storage(settings: Settings) -> ObjectStorage | None:
    if settings.media_storage_backend != "s3":
        return None
    try:
        return build_s3_storage(settings)
    except (ObjectStorageError, ValueError) as error:
        raise MediaStorageError("Public media storage is not configured") from error


def _upload_public_object(
    storage: ObjectStorage,
    public_path: str,
    source: Path,
    *,
    content_type: str,
) -> tuple[str, bool]:
    try:
        key = public_object_key(public_path)
        digest = sha256_file(source)
    except (MediaObjectKeyError, OSError) as error:
        raise MediaStorageError("Public media upload failed") from error
    try:
        stored = storage.put_file(
            key,
            source,
            sha256=digest,
            content_type=content_type,
        )
    except ObjectStorageError as error:
        raise MediaStorageError("Public media upload failed") from error
    try:
        remote = storage.head(key)
    except ObjectStorageError as error:
        if stored.created:
            _cleanup_remote_objects(storage, (key,))
        raise MediaStorageError("Public media upload verification failed") from error
    if remote is None or remote.size_bytes != source.stat().st_size or remote.sha256 != digest:
        if stored.created:
            _cleanup_remote_objects(storage, (key,))
        raise MediaStorageError("Public media upload verification failed")
    return key, stored.created


def _cleanup_remote_objects(storage: ObjectStorage | None, keys: tuple[str, ...]) -> None:
    if storage is None:
        return
    for key in keys:
        try:
            storage.delete(key)
        except ObjectStorageError:
            logger.error("Unable to clean up public media object", extra={"object_key": key})


def store_upload(
    upload: UploadFile,
    settings: Settings,
    namespace: str,
) -> StoredMedia:
    extension, expected_content_type, media_type = _validate_filename(upload.filename)
    if upload.content_type != expected_content_type:
        raise MediaValidationError("Media MIME type does not match its extension")

    storage_root = settings.media_root
    temporary_path = _write_temporary(
        upload,
        settings,
        storage_root=storage_root,
        max_bytes=(
            settings.media_max_video_bytes
            if media_type is MediaType.VIDEO
            else settings.media_max_bytes
        ),
    )
    storage: ObjectStorage | None = None
    remote_keys: list[str] = []
    try:
        storage = _public_storage(settings)
        with temporary_path.open("rb") as file_handle:
            detected_extension = _signature_extension(file_handle.read(64))
        if detected_extension != extension and not (
            detected_extension == ".jpg" and extension == ".jpeg"
        ):
            raise MediaValidationError("Media signature does not match its extension")
        if media_type is MediaType.VIDEO:
            duration = _probe_video_duration(temporary_path, settings)
            if duration > settings.media_max_video_duration_seconds:
                limit = settings.media_max_video_duration_seconds
                raise MediaValidationError(f"Video duration exceeds the {limit:g} seconds limit")
        try:
            published = publish_exercise_media(
                temporary_path,
                settings=settings,
                namespace=namespace,
                extension=extension,
            )
        except ExerciseMediaStorageError as error:
            raise MediaValidationError(str(error)) from error
        if media_type is MediaType.VIDEO:
            try:
                poster = ensure_exercise_video_poster(published.public_path, settings=settings)
                if storage is not None and poster.absolute_path.is_file():
                    poster_key, poster_created = _upload_public_object(
                        storage,
                        poster.public_path,
                        poster.absolute_path,
                        content_type="image/webp",
                    )
                    if poster_created:
                        remote_keys.append(poster_key)
            except ExerciseMediaStorageError:
                logger.warning(
                    "Exercise video stored without poster: %s",
                    published.public_path,
                    exc_info=True,
                )
        if storage is not None:
            media_key, media_created = _upload_public_object(
                storage,
                published.public_path,
                published.absolute_path,
                content_type=expected_content_type,
            )
            if media_created:
                remote_keys.append(media_key)
        temporary_path.unlink(missing_ok=True)
    except Exception:
        _cleanup_remote_objects(storage, tuple(remote_keys))
        if "published" in locals() and published.created:
            published.absolute_path.unlink(missing_ok=True)
        temporary_path.unlink(missing_ok=True)
        raise

    return StoredMedia(
        public_path=published.public_path,
        media_type=media_type,
        absolute_path=published.absolute_path,
        created=published.created or bool(remote_keys),
        object_key=remote_keys[0] if remote_keys else None,
        storage=storage,
        remote_created=bool(remote_keys),
        remote_object_keys=tuple(remote_keys),
    )


def discard_media(media: StoredMedia) -> None:
    if media.remote_created:
        _cleanup_remote_objects(media.storage, media.remote_object_keys)
    if media.created and media.absolute_path is not None:
        media.absolute_path.unlink(missing_ok=True)


def discard_managed_media_file(public_path: str | None, settings: Settings) -> None:
    if public_path is None:
        return
    expected_prefix = f"{settings.media_public_path.rstrip('/')}/"
    if not public_path.startswith(expected_prefix):
        return
    relative_path = public_path.removeprefix(expected_prefix)
    if not relative_path:
        return
    _discard_public_path(public_path, settings, relative_path)


def store_image_upload(
    upload: UploadFile,
    settings: Settings,
    subdirectory: str,
) -> StoredMedia:
    if not subdirectory or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in subdirectory
    ):
        raise MediaValidationError("Invalid media directory")
    if (
        not upload.filename
        or "\x00" in upload.filename
        or "/" in upload.filename
        or "\\" in upload.filename
    ):
        raise MediaValidationError("Invalid media filename")
    extension = Path(upload.filename).suffix.lower()
    expected_content_type = ALLOWED_IMAGE_MEDIA.get(extension)
    if expected_content_type is None:
        raise MediaValidationError("Only GIF, JPEG, PNG, and WebP image files are supported")
    if upload.content_type != expected_content_type:
        raise MediaValidationError("Image MIME type does not match its extension")

    storage_root = settings.media_root / subdirectory
    temporary_path = _write_temporary(upload, settings, storage_root)
    storage: ObjectStorage | None = None
    remote_keys: list[str] = []
    try:
        storage = _public_storage(settings)
        with temporary_path.open("rb") as file_handle:
            detected_extension = _signature_extension(file_handle.read(64))
        if detected_extension != extension and not (
            detected_extension == ".jpg" and extension == ".jpeg"
        ):
            raise MediaValidationError("Image signature does not match its extension")
        final_path = _publish_temporary(temporary_path, extension, storage_root)
        if storage is not None:
            remote_key, remote_created = _upload_public_object(
                storage,
                f"{settings.media_public_path.rstrip('/')}/{subdirectory}/{final_path.name}",
                final_path,
                content_type=expected_content_type,
            )
            if remote_created:
                remote_keys.append(remote_key)
    except Exception:
        _cleanup_remote_objects(storage, tuple(remote_keys))
        if "final_path" in locals() and final_path.exists():
            final_path.unlink(missing_ok=True)
        temporary_path.unlink(missing_ok=True)
        raise

    public_root = settings.media_public_path.rstrip("/")
    return StoredMedia(
        public_path=f"{public_root}/{subdirectory}/{final_path.name}",
        media_type=MediaType.IMAGE,
        absolute_path=final_path,
        created=True,
        object_key=remote_keys[0] if remote_keys else None,
        storage=storage,
        remote_created=bool(remote_keys),
        remote_object_keys=tuple(remote_keys),
    )


def discard_managed_media_path(
    public_path: str | None,
    settings: Settings,
    subdirectory: str,
) -> None:
    if public_path is None:
        return
    expected_prefix = f"{settings.media_public_path.rstrip('/')}/{subdirectory}/"
    if not public_path.startswith(expected_prefix):
        return
    filename = public_path.removeprefix(expected_prefix)
    if not filename or Path(filename).name != filename:
        return
    managed_root = (settings.media_root / subdirectory).resolve()
    target = (managed_root / filename).resolve()
    if target.parent == managed_root:
        _discard_public_path(public_path, settings, f"{subdirectory}/{filename}")


def _discard_public_path(public_path: str, settings: Settings, relative_path: str) -> None:
    media_root = settings.media_root.resolve()
    target = (media_root / relative_path).resolve()
    if target == media_root or media_root not in target.parents:
        return
    if settings.media_storage_backend == "s3":
        try:
            storage = _public_storage(settings)
            if storage is not None:
                storage.delete(public_object_key(public_path))
        except (MediaObjectKeyError, MediaStorageError, ObjectStorageError) as error:
            raise MediaStorageError("Public media delete failed") from error
    target.unlink(missing_ok=True)
