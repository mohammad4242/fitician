import pytest

from app.media.object_keys import MediaObjectKeyError, private_object_key, public_object_key
from app.media.storage import LocalObjectStorage, ObjectNotFoundError, ObjectStorageError


def test_existing_public_paths_keep_their_relative_hierarchy() -> None:
    assert public_object_key("/media/exercises/bench--123/media-abc.mp4") == (
        "public/exercises/bench--123/media-abc.mp4"
    )
    assert public_object_key("/media/food-catalogue/food.jpg") == ("public/food-catalogue/food.jpg")
    assert public_object_key("/media/meal-catalogue/meal.webp") == (
        "public/meal-catalogue/meal.webp"
    )


def test_private_keys_remain_private_and_keep_existing_relative_key() -> None:
    assert private_object_key("body-photos", "ab/abc.jpg") == "private/body-photos/ab/abc.jpg"
    assert private_object_key("nutrition-labs", "ab/doc.pdf") == (
        "private/nutrition-labs/ab/doc.pdf"
    )


@pytest.mark.parametrize(
    "path",
    [
        "https://provider.invalid/image.jpg",
        "/media/../private/photo.jpg",
        "/media/a//b.jpg",
        "/media/a%2fb.jpg",
        "/exercises/seed/a.gif",
    ],
)
def test_public_key_rejects_urls_and_unsafe_paths(path: str) -> None:
    with pytest.raises(MediaObjectKeyError):
        public_object_key(path)


def test_private_key_rejects_unknown_scope_and_traversal() -> None:
    with pytest.raises(MediaObjectKeyError):
        private_object_key("public", "aa/a.jpg")
    with pytest.raises(MediaObjectKeyError):
        private_object_key("body-photos", "../a.jpg")


def test_local_object_storage_uses_stable_keys_without_overwriting(tmp_path) -> None:  # type: ignore[no-untyped-def]
    storage = LocalObjectStorage(tmp_path)
    key = "private/body-photos/aa/photo.jpg"

    stored = storage.put(key, b"photo")
    assert stored.key == key
    assert stored.created is True
    assert storage.open(key).read() == b"photo"
    assert storage.put(key, b"photo").created is False

    with pytest.raises(FileExistsError):
        storage.put(key, b"different")
    storage.delete(key)
    with pytest.raises(ObjectNotFoundError):
        storage.open(key)


@pytest.mark.parametrize(
    "key",
    [
        "public/a//b.jpg",
        "public/a/./b.jpg",
        "public/a\\b.jpg",
        "https://provider.invalid/a.jpg",
    ],
)
def test_local_object_storage_rejects_non_normalized_keys(tmp_path, key: str) -> None:  # type: ignore[no-untyped-def]
    storage = LocalObjectStorage(tmp_path)

    with pytest.raises(ObjectStorageError, match="Invalid object key"):
        storage.put(key, b"photo")


def test_local_object_storage_rejects_symlink_escape(tmp_path) -> None:  # type: ignore[no-untyped-def]
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "objects"
    (root / "public").mkdir(parents=True)
    (root / "public" / "escape").symlink_to(outside, target_is_directory=True)
    storage = LocalObjectStorage(root)

    with pytest.raises(ObjectStorageError, match="escapes storage root"):
        storage.put("public/escape/photo.jpg", b"photo")
    assert not (outside / "photo.jpg").exists()
