from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol

from app.config import Settings
from app.media.private_storage import PrivateStorageError, build_private_storage


class BodyPhotoStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredBodyPhoto:
    key: str


class BodyPhotoStorageProtocol(Protocol):
    def store(self, content: bytes, extension: str) -> StoredBodyPhoto: ...

    def open(self, key: str) -> BinaryIO: ...

    def delete(self, key: str) -> None: ...


class BodyPhotoStorage:
    def __init__(self, settings: Settings) -> None:
        self._storage = build_private_storage(settings)

    def store(self, content: bytes, extension: str) -> StoredBodyPhoto:
        if extension not in {".jpg", ".png", ".webp"} or not content:
            raise BodyPhotoStorageError("Invalid normalized body photo")
        try:
            content_type = {
                ".jpg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }[extension]
            stored = self._storage.put("body-photos", content, extension, content_type)
        except PrivateStorageError as error:
            raise BodyPhotoStorageError(str(error)) from error
        return StoredBodyPhoto(key=stored.key)

    def open(self, key: str) -> BinaryIO:
        try:
            return self._storage.open("body-photos", key)
        except (OSError, BodyPhotoStorageError, PrivateStorageError) as error:
            raise BodyPhotoStorageError("Private body photo is unavailable") from error

    def delete(self, key: str) -> None:
        try:
            self._storage.delete("body-photos", key)
        except (OSError, BodyPhotoStorageError, PrivateStorageError) as error:
            raise BodyPhotoStorageError("Private storage is temporarily unavailable") from error
