"""Deterministic, resumable migration of approved public media to object storage."""

from __future__ import annotations

import json
import mimetypes
import os
import tempfile
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import httpx

from app.media.object_keys import MediaObjectKeyError, public_object_key
from app.media.storage import ObjectStorage, ObjectStorageError, sha256_file

PUBLIC_CATEGORIES = (
    "food-catalogue",
    "meal-catalogue",
    "exercise-seed",
    "exercises",
)


@dataclass(frozen=True)
class PublicMediaRecord:
    category: str
    source_path: str
    object_key: str
    size_bytes: int
    sha256: str
    content_type: str


@dataclass(frozen=True)
class MigrationManifest:
    schema_version: int
    records: tuple[PublicMediaRecord, ...]
    total_bytes: int
    categories: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "categories": list(self.categories),
            "object_count": len(self.records),
            "total_bytes": self.total_bytes,
            "records": [asdict(record) for record in self.records],
        }


@dataclass(frozen=True)
class RemotePlan:
    new_objects: int
    identical_objects: int
    identical_keys: tuple[str, ...]
    conflicting_objects: tuple[str, ...]
    unexpected_objects: tuple[str, ...]


@dataclass(frozen=True)
class VerificationSummary:
    objects: int
    bytes: int
    sha256_verified: int
    public_readable: int
    failures: tuple[str, ...]
    unexpected_objects: tuple[str, ...]


def _category_source(media_root: Path, category: str) -> tuple[Path, str]:
    if category == "exercise-seed":
        return media_root / "exercises" / "seed", "public/exercises/seed"
    if category in {"food-catalogue", "meal-catalogue", "exercises"}:
        return media_root / category, f"public/{category}"
    raise ValueError(f"Unsupported public media category: {category}")


def category_mapping(media_root: Path, category: str) -> tuple[Path, str]:
    """Return the approved local source and stable object-key prefix."""
    return _category_source(media_root, category)


def missing_database_targets(
    manifest: MigrationManifest,
    public_paths: Iterable[str],
) -> tuple[str, ...]:
    """Find selected DB-backed paths absent from the deterministic source manifest."""
    expected = {record.object_key for record in manifest.records}
    selected = set(manifest.categories)
    missing: set[str] = set()
    for path in public_paths:
        if not path.startswith("/media/"):
            continue
        if path.startswith("/media/exercises/seed/"):
            category = "exercise-seed"
        elif path.startswith("/media/exercises/"):
            category = "exercises"
        elif path.startswith("/media/food-catalogue/"):
            category = "food-catalogue"
        elif path.startswith("/media/meal-catalogue/"):
            category = "meal-catalogue"
        else:
            continue
        if category not in selected:
            continue
        try:
            key = public_object_key(path)
        except MediaObjectKeyError:
            missing.add(path)
            continue
        if key not in expected:
            missing.add(path)
    return tuple(sorted(missing))


def build_manifest(media_root: Path, categories: Iterable[str]) -> MigrationManifest:
    media_root = media_root.resolve()
    selected = tuple(dict.fromkeys(categories))
    if not selected or any(category not in PUBLIC_CATEGORIES for category in selected):
        raise ValueError("At least one approved public media category is required")
    records: list[PublicMediaRecord] = []
    keys: set[str] = set()
    for category in selected:
        source_root, object_prefix = _category_source(media_root, category)
        if not source_root.is_dir():
            raise FileNotFoundError(f"Missing public media source directory: {category}")
        category_start = len(records)
        for source in sorted(source_root.rglob("*")):
            if source.is_symlink():
                raise ValueError(f"Symlinks are not valid public media sources: {source.name}")
            if not source.is_file():
                continue
            relative = source.relative_to(source_root)
            if category == "exercises" and relative.parts[0] == "seed":
                continue
            resolved = source.resolve()
            if not resolved.is_relative_to(source_root.resolve()):
                raise ValueError(f"Public media source escapes its category: {source.name}")
            size = source.stat().st_size
            if size == 0:
                raise ValueError(f"Public media source is empty: {source.name}")
            key = f"{object_prefix}/{relative.as_posix()}"
            if key in keys:
                raise ValueError(f"Duplicate public object key: {key}")
            keys.add(key)
            content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            records.append(
                PublicMediaRecord(
                    category=category,
                    source_path=source.relative_to(media_root).as_posix(),
                    object_key=key,
                    size_bytes=size,
                    sha256=sha256_file(source),
                    content_type=content_type,
                )
            )
        if len(records) == category_start:
            raise FileNotFoundError(f"Public media source directory is empty: {category}")
    records.sort(key=lambda item: (item.category, item.object_key))
    return MigrationManifest(1, tuple(records), sum(item.size_bytes for item in records), selected)


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=".media-s3-", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _remote_keys_for_category(storage: ObjectStorage, category: str) -> set[str]:
    _, prefix = _category_source(Path("."), category)
    keys = set(storage.list_keys(f"{prefix}/"))
    if category == "exercises":
        keys = {key for key in keys if not key.startswith("public/exercises/seed/")}
    return keys


def plan_remote(
    storage: ObjectStorage,
    manifest: MigrationManifest,
    *,
    workers: int = 8,
) -> RemotePlan:
    new_objects = 0
    identical_objects = 0
    identical_keys: list[str] = []
    conflicts: list[str] = []
    expected_by_category: dict[str, set[str]] = {
        category: set() for category in manifest.categories
    }
    remote_by_category = {
        category: _remote_keys_for_category(storage, category) for category in manifest.categories
    }
    existing_records: list[PublicMediaRecord] = []
    for record in manifest.records:
        expected_by_category[record.category].add(record.object_key)
        if record.object_key not in remote_by_category[record.category]:
            new_objects += 1
            continue
        existing_records.append(record)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(storage.head, record.object_key): record for record in existing_records
        }
        for future in as_completed(futures):
            record = futures[future]
            remote = future.result()
            if (
                remote is not None
                and remote.size_bytes == record.size_bytes
                and remote.sha256 == record.sha256
            ):
                identical_objects += 1
                identical_keys.append(record.object_key)
            else:
                conflicts.append(record.object_key)
    unexpected: list[str] = []
    for category, expected in expected_by_category.items():
        unexpected.extend(sorted(remote_by_category[category] - expected))
    return RemotePlan(
        new_objects,
        identical_objects,
        tuple(sorted(identical_keys)),
        tuple(conflicts),
        tuple(unexpected),
    )


def _state_records(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text())
    if raw.get("schema_version") != 1 or not isinstance(raw.get("records"), dict):
        raise ValueError("Invalid media migration state file")
    return cast(dict[str, dict[str, Any]], raw["records"])


def upload_manifest(
    storage: ObjectStorage,
    media_root: Path,
    manifest: MigrationManifest,
    *,
    state_path: Path,
    resume: bool,
    workers: int = 8,
) -> tuple[int, int]:
    remote_plan = plan_remote(storage, manifest, workers=workers)
    if remote_plan.conflicting_objects or remote_plan.unexpected_objects:
        raise ObjectStorageError("Remote conflicts or unexpected objects block upload")
    state = _state_records(state_path) if resume else {}
    uploaded = 0
    skipped = 0
    total = len(manifest.records)
    identical_keys = frozenset(remote_plan.identical_keys)

    def upload_one(record: PublicMediaRecord) -> tuple[PublicMediaRecord, bool]:
        source = media_root / record.source_path
        if record.object_key in identical_keys:
            return record, False
        stored = storage.put_file(
            record.object_key,
            source,
            sha256=record.sha256,
            content_type=record.content_type,
        )
        return record, stored.created

    failures: list[str] = []
    upload_order = sorted(
        manifest.records, key=lambda record: (record.size_bytes, record.object_key)
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(upload_one, record): record for record in upload_order}
        for index, future in enumerate(as_completed(futures), start=1):
            record = futures[future]
            try:
                record, created = future.result()
                uploaded += int(created)
                skipped += int(not created)
                state[record.object_key] = {
                    "sha256": record.sha256,
                    "size_bytes": record.size_bytes,
                    "status": "metadata_verified",
                }
            except (OSError, ObjectStorageError) as error:
                failures.append(f"{record.object_key}: {type(error).__name__}")
            if index == total or index % 10 == 0:
                write_json_atomic(state_path, {"schema_version": 1, "records": state})
            if index == total or index % 50 == 0:
                print(f"Processed {index}/{total} objects")
    if failures:
        raise ObjectStorageError(f"{len(failures)} public media uploads failed")
    if total == 0:
        write_json_atomic(state_path, {"schema_version": 1, "records": state})
    return uploaded, skipped


def verify_manifest(
    storage: ObjectStorage,
    manifest: MigrationManifest,
    *,
    state_path: Path,
    check_public_read: bool = True,
    workers: int = 8,
) -> VerificationSummary:
    failures: list[str] = []
    verified = 0
    public_readable = 0
    total_bytes = 0
    state = _state_records(state_path)
    client = httpx.Client(timeout=30.0, follow_redirects=True, trust_env=False)

    def verify_one(record: PublicMediaRecord) -> tuple[PublicMediaRecord, int, bool]:
        remote = storage.head(record.object_key)
        if (
            remote is None
            or remote.size_bytes != record.size_bytes
            or remote.sha256 != record.sha256
        ):
            raise ObjectStorageError("metadata mismatch")
        digest = __import__("hashlib").sha256()
        downloaded = 0
        for chunk in storage.iter_bytes(record.object_key):
            downloaded += len(chunk)
            digest.update(chunk)
        if downloaded != record.size_bytes or digest.hexdigest() != record.sha256:
            raise ObjectStorageError("downloaded content mismatch")
        readable = False
        if check_public_read:
            response = client.head(storage.public_url(record.object_key))
            if response.status_code != 200:
                raise ObjectStorageError(f"public URL returned HTTP {response.status_code}")
            readable = True
        return record, downloaded, readable

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(verify_one, record): record for record in manifest.records}
            for index, future in enumerate(as_completed(futures), start=1):
                record = futures[future]
                try:
                    record, downloaded, readable = future.result()
                    verified += 1
                    total_bytes += downloaded
                    public_readable += int(readable)
                    state[record.object_key] = {
                        "sha256": record.sha256,
                        "size_bytes": record.size_bytes,
                        "status": "verified",
                    }
                except (OSError, httpx.HTTPError, ObjectStorageError) as error:
                    failures.append(f"{record.object_key}: {type(error).__name__}")
                if index == len(manifest.records) or index % 10 == 0:
                    write_json_atomic(state_path, {"schema_version": 1, "records": state})
                if index == len(manifest.records) or index % 50 == 0:
                    print(f"Verified {index}/{len(manifest.records)} objects")
    finally:
        client.close()
    unexpected: list[str] = []
    expected_by_category = {
        category: {record.object_key for record in manifest.records if record.category == category}
        for category in manifest.categories
    }
    for category, expected in expected_by_category.items():
        unexpected.extend(sorted(_remote_keys_for_category(storage, category) - expected))
    return VerificationSummary(
        objects=len(manifest.records),
        bytes=total_bytes,
        sha256_verified=verified,
        public_readable=public_readable,
        failures=tuple(failures),
        unexpected_objects=tuple(unexpected),
    )
