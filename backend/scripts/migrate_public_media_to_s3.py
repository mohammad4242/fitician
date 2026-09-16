"""Dry-run, upload, or verify approved Fitician public media in S3-compatible storage."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_engine
from app.media.factory import build_s3_storage
from app.media.public_migration import (
    PUBLIC_CATEGORIES,
    build_manifest,
    category_mapping,
    missing_database_targets,
    plan_remote,
    upload_manifest,
    verify_manifest,
    write_json_atomic,
)


def _print_examples(label: str, values: tuple[str, ...]) -> None:
    for value in values[:20]:
        print(f"{label}: {value}")
    if len(values) > 20:
        print(f"{label}: ... and {len(values) - 20} more")


def _database_media_paths(database_url: str, categories: tuple[str, ...]) -> tuple[str, ...]:
    paths: set[str] = set()
    with Session(get_engine(database_url)) as session:
        if "exercises" in categories or "exercise-seed" in categories:
            paths.update(
                session.scalars(
                    text(
                        "SELECT media_path FROM exercises UNION "
                        "SELECT media_path FROM exercise_media_assets"
                    )
                )
            )
        if "food-catalogue" in categories:
            paths.update(
                path
                for path in session.scalars(
                    text("SELECT image_path FROM nutrition_catalogue_foods")
                )
                if path
            )
        if "meal-catalogue" in categories:
            paths.update(
                path
                for path in session.scalars(
                    text("SELECT image_path FROM nutrition_catalogue_meals")
                )
                if path
            )
    return tuple(sorted(paths))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--upload", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument(
        "--category",
        action="append",
        choices=PUBLIC_CATEGORIES,
        dest="categories",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=8, choices=range(1, 33))
    parser.add_argument("--skip-public-read-check", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    categories = tuple(args.categories or PUBLIC_CATEGORIES)
    manifest = build_manifest(settings.media_root, categories)
    report_root = Path("var/media-s3-migration")
    label = "-".join(categories)
    manifest_path = report_root / f"manifest-{label}.json"
    state_path = report_root / f"state-{label}.json"
    write_json_atomic(manifest_path, manifest.to_dict())
    print(f"Manifest: {len(manifest.records)} objects, {manifest.total_bytes} bytes")
    print(f"Categories: {', '.join(categories)}")
    for category in categories:
        source, prefix = category_mapping(settings.media_root, category)
        print(f"Mapping: {source} -> {prefix}/")

    if args.dry_run or args.upload:
        database_paths = _database_media_paths(settings.database_url, categories)
        missing = missing_database_targets(manifest, database_paths)
        print(f"Database media paths checked: {len(database_paths)}")
        print(f"Missing database targets: {len(missing)}")
        _print_examples("Missing", missing)
        if missing:
            raise SystemExit(2)

    storage = build_s3_storage(settings)
    if args.dry_run:
        plan = plan_remote(storage, manifest, workers=args.workers)
        print(f"New: {plan.new_objects}")
        print(f"Already identical: {plan.identical_objects}")
        print(f"Conflicts: {len(plan.conflicting_objects)}")
        print(f"Unexpected destination objects: {len(plan.unexpected_objects)}")
        _print_examples("Conflict", plan.conflicting_objects)
        _print_examples("Unexpected", plan.unexpected_objects)
        if plan.conflicting_objects or plan.unexpected_objects:
            raise SystemExit(2)
        return
    if args.upload:
        uploaded, skipped = upload_manifest(
            storage,
            settings.media_root,
            manifest,
            state_path=state_path,
            resume=args.resume,
            workers=args.workers,
        )
        print(f"Uploaded: {uploaded}; skipped identical: {skipped}")
        return
    result = verify_manifest(
        storage,
        manifest,
        state_path=state_path,
        check_public_read=not args.skip_public_read_check,
        workers=args.workers,
    )
    print(f"SHA-256 verified: {result.sha256_verified}/{result.objects}")
    print(f"Verified bytes: {result.bytes}")
    print(f"Public readable: {result.public_readable}/{result.objects}")
    print(f"Failures: {len(result.failures)}")
    print(f"Unexpected destination objects: {len(result.unexpected_objects)}")
    _print_examples("Failure", result.failures)
    _print_examples("Unexpected", result.unexpected_objects)
    if result.failures or result.unexpected_objects:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
