"""Read-only private-media reconciliation. Detailed output stays under backend/var/."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.session import get_engine

GROUPS = ("body-photos", "food-photos", "profile-photos", "nutrition-labs")
CLASSIFICATIONS = (
    "REFERENCED_CURRENT",
    "REFERENCED_HISTORICAL",
    "TEST_FIXTURE",
    "KNOWN_GENERATED",
    "ORPHAN_CANDIDATE",
    "MISSING_ON_DISK",
    "UNKNOWN",
)
TEST_PDF_HASHES = {
    hashlib.sha256(payload).hexdigest()
    for payload in (
        b"%PDF-1.4\n%%EOF",
        b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF",
    )
}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def database_keys(db: Session) -> dict[str, tuple[dict[str, str], dict[str, str]]]:
    references: dict[str, tuple[dict[str, str], dict[str, str]]] = {
        group: ({}, {}) for group in GROUPS
    }
    body_current, body_historical = references["body-photos"]
    for key, deleted_at in db.execute(
        text(
            "SELECT p.storage_key, s.deleted_at FROM body_photos p "
            "JOIN body_photo_sessions s ON s.id = p.session_id"
        )
    ):
        (body_historical if deleted_at is not None else body_current)[key] = "body_photos"
    for key in db.scalars(text("SELECT storage_key FROM body_photo_storage_cleanups")):
        body_historical[key] = "body_photo_storage_cleanups"

    profile_current, _ = references["profile-photos"]
    for key in db.scalars(text("SELECT storage_key FROM user_profile_photos")):
        profile_current[key] = "user_profile_photos"

    food_current, food_historical = references["food-photos"]
    for key, status, deleted_at in db.execute(
        text("SELECT storage_key, status, deleted_at FROM nutrition_food_photo_estimates")
    ):
        (
            food_historical
            if deleted_at is not None or status in {"deleted", "expired"}
            else food_current
        )[key] = f"nutrition_food_photo_estimates:{status}"

    lab_current, lab_historical = references["nutrition-labs"]
    for key, purged_at in db.execute(
        text("SELECT storage_key, purged_at FROM nutrition_lab_documents")
    ):
        (lab_historical if purged_at is not None else lab_current)[key] = "nutrition_lab_documents"
    return references


def classify_private_files(
    *,
    category: str,
    root: Path,
    current_keys: dict[str, str],
    historical_keys: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Classify conservatively; an absent current key alone never means orphan."""
    files = sorted(path for path in root.rglob("*") if path.is_file() or path.is_symlink())
    metadata: list[tuple[Path, str, int | None, str | None, str | None]] = []
    hash_counts: Counter[str] = Counter()
    for path in files:
        key = path.relative_to(root).as_posix()
        try:
            if path.is_symlink():
                raise OSError("Symlink not followed")
            size = path.stat().st_size
            digest = _hash(path)
            hash_counts[digest] += 1
            error = None
        except OSError as exc:
            size, digest, error = None, None, type(exc).__name__
        metadata.append((path, key, size, digest, error))

    records: list[dict[str, Any]] = []
    present = {key for _, key, _, _, _ in metadata}
    for _, key, size, digest, error in metadata:
        if key in current_keys:
            classification = "REFERENCED_CURRENT"
            reference = current_keys[key]
        elif key in historical_keys:
            classification = "REFERENCED_HISTORICAL"
            reference = historical_keys[key]
        elif category == "nutrition-labs" and digest in TEST_PDF_HASHES:
            classification = "TEST_FIXTURE"
            reference = None
        elif (
            digest is not None and size is not None and size <= 2048 and hash_counts[digest] >= 100
        ):
            classification = "KNOWN_GENERATED"
            reference = None
        else:
            classification = "UNKNOWN"
            reference = None
        records.append(
            {
                "current_path": f"{category}/{key}",
                "size_bytes": size,
                "sha256": digest,
                "category": classification,
                "database_reference": reference,
                "proposed_s3_key": f"private/{category}/{key}" if reference else None,
                "migration_status": "LOCAL_ONLY",
                "notes": error,
            }
        )
    for keys, reference_status in (
        (current_keys, "current"),
        (historical_keys, "historical"),
    ):
        for key in sorted(keys.keys() - present):
            records.append(
                {
                    "current_path": f"{category}/{key}",
                    "size_bytes": None,
                    "sha256": None,
                    "category": "MISSING_ON_DISK",
                    "database_reference": keys[key],
                    "proposed_s3_key": None,
                    "migration_status": "BLOCKED"
                    if reference_status == "current"
                    else "HISTORICAL_REMOVAL",
                    "notes": f"{reference_status} database key has no local file",
                }
            )
    classes = Counter(record["category"] for record in records)
    summary = {
        "db_total_keys": len(current_keys) + len(historical_keys),
        "db_current_keys": len(current_keys),
        "db_historical_keys": len(historical_keys),
        "disk_files": len(files),
        "matching_current": classes["REFERENCED_CURRENT"],
        "matching_historical": classes["REFERENCED_HISTORICAL"],
        "missing_current": len(current_keys.keys() - present),
        "missing_historical": len(historical_keys.keys() - present),
        "unreferenced_disk": len(files)
        - classes["REFERENCED_CURRENT"]
        - classes["REFERENCED_HISTORICAL"],
        "classifications": {name: classes[name] for name in CLASSIFICATIONS},
    }
    return records, summary


def reconcile(settings: Settings, db: Session) -> dict[str, Any]:
    references = database_keys(db)
    report: dict[str, Any] = {"schema_version": 1, "read_only": True, "groups": {}}
    for group in GROUPS:
        root = {
            "body-photos": settings.body_photo_storage_root,
            "food-photos": settings.food_photo_storage_root,
            "profile-photos": settings.profile_photo_storage_root,
            "nutrition-labs": settings.nutrition_lab_storage_root,
        }[group]
        current, historical = references[group]
        records, summary = classify_private_files(
            category=group, root=root, current_keys=current, historical_keys=historical
        )
        report["groups"][group] = {"summary": summary, "records": records}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Detailed local JSON under backend/var/ only")
    args = parser.parse_args()
    settings = get_settings()
    with Session(get_engine(settings.database_url)) as db:
        report = reconcile(settings, db)
    if args.output is not None:
        permitted_root = (Path(__file__).resolve().parents[1] / "var").resolve()
        output = args.output.resolve()
        if not output.is_relative_to(permitted_root):
            parser.error("--output must stay under backend/var/ so private keys are not committed")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
    for group, value in report["groups"].items():
        summary = value["summary"]
        print(
            f"{group}: db={summary['db_total_keys']} disk={summary['disk_files']} "
            f"current_match={summary['matching_current']} "
            f"historical_match={summary['matching_historical']} "
            f"missing_current={summary['missing_current']} "
            f"missing_historical={summary['missing_historical']} "
            f"unknown={summary['classifications']['UNKNOWN']}"
        )


if __name__ == "__main__":
    main()
