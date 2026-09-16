"""Provider-neutral binary object storage boundary for future media adapters."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol


class ObjectStorageError(RuntimeError):
    pass


class ObjectNotFoundError(ObjectStorageError):
    pass


@dataclass(frozen=True)
class StoredObject:
    key: str
    sha256: str
    size_bytes: int
    created: bool


class ObjectStorage(Protocol):
    def put(self, key: str, content: bytes) -> StoredObject: ...

    def open(self, key: str) -> BinaryIO: ...

    def delete(self, key: str) -> None: ...


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class LocalObjectStorage:
    """Bucket-shaped local storage with collision and traversal protection."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _path_for(self, key: str) -> Path:
        relative = PurePosixPath(key)
        if (
            not key
            or key.strip() != key
            or "\\" in key
            or "%" in key
            or relative.as_posix() != key
            or relative.is_absolute()
            or len(relative.parts) < 2
            or relative.parts[0] not in {"public", "private"}
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            raise ObjectStorageError("Invalid object key")
        path = self._root.joinpath(*relative.parts)
        if not path.resolve(strict=False).is_relative_to(self._root):
            raise ObjectStorageError("Object key escapes storage root")
        return path

    def put(self, key: str, content: bytes) -> StoredObject:
        if not content:
            raise ObjectStorageError("Object content must not be empty")
        path = self._path_for(key)
        digest = _digest(content)
        if path.exists():
            if not path.is_file() or _digest(path.read_bytes()) != digest:
                raise FileExistsError(f"Object key already contains different bytes: {key}")
            return StoredObject(key, digest, len(content), False)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".object-", dir=path.parent, delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if _digest(path.read_bytes()) != digest:
                    raise FileExistsError(
                        f"Object key already contains different bytes: {key}"
                    ) from None
                return StoredObject(key, digest, len(content), False)
            return StoredObject(key, digest, len(content), True)
        except OSError as error:
            if isinstance(error, FileExistsError):
                raise
            raise ObjectStorageError("Local object storage write failed") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def open(self, key: str) -> BinaryIO:
        try:
            return self._path_for(key).open("rb")
        except FileNotFoundError as error:
            raise ObjectNotFoundError(key) from error
        except OSError as error:
            raise ObjectStorageError("Local object storage read failed") from error

    def delete(self, key: str) -> None:
        try:
            self._path_for(key).unlink(missing_ok=True)
        except OSError as error:
            raise ObjectStorageError("Local object storage delete failed") from error
