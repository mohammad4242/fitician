"""Provider-neutral object storage used by public media and migration tooling."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from urllib.parse import quote

from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]


class ObjectStorageError(RuntimeError):
    pass


class ObjectNotFoundError(ObjectStorageError):
    pass


class ObjectConflictError(FileExistsError, ObjectStorageError):
    pass


@dataclass(frozen=True)
class ObjectMetadata:
    key: str
    size_bytes: int
    sha256: str | None
    content_type: str | None = None


@dataclass(frozen=True)
class StoredObject:
    key: str
    sha256: str
    size_bytes: int
    created: bool


class ObjectStorage(Protocol):
    def head(self, key: str) -> ObjectMetadata | None: ...

    def put_file(
        self,
        key: str,
        source: Path,
        *,
        sha256: str,
        content_type: str | None = None,
    ) -> StoredObject: ...

    def iter_bytes(self, key: str) -> Iterator[bytes]: ...

    def read(self, key: str) -> bytes: ...

    def list_keys(self, prefix: str) -> tuple[str, ...]: ...

    def delete(self, key: str) -> None: ...

    def public_url(self, key: str) -> str: ...


def validate_object_key(key: str) -> PurePosixPath:
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
    return relative


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LocalObjectStorage:
    """Bucket-shaped local storage with collision and traversal protection."""

    def __init__(self, root: Path, *, public_base_url: str = "/media") -> None:
        self._root = root.resolve()
        self._public_base_url = public_base_url.rstrip("/")

    def _path_for(self, key: str) -> Path:
        relative = validate_object_key(key)
        path = self._root.joinpath(*relative.parts)
        if not path.resolve(strict=False).is_relative_to(self._root):
            raise ObjectStorageError("Object key escapes storage root")
        return path

    def head(self, key: str) -> ObjectMetadata | None:
        path = self._path_for(key)
        if not path.exists():
            return None
        if not path.is_file():
            raise ObjectStorageError("Object key does not identify a file")
        return ObjectMetadata(key, path.stat().st_size, sha256_file(path))

    def put(self, key: str, content: bytes) -> StoredObject:
        if not content:
            raise ObjectStorageError("Object content must not be empty")
        digest = hashlib.sha256(content).hexdigest()
        staged: Path | None = None
        self._root.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".object-source-", dir=self._root, delete=False
            ) as handle:
                staged = Path(handle.name)
                handle.write(content)
            return self.put_file(key, staged, sha256=digest)
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)

    def put_file(
        self,
        key: str,
        source: Path,
        *,
        sha256: str,
        content_type: str | None = None,
    ) -> StoredObject:
        del content_type
        if not source.is_file() or source.stat().st_size == 0:
            raise ObjectStorageError("Object source must be a non-empty file")
        if sha256_file(source) != sha256:
            raise ObjectStorageError("Object source SHA-256 does not match")
        path = self._path_for(key)
        current = self.head(key)
        if current is not None:
            if current.size_bytes != source.stat().st_size or current.sha256 != sha256:
                raise ObjectConflictError(f"Object key contains different bytes: {key}")
            return StoredObject(key, sha256, current.size_bytes, False)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".object-", dir=path.parent, delete=False
            ) as handle:
                temporary = Path(handle.name)
                with source.open("rb") as source_handle:
                    shutil.copyfileobj(source_handle, handle)
                handle.flush()
                os.fsync(handle.fileno())
            if sha256_file(temporary) != sha256:
                raise ObjectStorageError("Local object copy verification failed")
            try:
                os.link(temporary, path)
            except FileExistsError:
                current = self.head(key)
                if current is None or current.sha256 != sha256:
                    raise ObjectConflictError(
                        f"Object key contains different bytes: {key}"
                    ) from None
                return StoredObject(key, sha256, current.size_bytes, False)
            return StoredObject(key, sha256, source.stat().st_size, True)
        except ObjectConflictError:
            raise
        except OSError as error:
            raise ObjectStorageError("Local object storage write failed") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def iter_bytes(self, key: str) -> Iterator[bytes]:
        try:
            with self._path_for(key).open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    yield chunk
        except FileNotFoundError as error:
            raise ObjectNotFoundError(key) from error
        except OSError as error:
            raise ObjectStorageError("Local object storage read failed") from error

    def read(self, key: str) -> bytes:
        return b"".join(self.iter_bytes(key))

    def open(self, key: str) -> Any:
        """Compatibility helper for existing callers; prefer read or iter_bytes."""
        try:
            return self._path_for(key).open("rb")
        except FileNotFoundError as error:
            raise ObjectNotFoundError(key) from error

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        prefix_path = validate_object_key(prefix.rstrip("/") + "/placeholder").parent
        root = self._root.joinpath(*prefix_path.parts)
        if not root.exists():
            return ()
        return tuple(
            sorted(
                path.relative_to(self._root).as_posix()
                for path in root.rglob("*")
                if path.is_file() and not path.is_symlink()
            )
        )

    def delete(self, key: str) -> None:
        try:
            self._path_for(key).unlink(missing_ok=True)
        except OSError as error:
            raise ObjectStorageError("Local object storage delete failed") from error

    def public_url(self, key: str) -> str:
        relative = validate_object_key(key)
        if relative.parts[0] != "public":
            raise ObjectStorageError("Private objects do not have public URLs")
        return f"{self._public_base_url}/{quote('/'.join(relative.parts[1:]), safe='/')}"


class S3ObjectStorage:
    """S3-compatible storage with SHA-256 metadata and conflict protection."""

    _SINGLE_PUT_MAX_BYTES = 64 * 1024 * 1024

    def __init__(
        self,
        client: Any,
        *,
        bucket: str,
        public_base_url: str,
        public_acl: str = "public-read",
    ) -> None:
        self._client = client
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/")
        self._public_acl = public_acl

    def head(self, key: str) -> ObjectMetadata | None:
        validate_object_key(key)
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise ObjectStorageError("S3 object metadata request failed") from error
        except BotoCoreError as error:
            raise ObjectStorageError("S3 object metadata request failed") from error
        metadata = response.get("Metadata", {})
        return ObjectMetadata(
            key=key,
            size_bytes=int(response["ContentLength"]),
            sha256=metadata.get("sha256"),
            content_type=response.get("ContentType"),
        )

    def put_file(
        self,
        key: str,
        source: Path,
        *,
        sha256: str,
        content_type: str | None = None,
    ) -> StoredObject:
        relative = validate_object_key(key)
        if not source.is_file() or source.stat().st_size == 0:
            raise ObjectStorageError("Object source must be a non-empty file")
        if sha256_file(source) != sha256:
            raise ObjectStorageError("Object source SHA-256 does not match")
        current = self.head(key)
        if current is not None:
            if current.size_bytes != source.stat().st_size or current.sha256 != sha256:
                raise ObjectConflictError(f"Remote object differs or lacks SHA-256 metadata: {key}")
            return StoredObject(key, sha256, current.size_bytes, False)
        extra: dict[str, Any] = {"Metadata": {"sha256": sha256}}
        if content_type:
            extra["ContentType"] = content_type
        if relative.parts[0] == "public" and self._public_acl:
            extra["ACL"] = self._public_acl
        try:
            if source.stat().st_size <= self._SINGLE_PUT_MAX_BYTES:
                with source.open("rb") as body:
                    self._client.put_object(
                        Bucket=self._bucket,
                        Key=key,
                        Body=body,
                        **extra,
                    )
            else:
                self._client.upload_file(str(source), self._bucket, key, ExtraArgs=extra)
        except (BotoCoreError, ClientError, OSError) as error:
            # S3-compatible providers can commit the object and lose the PUT response.
            # Accept that outcome only after an authenticated size and SHA-256 check.
            try:
                completed = self.head(key)
            except ObjectStorageError:
                completed = None
            if (
                completed is not None
                and completed.size_bytes == source.stat().st_size
                and completed.sha256 == sha256
            ):
                return StoredObject(key, sha256, completed.size_bytes, True)
            raise ObjectStorageError("S3 object upload failed") from error
        uploaded = self.head(key)
        if (
            uploaded is None
            or uploaded.size_bytes != source.stat().st_size
            or uploaded.sha256 != sha256
        ):
            raise ObjectStorageError(f"S3 object metadata verification failed: {key}")
        return StoredObject(key, sha256, uploaded.size_bytes, True)

    def iter_bytes(self, key: str) -> Iterator[bytes]:
        validate_object_key(key)
        body: Any | None = None
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            body = response["Body"]
            for chunk in body.iter_chunks(chunk_size=1024 * 1024):
                if chunk:
                    yield chunk
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise ObjectNotFoundError(key) from error
            raise ObjectStorageError("S3 object read failed") from error
        except BotoCoreError as error:
            raise ObjectStorageError("S3 object read failed") from error
        finally:
            if body is not None:
                body.close()

    def read(self, key: str) -> bytes:
        return b"".join(self.iter_bytes(key))

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        validate_object_key(prefix.rstrip("/") + "/placeholder")
        keys: list[str] = []
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                keys.extend(item["Key"] for item in page.get("Contents", ()))
        except (BotoCoreError, ClientError) as error:
            raise ObjectStorageError("S3 object listing failed") from error
        return tuple(sorted(keys))

    def delete(self, key: str) -> None:
        validate_object_key(key)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError) as error:
            raise ObjectStorageError("S3 object deletion failed") from error

    def public_url(self, key: str) -> str:
        relative = validate_object_key(key)
        if relative.parts[0] != "public":
            raise ObjectStorageError("Private objects do not have public URLs")
        return f"{self._public_base_url}/{quote(key, safe='/')}"
