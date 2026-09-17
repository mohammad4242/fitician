"""Provider-neutral private media storage for authenticated user-owned files."""

from __future__ import annotations

import io
import os
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol
from uuid import uuid4

from app.config import Settings
from app.media.object_keys import PRIVATE_SCOPES, MediaObjectKeyError, private_object_key
from app.media.storage import (
    ObjectNotFoundError,
    ObjectStorageError,
    S3ObjectStorage,
    StoredObject,
)


class PrivateStorageError(RuntimeError):
    pass


class PrivateStorage(Protocol):
    def put(
        self, scope: str, content: bytes, extension: str, content_type: str
    ) -> StoredObject: ...

    def exists(self, scope: str, storage_key: str) -> bool: ...

    def read(self, scope: str, storage_key: str) -> bytes: ...

    def iter_bytes(self, scope: str, storage_key: str) -> Iterator[bytes]: ...

    def open(self, scope: str, storage_key: str) -> BinaryIO: ...

    def delete(self, scope: str, storage_key: str) -> None: ...


def _validate_storage_key(scope: str, storage_key: str) -> PurePosixPath:
    try:
        object_key = private_object_key(scope, storage_key)
    except MediaObjectKeyError as error:
        raise PrivateStorageError("Invalid private storage key") from error
    parts = PurePosixPath(object_key).parts
    if len(parts) < 3 or parts[:2] != ("private", scope):
        raise PrivateStorageError("Invalid private storage key")
    return PurePosixPath(*parts[2:])


class LocalPrivateStorage:
    def __init__(self, roots: dict[str, Path]) -> None:
        self._roots = {scope: path.resolve() for scope, path in roots.items()}

    def _path(self, scope: str, storage_key: str) -> Path:
        relative = _validate_storage_key(scope, storage_key)
        root = self._roots.get(scope)
        if root is None:
            raise PrivateStorageError("Unknown private storage scope")
        path = root.joinpath(*relative.parts)
        if not path.resolve(strict=False).is_relative_to(root):
            raise PrivateStorageError("Invalid private storage key")
        return path

    def put(self, scope: str, content: bytes, extension: str, content_type: str) -> StoredObject:
        del content_type
        if scope not in PRIVATE_SCOPES or extension not in {".jpg", ".png", ".webp", ".pdf"}:
            raise PrivateStorageError("Invalid private media")
        if not content:
            raise PrivateStorageError("Private media must not be empty")
        identifier = uuid4().hex
        storage_key = f"{identifier[:2]}/{identifier}{extension}"
        path = self._path(scope, storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(content)
            os.chmod(path, 0o644)
        except OSError as error:
            raise PrivateStorageError("Private storage is temporarily unavailable") from error
        digest = __import__("hashlib").sha256(content).hexdigest()
        return StoredObject(storage_key, digest, len(content), True)

    def exists(self, scope: str, storage_key: str) -> bool:
        try:
            return self._path(scope, storage_key).is_file()
        except PrivateStorageError:
            return False

    def read(self, scope: str, storage_key: str) -> bytes:
        try:
            return self._path(scope, storage_key).read_bytes()
        except FileNotFoundError as error:
            raise ObjectNotFoundError(storage_key) from error
        except OSError as error:
            raise PrivateStorageError("Private media read failed") from error

    def iter_bytes(self, scope: str, storage_key: str) -> Iterator[bytes]:
        try:
            with self._path(scope, storage_key).open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    yield chunk
        except FileNotFoundError as error:
            raise ObjectNotFoundError(storage_key) from error
        except OSError as error:
            raise PrivateStorageError("Private media read failed") from error

    def open(self, scope: str, storage_key: str) -> BinaryIO:
        try:
            return self._path(scope, storage_key).open("rb")
        except FileNotFoundError as error:
            raise ObjectNotFoundError(storage_key) from error
        except OSError as error:
            raise PrivateStorageError("Private media read failed") from error

    def delete(self, scope: str, storage_key: str) -> None:
        try:
            self._path(scope, storage_key).unlink(missing_ok=True)
        except OSError as error:
            raise PrivateStorageError("Private storage delete failed") from error


class S3PrivateStorage:
    def __init__(self, storage: S3ObjectStorage) -> None:
        self._storage = storage

    def _key(self, scope: str, storage_key: str) -> str:
        try:
            return private_object_key(scope, storage_key)
        except MediaObjectKeyError as error:
            raise PrivateStorageError("Invalid private storage key") from error

    def put(self, scope: str, content: bytes, extension: str, content_type: str) -> StoredObject:
        if extension not in {".jpg", ".png", ".webp", ".pdf"}:
            raise PrivateStorageError("Invalid private media")
        try:
            identifier = uuid4().hex
            object_key = self._storage.put(
                self._key(scope, f"{identifier[:2]}/{identifier}{extension}"),
                content,
                content_type=content_type,
            )
            return StoredObject(
                key=object_key.key.removeprefix(f"private/{scope}/"),
                sha256=object_key.sha256,
                size_bytes=object_key.size_bytes,
                created=object_key.created,
            )
        except ObjectStorageError as error:
            raise PrivateStorageError("Private S3 upload failed") from error

    def exists(self, scope: str, storage_key: str) -> bool:
        try:
            return self._storage.head(self._key(scope, storage_key)) is not None
        except ObjectStorageError as error:
            raise PrivateStorageError("Private S3 metadata request failed") from error

    def read(self, scope: str, storage_key: str) -> bytes:
        try:
            return self._storage.read(self._key(scope, storage_key))
        except ObjectNotFoundError:
            raise
        except ObjectStorageError as error:
            raise PrivateStorageError("Private S3 read failed") from error

    def iter_bytes(self, scope: str, storage_key: str) -> Iterator[bytes]:
        try:
            yield from self._storage.iter_bytes(self._key(scope, storage_key))
        except ObjectNotFoundError:
            raise
        except ObjectStorageError as error:
            raise PrivateStorageError("Private S3 read failed") from error

    def open(self, scope: str, storage_key: str) -> BinaryIO:
        return io.BytesIO(self.read(scope, storage_key))

    def delete(self, scope: str, storage_key: str) -> None:
        try:
            self._storage.delete(self._key(scope, storage_key))
        except ObjectStorageError as error:
            raise PrivateStorageError("Private S3 delete failed") from error


def build_private_storage(settings: Settings) -> PrivateStorage:
    roots = {
        "body-photos": Path(
            getattr(settings, "body_photo_storage_root", Path("var/private/body-photos"))
        ),
        "food-photos": Path(
            getattr(settings, "food_photo_storage_root", Path("var/private/food-photos"))
        ),
        "profile-photos": Path(
            getattr(settings, "profile_photo_storage_root", Path("var/private/profile-photos"))
        ),
        "nutrition-labs": Path(
            getattr(settings, "nutrition_lab_storage_root", Path("var/private/nutrition-labs"))
        ),
    }
    if getattr(settings, "media_storage_backend", "local") == "s3":
        from app.media.factory import build_private_s3_storage

        return S3PrivateStorage(build_private_s3_storage(settings))
    return LocalPrivateStorage(roots)
