"""Publish approved tracked seed GIFs to the backend's local served media root."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from app.config import get_settings
from app.exercises.seed_data import EXERCISE_SEEDS
from app.media.object_keys import public_object_key
from app.media.storage import ObjectStorage

SEED_PREFIX = "/media/exercises/seed/"


class SeedMediaSyncError(RuntimeError):
    pass


def validate_seed_media(public_paths: tuple[str, ...], storage: ObjectStorage) -> tuple[str, ...]:
    """Validate approved seed objects in object storage without a source checkout."""
    approved = {
        seed.media_path
        for seed in EXERCISE_SEEDS
        if seed.media_path.startswith(SEED_PREFIX) and seed.media_path.endswith(".gif")
    }
    validated: list[str] = []
    for public_path in dict.fromkeys(public_paths):
        if public_path not in approved:
            raise SeedMediaSyncError(f"{public_path} is not an approved seed GIF path")
        try:
            key = public_object_key(public_path)
            remote = storage.head(key)
        except Exception as error:
            raise SeedMediaSyncError(f"Unable to validate {public_path}") from error
        if remote is None:
            raise SeedMediaSyncError(f"Missing object for {public_path}")
        validated.append(public_path)
    return tuple(validated)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sync_seed_media(
    public_paths: tuple[str, ...], *, source_root: Path, media_root: Path
) -> tuple[str, ...]:
    """Copy only approved seed paths; verify existing bytes and never overwrite them."""
    approved = {
        seed.media_path
        for seed in EXERCISE_SEEDS
        if seed.media_path.startswith(SEED_PREFIX) and seed.media_path.endswith(".gif")
    }
    source_root = source_root.resolve()
    media_root = media_root.resolve()
    copied: list[str] = []
    for public_path in dict.fromkeys(public_paths):
        if public_path not in approved:
            raise SeedMediaSyncError(f"{public_path} is not an approved seed GIF path")
        name = public_path.removeprefix(SEED_PREFIX)
        sources = [
            path
            for path in source_root.rglob(name)
            if path.is_file() and path.resolve().is_relative_to(source_root)
        ]
        if len(sources) != 1:
            raise SeedMediaSyncError(f"Missing or ambiguous tracked source for {public_path}")
        source = sources[0]
        destination = media_root / "exercises" / "seed" / name
        source_hash = _sha256(source)
        if destination.exists():
            if not destination.is_file() or _sha256(destination) != source_hash:
                raise SeedMediaSyncError(
                    f"Existing {public_path} does not match its tracked source"
                )
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        staged: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".seed-media-", dir=destination.parent, delete=False
            ) as handle:
                staged = Path(handle.name)
                with source.open("rb") as source_handle:
                    shutil.copyfileobj(source_handle, handle)
                handle.flush()
                os.fsync(handle.fileno())
            if _sha256(staged) != source_hash:
                raise SeedMediaSyncError(f"Copy verification failed for {public_path}")
            try:
                os.link(staged, destination)
            except FileExistsError:
                if _sha256(destination) != source_hash:
                    raise SeedMediaSyncError(
                        f"Existing {public_path} does not match its tracked source"
                    ) from None
            copied.append(public_path)
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    return tuple(copied)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    settings = get_settings()
    paths = tuple(
        seed.media_path
        for seed in EXERCISE_SEEDS
        if seed.media_path.startswith(SEED_PREFIX) and seed.media_path.endswith(".gif")
    )
    copied = sync_seed_media(paths, source_root=args.source_root, media_root=settings.media_root)
    print(f"Verified {len(paths)} approved seed GIFs; copied {len(copied)} missing files")


if __name__ == "__main__":
    main()
