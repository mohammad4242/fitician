from pathlib import Path

import pytest

from app.exercises.seed_media_sync import SeedMediaSyncError, sync_seed_media


def test_sync_only_referenced_seed_media_without_overwriting(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "upper-body" / "biceps").mkdir(parents=True)
    (source / "upper-body" / "biceps" / "cable-curl.gif").write_bytes(b"GIF89a-source")
    media = tmp_path / "media"
    path = "/media/exercises/seed/cable-curl.gif"

    assert sync_seed_media((path,), source_root=source, media_root=media) == (path,)
    target = media / "exercises" / "seed" / "cable-curl.gif"
    assert target.read_bytes() == b"GIF89a-source"
    assert sync_seed_media((path,), source_root=source, media_root=media) == ()

    target.write_bytes(b"GIF89a-different")
    with pytest.raises(SeedMediaSyncError, match="does not match"):
        sync_seed_media((path,), source_root=source, media_root=media)
    assert target.read_bytes() == b"GIF89a-different"


def test_seed_source_resolves_every_curated_gif(tmp_path: Path) -> None:
    from app.exercises.seed_data import EXERCISE_SEEDS

    source = Path(__file__).resolve().parents[3] / "frontend/public/exercises"
    paths = tuple(seed.media_path for seed in EXERCISE_SEEDS if seed.media_path.endswith(".gif"))

    assert len(paths) == 17
    assert sync_seed_media(paths, source_root=source, media_root=tmp_path / "media") == paths
    assert all((tmp_path / "media" / path.removeprefix("/media/")).is_file() for path in paths)


def test_seed_sync_rejects_unapproved_or_missing_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(SeedMediaSyncError, match="not an approved"):
        sync_seed_media(
            ("/media/exercises/seed/not-curated.gif",), source_root=source, media_root=tmp_path
        )
    with pytest.raises(SeedMediaSyncError, match="Missing"):
        sync_seed_media(
            ("/media/exercises/seed/cable-curl.gif",), source_root=source, media_root=tmp_path
        )
