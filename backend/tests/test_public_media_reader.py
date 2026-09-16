from collections.abc import Iterator
from pathlib import Path

from app.config import Settings
from app.media.public import PublicMediaReader
from app.media.storage import ObjectMetadata, ObjectNotFoundError, StoredObject


class CountingStorage:
    def __init__(self, content: bytes | None) -> None:
        self.content = content
        self.reads = 0

    def read(self, key: str) -> bytes:
        self.reads += 1
        if self.content is None:
            raise ObjectNotFoundError(key)
        return self.content

    def head(self, key: str) -> ObjectMetadata | None:
        raise NotImplementedError

    def iter_bytes(self, key: str) -> Iterator[bytes]:
        raise NotImplementedError

    def put_file(self, key: str, source: Path, **kwargs: object) -> StoredObject:
        raise NotImplementedError

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        return ()

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def public_url(self, key: str) -> str:
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


def test_public_reader_caches_s3_content_during_one_render(tmp_path: Path) -> None:
    storage = CountingStorage(b"remote-image")
    reader = PublicMediaReader(_settings(tmp_path), storage)

    assert reader.read_public_path("/media/meal-catalogue/meal.webp") == b"remote-image"
    assert reader.read_public_path("/media/meal-catalogue/meal.webp") == b"remote-image"
    assert storage.reads == 1


def test_public_reader_uses_local_fallback_without_exposing_private_paths(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    local = settings.media_root / "food-catalogue" / "food.jpg"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"local-image")
    storage = CountingStorage(None)
    reader = PublicMediaReader(settings, storage)

    assert reader.read_public_path("/media/food-catalogue/food.jpg") == b"local-image"
    assert storage.reads == 1
