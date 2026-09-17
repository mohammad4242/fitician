from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.media.storage import ObjectMetadata, ObjectStorageError, StoredObject


class StubStorage:
    def __init__(self, *, exists: bool, fail: bool = False) -> None:
        self.exists = exists
        self.fail = fail

    def head(self, key: str) -> ObjectMetadata | None:
        if self.fail:
            raise ObjectStorageError("provider unavailable")
        return ObjectMetadata(key, 5, "abc") if self.exists else None

    def public_url(self, key: str) -> str:
        return f"https://media.example.test/{key}"

    def read(self, key: str) -> bytes:
        raise NotImplementedError

    def iter_bytes(self, key: str) -> Iterator[bytes]:
        raise NotImplementedError

    def put_file(self, key: str, source: Path, **kwargs: object) -> StoredObject:
        raise NotImplementedError

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        return ()

    def delete(self, key: str) -> None:
        raise NotImplementedError


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        media_root=tmp_path / "media",
        media_storage_backend="s3",
        s3_endpoint="https://s3.example.test",
        s3_bucket="fitician-media",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
        s3_region="ir-thr-at1",
        media_public_base_url="https://media.example.test",
    )


def test_s3_public_media_redirects_without_changing_logical_path(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings, public_media_storage=StubStorage(exists=True))

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/media/exercises/bench--123/media-abc.mp4")

    assert response.status_code == 307
    assert response.headers["location"] == (
        "https://media.example.test/public/exercises/bench--123/media-abc.mp4"
    )


def test_s3_missing_object_uses_visible_local_fallback(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    local = settings.media_root / "food-catalogue" / "food.jpg"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"local")
    app = create_app(settings, public_media_storage=StubStorage(exists=False))

    with TestClient(app) as client:
        response = client.get("/media/food-catalogue/food.jpg")

    assert response.status_code == 200
    assert response.content == b"local"
    assert response.headers["X-Fitician-Media-Fallback"] == "local"


def test_s3_failure_without_local_copy_is_explicit(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings, public_media_storage=StubStorage(exists=False, fail=True))

    with TestClient(app) as client:
        response = client.get("/media/meal-catalogue/missing.webp")

    assert response.status_code == 503


def test_s3_disabled_local_fallback_does_not_serve_local_copy(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.media_local_fallback_enabled = False
    local = settings.media_root / "food-catalogue" / "food.jpg"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"local")
    app = create_app(settings, public_media_storage=StubStorage(exists=False))

    with TestClient(app) as client:
        response = client.get("/media/food-catalogue/food.jpg")

    assert response.status_code == 404
