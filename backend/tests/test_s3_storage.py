from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from botocore.exceptions import ClientError

from app.media.storage import (
    ObjectConflictError,
    ObjectNotFoundError,
    ObjectStorageError,
    S3ObjectStorage,
    sha256_file,
)


class _Body:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.closed = False

    def iter_chunks(self, chunk_size: int) -> Any:
        stream = BytesIO(self.content)
        while chunk := stream.read(chunk_size):
            yield chunk

    def close(self) -> None:
        self.closed = True


class _Paginator:
    def __init__(self, client: FakeS3Client) -> None:
        self.client = client

    def paginate(self, *, Bucket: str, Prefix: str) -> list[dict[str, Any]]:
        assert Bucket == "fitician-media"
        return [
            {"Contents": [{"Key": key} for key in self.client.objects if key.startswith(Prefix)]}
        ]


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.upload_args: dict[str, Any] | None = None
        self.last_body: _Body | None = None

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        assert Bucket == "fitician-media"
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        item = self.objects[Key]
        return {
            "ContentLength": len(item["body"]),
            "Metadata": item["metadata"],
            "ContentType": item.get("content_type"),
        }

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        *,
        ExtraArgs: dict[str, Any],
    ) -> None:
        assert bucket == "fitician-media"
        self.upload_args = ExtraArgs
        self.objects[key] = {
            "body": Path(filename).read_bytes(),
            "metadata": ExtraArgs["Metadata"],
            "content_type": ExtraArgs.get("ContentType"),
        }

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: Any,
        **kwargs: Any,
    ) -> None:
        assert Bucket == "fitician-media"
        self.upload_args = kwargs
        self.objects[Key] = {
            "body": Body.read(),
            "metadata": kwargs["Metadata"],
            "content_type": kwargs.get("ContentType"),
        }

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        assert Bucket == "fitician-media"
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        self.last_body = _Body(self.objects[Key]["body"])
        return {"Body": self.last_body}

    def get_paginator(self, name: str) -> _Paginator:
        assert name == "list_objects_v2"
        return _Paginator(self)

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        assert Bucket == "fitician-media"
        self.objects.pop(Key, None)


class CommitThenFailS3Client(FakeS3Client):
    def put_object(self, *, Bucket: str, Key: str, Body: Any, **kwargs: Any) -> None:
        super().put_object(Bucket=Bucket, Key=Key, Body=Body, **kwargs)
        raise OSError("response lost after remote commit")


def _storage(client: FakeS3Client) -> S3ObjectStorage:
    return S3ObjectStorage(
        client,
        bucket="fitician-media",
        public_base_url="https://media.example.test",
    )


def test_s3_upload_sets_sha256_content_type_and_public_acl(tmp_path: Path) -> None:
    client = FakeS3Client()
    storage = _storage(client)
    source = tmp_path / "meal.webp"
    source.write_bytes(b"image")
    digest = sha256_file(source)

    stored = storage.put_file(
        "public/meal-catalogue/meal.webp",
        source,
        sha256=digest,
        content_type="image/webp",
    )

    assert stored.created is True
    assert client.upload_args == {
        "Metadata": {"sha256": digest},
        "ContentType": "image/webp",
        "ACL": "public-read",
    }
    assert storage.read(stored.key) == b"image"
    assert client.last_body is not None and client.last_body.closed
    assert storage.public_url(stored.key) == (
        "https://media.example.test/public/meal-catalogue/meal.webp"
    )


def test_s3_upload_skips_identical_and_rejects_conflicts(tmp_path: Path) -> None:
    client = FakeS3Client()
    storage = _storage(client)
    source = tmp_path / "food.jpg"
    source.write_bytes(b"food")
    digest = sha256_file(source)

    assert storage.put_file("public/food-catalogue/food.jpg", source, sha256=digest).created
    assert not storage.put_file("public/food-catalogue/food.jpg", source, sha256=digest).created
    client.objects["public/food-catalogue/food.jpg"]["metadata"] = {}
    with pytest.raises(ObjectConflictError, match="differs"):
        storage.put_file("public/food-catalogue/food.jpg", source, sha256=digest)


def test_s3_upload_accepts_committed_object_when_put_response_is_lost(tmp_path: Path) -> None:
    client = CommitThenFailS3Client()
    storage = _storage(client)
    source = tmp_path / "food.jpg"
    source.write_bytes(b"food")

    stored = storage.put_file(
        "public/food-catalogue/food.jpg",
        source,
        sha256=sha256_file(source),
    )

    assert stored.created is True
    assert stored.size_bytes == source.stat().st_size


def test_s3_missing_and_private_url_are_safe() -> None:
    client = FakeS3Client()
    storage = _storage(client)
    assert storage.head("public/exercises/missing.mp4") is None
    with pytest.raises(ObjectNotFoundError):
        storage.read("public/exercises/missing.mp4")
    with pytest.raises(ObjectStorageError, match="Private"):
        storage.public_url("private/body-photos/photo.jpg")
    with pytest.raises(ObjectStorageError, match="Invalid"):
        storage.head("public/../private/photo.jpg")
    with pytest.raises(ObjectStorageError, match="Invalid"):
        storage.head("public/%2e%2e/private/photo.jpg")


def test_s3_private_object_never_receives_public_acl(tmp_path: Path) -> None:
    client = FakeS3Client()
    storage = _storage(client)
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"private")

    storage.put_file(
        "private/profile-photos/photo.jpg",
        source,
        sha256=sha256_file(source),
        content_type="image/jpeg",
    )

    assert client.upload_args is not None
    assert "ACL" not in client.upload_args
