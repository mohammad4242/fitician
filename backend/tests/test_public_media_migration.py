from pathlib import Path

import pytest

from app.media.public_migration import (
    PUBLIC_CATEGORIES,
    build_manifest,
    missing_database_targets,
    plan_remote,
    upload_manifest,
    verify_manifest,
)
from app.media.storage import LocalObjectStorage, ObjectStorageError


def _media_tree(root: Path) -> None:
    files = {
        "food-catalogue/food.jpg": b"food",
        "meal-catalogue/meal.webp": b"meal",
        "exercises/seed/curl.gif": b"seed",
        "exercises/bench--123/media-abc.mp4": b"exercise",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def test_manifest_is_deterministic_and_keeps_canonical_keys(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    _media_tree(media_root)

    first = build_manifest(media_root, PUBLIC_CATEGORIES)
    second = build_manifest(media_root, PUBLIC_CATEGORIES)

    assert first == second
    assert len(first.records) == 4
    assert {record.object_key for record in first.records} == {
        "public/food-catalogue/food.jpg",
        "public/meal-catalogue/meal.webp",
        "public/exercises/seed/curl.gif",
        "public/exercises/bench--123/media-abc.mp4",
    }
    assert all(not Path(record.source_path).is_absolute() for record in first.records)


def test_manifest_rejects_an_empty_approved_category(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    (media_root / "food-catalogue").mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match="is empty"):
        build_manifest(media_root, ("food-catalogue",))


def test_manifest_detects_missing_selected_database_targets(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    _media_tree(media_root)
    manifest = build_manifest(media_root, PUBLIC_CATEGORIES)

    assert missing_database_targets(
        manifest,
        (
            "/media/exercises/bench--123/media-abc.mp4",
            "/media/exercises/seed/missing.gif",
            "/media/food-catalogue/missing.jpg",
            "/media/meal-catalogue/../private.jpg",
            "/exercises/exercise-placeholder.svg",
        ),
    ) == (
        "/media/exercises/seed/missing.gif",
        "/media/food-catalogue/missing.jpg",
        "/media/meal-catalogue/../private.jpg",
    )


def test_upload_is_resumable_and_verifies_downloaded_sha256(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    _media_tree(media_root)
    manifest = build_manifest(media_root, PUBLIC_CATEGORIES)
    storage = LocalObjectStorage(tmp_path / "bucket", public_base_url="https://media.test")
    state = tmp_path / "state.json"

    plan = plan_remote(storage, manifest)
    assert plan.new_objects == 4
    assert plan.conflicting_objects == ()
    assert upload_manifest(storage, media_root, manifest, state_path=state, resume=False) == (4, 0)
    result = verify_manifest(storage, manifest, state_path=state, check_public_read=False)
    assert result.sha256_verified == 4
    assert result.bytes == manifest.total_bytes
    assert result.failures == ()
    assert result.unexpected_objects == ()
    assert upload_manifest(storage, media_root, manifest, state_path=state, resume=True) == (0, 4)
    assert all(path.is_file() for path in media_root.rglob("*") if path.suffix)


def test_upload_refuses_remote_conflict_or_unexpected_key(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    _media_tree(media_root)
    manifest = build_manifest(media_root, ("food-catalogue",))
    storage = LocalObjectStorage(tmp_path / "bucket")
    storage.put("public/food-catalogue/food.jpg", b"different")

    plan = plan_remote(storage, manifest)
    assert plan.conflicting_objects == ("public/food-catalogue/food.jpg",)
    with pytest.raises(ObjectStorageError, match="block upload"):
        upload_manifest(
            storage,
            media_root,
            manifest,
            state_path=tmp_path / "state.json",
            resume=False,
        )
