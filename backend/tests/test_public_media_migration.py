from dataclasses import replace
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
from app.media.storage import LocalObjectStorage, ObjectMetadata, ObjectStorageError


class MetadataLessStorage(LocalObjectStorage):
    def head(self, key: str) -> ObjectMetadata | None:
        metadata = super().head(key)
        return replace(metadata, sha256=None) if metadata is not None else None


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


def test_manifest_maps_large_landing_media_to_remote_prefix(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    landing_root = tmp_path / "landing"
    _media_tree(media_root)
    landing_root.mkdir()
    (landing_root / "story.mp4").write_bytes(b"video")
    (landing_root / "hero.png").write_bytes(b"large-image")
    (landing_root / "icon.png").write_bytes(b"tiny")

    manifest = build_manifest(
        media_root,
        ("landing-videos", "landing-images"),
        landing_root=landing_root,
        landing_image_min_bytes=5,
    )

    assert {record.object_key for record in manifest.records} == {
        "public/landing/videos/story.mp4",
        "public/landing/images/hero.png",
    }


def test_landing_upload_uses_the_landing_source_root(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    landing_root = tmp_path / "landing"
    _media_tree(media_root)
    landing_root.mkdir()
    (landing_root / "story.mp4").write_bytes(b"video")

    manifest = build_manifest(
        media_root,
        ("landing-videos",),
        landing_root=landing_root,
    )
    storage = LocalObjectStorage(tmp_path / "bucket")

    assert upload_manifest(
        storage,
        media_root,
        manifest,
        source_roots={"landing-videos": landing_root},
        state_path=tmp_path / "state.json",
        resume=False,
    ) == (1, 0)
    assert storage.read("public/landing/videos/story.mp4") == b"video"


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

    metadata_less = MetadataLessStorage(tmp_path / "bucket")
    result = verify_manifest(
        metadata_less,
        manifest,
        state_path=tmp_path / "state-2.json",
        check_public_read=False,
    )
    assert result.sha256_verified == 4
    assert result.failures == ()


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


def test_plan_hashes_same_size_object_without_sha_metadata(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    _media_tree(media_root)
    manifest = build_manifest(media_root, ("food-catalogue",))
    bucket = tmp_path / "bucket"
    LocalObjectStorage(bucket).put("public/food-catalogue/food.jpg", b"food")

    storage = MetadataLessStorage(bucket)
    plan = plan_remote(storage, manifest, workers=1)
    assert plan.identical_objects == 1
    assert plan.conflicting_objects == ()
