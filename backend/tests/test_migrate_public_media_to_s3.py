import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import migrate_public_media_to_s3 as migration_script


def test_mp4_and_webm_paths_require_their_convention_posters() -> None:
    video_paths = (
        "/media/exercises/bench/media-abc.mp4",
        "/media/exercises/squat/media-def.webm",
    )

    assert migration_script._required_database_media_paths(video_paths) == (
        "/media/exercises/bench/media-abc.mp4",
        "/media/exercises/bench/media-abc.poster.webp",
        "/media/exercises/squat/media-def.poster.webp",
        "/media/exercises/squat/media-def.webm",
    )


@pytest.mark.parametrize(
    "path",
    (
        "/media/exercises/bench/mobility.gif",
        "/media/exercises/bench/mobility.webp",
        "/media/food-catalogue/food.mp4",
    ),
)
def test_gif_and_image_paths_do_not_require_posters(path: str) -> None:
    assert migration_script._required_database_media_paths((path,)) == (path,)


def test_required_targets_deduplicate_duplicate_video_paths() -> None:
    video_path = "/media/exercises/bench/media-abc.mp4"

    assert migration_script._required_database_media_paths((video_path, video_path)) == (
        video_path,
        "/media/exercises/bench/media-abc.poster.webp",
    )


def test_invalid_or_non_managed_paths_do_not_create_poster_targets() -> None:
    paths = (
        "/media/exercises/bench/../escape.mp4",
        "/media/exercises/bench\\media-abc.mp4",
        "https://cdn.example.test/media/exercises/bench/media-abc.mp4",
        "/media/food-catalogue/video.mp4",
    )

    required = migration_script._required_database_media_paths(paths)

    assert set(required) == set(paths)
    assert not any(path.endswith(".poster.webp") for path in required)


def test_verify_checks_database_targets_before_contacting_object_storage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    video_path = "/media/exercises/bench/media-abc.mp4"
    poster_path = "/media/exercises/bench/media-abc.poster.webp"
    manifest = SimpleNamespace(
        categories=("exercises",),
        records=(),
        total_bytes=0,
        to_dict=lambda: {},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["migrate_public_media_to_s3", "--verify", "--category", "exercises"],
    )
    monkeypatch.setattr(
        migration_script,
        "get_settings",
        lambda: SimpleNamespace(media_root=tmp_path / "media", database_url="unused"),
    )
    monkeypatch.setattr(migration_script, "build_manifest", lambda *_args, **_kwargs: manifest)
    monkeypatch.setattr(migration_script, "write_json_atomic", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        migration_script,
        "category_mapping",
        lambda media_root, category, **_kwargs: (media_root, f"public/{category}"),
    )
    monkeypatch.setattr(
        migration_script,
        "_database_media_paths",
        lambda *_args: (video_path, poster_path),
    )
    monkeypatch.setattr(
        migration_script,
        "missing_database_targets",
        lambda *_args: (poster_path,),
    )
    monkeypatch.setattr(
        migration_script,
        "build_s3_storage",
        lambda *_args: pytest.fail("verification must stop before contacting storage"),
    )

    with pytest.raises(SystemExit, match="2"):
        migration_script.main()
