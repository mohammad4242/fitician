"""Migrate only current, locally matched private media to the private S3 bucket."""

from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_engine
from app.media.factory import build_private_s3_storage
from app.media.private_migration import (
    PRIVATE_CATEGORIES,
    build_private_manifest,
    remote_conflicts,
    upload_private_manifest,
    verify_private_manifest,
)
from scripts.reconcile_media import database_keys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--upload", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--category", action="append", choices=PRIVATE_CATEGORIES)
    args = parser.parse_args()

    settings = get_settings()
    categories = tuple(args.category or PRIVATE_CATEGORIES)
    with Session(get_engine(settings.database_url)) as db:
        references = database_keys(db)
    current = {category: set(references[category][0]) for category in PRIVATE_CATEGORIES}
    records, missing = build_private_manifest(settings, current, categories=categories)
    print(f"Current matched objects: {len(records)}")
    print(f"Current matched bytes: {sum(record.size_bytes for record in records)}")
    print(f"Missing current files: {len(missing)}")
    if missing:
        print("Upload blocked: unresolved current private files remain")
        raise SystemExit(2)

    storage = build_private_s3_storage(settings)
    new, conflicts = remote_conflicts(storage, records)
    print(f"New private objects: {len(new)}")
    print(f"Conflicts: {len(conflicts)}")
    if conflicts:
        raise SystemExit(2)
    if args.dry_run:
        return
    if args.upload:
        uploaded, skipped = upload_private_manifest(storage, records)
        print(f"Uploaded: {uploaded}; skipped identical: {skipped}")
        return
    verified, total_bytes = verify_private_manifest(storage, records)
    print(f"SHA-256 verified: {verified}/{len(records)}")
    print(f"Verified bytes: {total_bytes}")
    if verified != len(records):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
