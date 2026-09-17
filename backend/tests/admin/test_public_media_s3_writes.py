from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.admin import media
from app.admin.media import MediaStorageError
from app.admin.router import _media_storage_error
from app.config import Settings
from app.media.storage import ObjectMetadata, ObjectStorageError, StoredObject, sha256_file

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
GIF_BYTES = b"GIF89a" + b"\x00" * 32


def upload(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


class FakePublicStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def head(self, key: str) -> ObjectMetadata | None:
        content = self.objects.get(key)
        if content is None:
            return None
        return ObjectMetadata(
            key=key,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    def put_file(
        self,
        key: str,
        source: Path,
        *,
        sha256: str,
        content_type: str | None = None,
    ) -> StoredObject:
        del content_type
        assert sha256_file(source) == sha256
        content = source.read_bytes()
        current = self.objects.get(key)
        if current is not None:
            assert current == content
            return StoredObject(key, sha256, len(content), False)
        self.objects[key] = content
        return StoredObject(key, sha256, len(content), True)

    def iter_bytes(self, key: str):
        yield self.objects[key]

    def read(self, key: str) -> bytes:
        return self.objects[key]

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        return tuple(sorted(key for key in self.objects if key.startswith(prefix)))

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)

    def public_url(self, key: str) -> str:
        return f"https://media.example/{key}"


class HeadFailsAfterWriteStorage(FakePublicStorage):
    def head(self, key: str) -> ObjectMetadata | None:
        if key in self.objects:
            raise ObjectStorageError("verification unavailable")
        return super().head(key)


def s3_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        cookie_secure=False,
        session_cookie_name="fitician_session",
        media_root=tmp_path,
        media_storage_backend="s3",
        media_public_base_url="https://media.example.test",
        s3_endpoint="https://s3.example.test",
        s3_bucket="fitician-media",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
        s3_region="ir-thr-at1",
    )


def test_food_image_s3_write_keeps_local_fallback_and_provider_neutral_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = FakePublicStorage()
    monkeypatch.setattr(media, "build_s3_storage", lambda settings: storage)

    stored = media.store_image_upload(
        upload("food.png", PNG_BYTES, "image/png"),
        s3_settings(tmp_path),
        "food-catalogue",
    )

    assert stored.object_key == f"public/food-catalogue/{stored.absolute_path.name}"
    assert storage.objects[stored.object_key] == PNG_BYTES
    assert stored.absolute_path.read_bytes() == PNG_BYTES
    assert "s3.example" not in stored.public_path

    media.discard_media(stored)

    assert storage.deleted == [stored.object_key]
    assert not stored.absolute_path.exists()


def test_exercise_s3_write_uses_canonical_hashed_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = FakePublicStorage()
    monkeypatch.setattr(media, "build_s3_storage", lambda settings: storage)

    stored = media.store_upload(
        upload("demo.gif", GIF_BYTES, "image/gif"),
        s3_settings(tmp_path),
        "bench-press--1234",
    )

    digest = hashlib.sha256(GIF_BYTES).hexdigest()
    assert stored.public_path == f"/media/exercises/bench-press--1234/media-{digest}.gif"
    assert stored.object_key == f"public/exercises/bench-press--1234/media-{digest}.gif"
    assert storage.objects[stored.object_key] == GIF_BYTES
    assert stored.absolute_path.read_bytes() == GIF_BYTES

    media.discard_media(stored)
    assert stored.object_key not in storage.objects


def test_s3_delete_helper_only_targets_public_managed_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = FakePublicStorage()
    monkeypatch.setattr(media, "build_s3_storage", lambda settings: storage)
    settings = s3_settings(tmp_path)
    storage.objects["public/food-catalogue/old.png"] = PNG_BYTES

    media.discard_managed_media_path("/media/food-catalogue/old.png", settings, "food-catalogue")
    media.discard_managed_media_path("/media/../private/secret.png", settings, "food-catalogue")

    assert storage.deleted == ["public/food-catalogue/old.png"]
    assert "private/secret.png" not in storage.deleted


def test_admin_storage_failures_have_stable_operational_error_code() -> None:
    error = _media_storage_error(MediaStorageError("upload failed"))

    assert error.status_code == 503
    assert error.detail == {"code": "MEDIA_UPLOAD_FAILED"}


def test_remote_verification_failure_cleans_new_object_and_local_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = HeadFailsAfterWriteStorage()
    monkeypatch.setattr(media, "build_s3_storage", lambda settings: storage)

    with pytest.raises(media.MediaStorageError, match="Public media upload"):
        media.store_image_upload(
            upload("food.png", PNG_BYTES, "image/png"),
            s3_settings(tmp_path),
            "food-catalogue",
        )

    assert storage.objects == {}
    assert not any(tmp_path.rglob("*.png"))
