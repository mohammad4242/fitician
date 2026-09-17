"""Current-reference-only private media migration helpers."""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.media.object_keys import MediaObjectKeyError, private_object_key
from app.media.storage import ObjectStorageError, S3ObjectStorage, sha256_file

PRIVATE_CATEGORIES = ("body-photos", "food-photos", "profile-photos", "nutrition-labs")


@dataclass(frozen=True)
class PrivateMediaRecord:
    category: str
    storage_key: str
    object_key: str
    source: Path
    size_bytes: int
    sha256: str


def _roots(settings: Settings) -> dict[str, Path]:
    return {
        "body-photos": settings.body_photo_storage_root,
        "food-photos": settings.food_photo_storage_root,
        "profile-photos": settings.profile_photo_storage_root,
        "nutrition-labs": settings.nutrition_lab_storage_root,
    }


def build_private_manifest(
    settings: Settings,
    current_keys: dict[str, set[str]],
    *,
    categories: tuple[str, ...] = PRIVATE_CATEGORIES,
) -> tuple[tuple[PrivateMediaRecord, ...], tuple[str, ...]]:
    roots = _roots(settings)
    records: list[PrivateMediaRecord] = []
    missing: list[str] = []
    for category in categories:
        if category not in roots:
            raise ValueError(f"Unsupported private media category: {category}")
        root = roots[category].resolve()
        for storage_key in sorted(current_keys.get(category, set())):
            try:
                object_key = private_object_key(category, storage_key)
            except MediaObjectKeyError as error:
                raise ValueError("Invalid current private storage key") from error
            source = (root / storage_key).resolve(strict=False)
            if not source.is_relative_to(root) or not source.is_file():
                missing.append(f"{category}:{storage_key}")
                continue
            records.append(
                PrivateMediaRecord(
                    category=category,
                    storage_key=storage_key,
                    object_key=object_key,
                    source=source,
                    size_bytes=source.stat().st_size,
                    sha256=sha256_file(source),
                )
            )
    return tuple(records), tuple(sorted(missing))


def remote_conflicts(
    storage: S3ObjectStorage,
    records: tuple[PrivateMediaRecord, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    new: list[str] = []
    conflicts: list[str] = []
    for record in records:
        remote = storage.head(record.object_key)
        if remote is None:
            new.append(record.object_key)
            continue
        remote_hash = remote.sha256
        if remote_hash is None and remote.size_bytes == record.size_bytes:
            digest = hashlib.sha256()
            for chunk in storage.iter_bytes(record.object_key):
                digest.update(chunk)
            remote_hash = digest.hexdigest()
        if remote.size_bytes != record.size_bytes or remote_hash != record.sha256:
            conflicts.append(record.object_key)
    return tuple(new), tuple(sorted(conflicts))


def upload_private_manifest(
    storage: S3ObjectStorage,
    records: tuple[PrivateMediaRecord, ...],
) -> tuple[int, int]:
    new, conflicts = remote_conflicts(storage, records)
    if conflicts:
        raise ObjectStorageError("Private remote conflicts block upload")
    new_keys = frozenset(new)
    uploaded = 0
    skipped = 0
    for record in records:
        if record.object_key not in new_keys:
            skipped += 1
            continue
        storage.put_file(
            record.object_key,
            record.source,
            sha256=record.sha256,
            content_type=_content_type(record.source),
        )
        uploaded += 1
    return uploaded, skipped


def verify_private_manifest(
    storage: S3ObjectStorage,
    records: tuple[PrivateMediaRecord, ...],
) -> tuple[int, int]:
    def verify_one(record: PrivateMediaRecord) -> int:
        remote = storage.head(record.object_key)
        if remote is None or remote.size_bytes != record.size_bytes:
            raise ObjectStorageError("Private object metadata verification failed")
        digest = hashlib.sha256()
        downloaded = 0
        for chunk in storage.iter_bytes(record.object_key):
            downloaded += len(chunk)
            digest.update(chunk)
        if downloaded != record.size_bytes or digest.hexdigest() != record.sha256:
            raise ObjectStorageError("Private object content verification failed")
        return downloaded

    if not records:
        return 0, 0
    with ThreadPoolExecutor(max_workers=min(8, len(records))) as executor:
        verified_bytes = tuple(executor.map(verify_one, records))
    return len(verified_bytes), sum(verified_bytes)


def _content_type(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }.get(path.suffix.lower(), "application/octet-stream")
