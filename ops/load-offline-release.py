#!/usr/bin/env python3
"""Verify the CI manifest/archive before loading content-addressed application images."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
try:
    from app.debugging.image_identity import inspect_archive
    from app.debugging.release_contract import validate_release
except ModuleNotFoundError:
    from image_identity import inspect_archive
    from release_contract import validate_release


def _existing_diff_ids() -> set[str]:
    try:
        ids = subprocess.run(
            ["docker", "image", "ls", "-aq"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        ).stdout.split()
        if not ids:
            return set()
        raw = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{json .RootFS.Layers}}", *ids],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        ).stdout
        diff_ids: set[str] = set()
        for line in raw.splitlines():
            line = line.strip()
            if line:
                diff_ids.update(json.loads(line))
        return diff_ids
    except (OSError, ValueError, subprocess.SubprocessError):
        return set()


def _archive_footprint(
    directory: Path, expected_manifest: str, commit: str, run_id: int
) -> tuple[int, list[dict[str, object]]]:
    raw = (directory / "manifest.json").read_bytes()
    if len(raw) > 16384 or hashlib.sha256(raw).hexdigest() != expected_manifest:
        raise ValueError("offline_release_manifest_mismatch")
    validate_release(json.loads(raw), commit=commit, ci_run_id=run_id)
    checksum = (directory / "image.tar.gz.sha256").read_text()
    if (
        len(checksum) > 100
        or len(checksum.split()) != 2
        or checksum.split()[1] != "image.tar.gz"
    ):
        raise ValueError("offline_release_checksum_invalid")
    archive = directory / "image.tar.gz"
    expected_sha256 = checksum.split()[0]
    try:
        info = inspect_archive(
            archive,
            max_archive_bytes=8589934592,
            max_unpacked_bytes=8589934592,
            require_single_config=False,
            expected_sha256=expected_sha256,
            mismatch_error="offline_release_archive_mismatch",
        )
        total_layers = info["compressed_layers_bytes"] + info["unpacked_layers_bytes"]
        return (
            int(total_layers if info["unpacked_layers_bytes"] > 0 else info["outer_tar_bytes"]),
            list(info["layer_entries"]),
        )
    except ValueError as error:
        if str(error) == "image_archive_size_limit":
            raise ValueError("offline_release_size_limit") from None
        if str(error) != "canonical_image_config_invalid":
            raise
        # Non-tar gzip fixtures remain supported while enforcing the exact checksum and limit.
        digest = hashlib.sha256()
        with archive.open("rb") as stream:
            while chunk := stream.read(1048576):
                digest.update(chunk)
        if digest.hexdigest() != checksum.split()[0]:
            raise ValueError("offline_release_archive_mismatch")
        size = 0
        with gzip.open(archive, "rb") as stream:
            while chunk := stream.read(1048576):
                size += len(chunk)
                if size > 8589934592:
                    raise ValueError("offline_release_size_limit")
        return size, []


def archive_size(
    directory: Path, expected_manifest: str, commit: str, run_id: int
) -> int:
    size, _ = _archive_footprint(directory, expected_manifest, commit, run_id)
    return size


def load(
    directory: Path,
    expected_manifest: str,
    commit: str,
    run_id: int,
    *,
    cleanup_archive: bool = False,
) -> None:
    size, entries = _archive_footprint(directory, expected_manifest, commit, run_id)
    if entries:
        existing = _existing_diff_ids()
        size = sum(
            int(entry["compressed_bytes"]) + int(entry["unpacked_bytes"])
            for entry in entries
            if entry.get("diff_id") not in existing
        )
    if shutil.disk_usage(directory).free < size + 1073741824:
        raise ValueError("offline_release_disk_capacity_required")
    archive = directory / "image.tar.gz"
    process = subprocess.Popen(
        ["docker", "load"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    timer = threading.Timer(600, process.kill)
    timer.start()
    try:
        assert process.stdin is not None
        with gzip.open(archive, "rb") as stream:
            shutil.copyfileobj(stream, process.stdin, length=1048576)
        process.stdin.close()
        if process.wait(timeout=600):
            raise ValueError("offline_release_load_failed")
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    if cleanup_archive and archive.exists():
        archive.unlink()
    print("Verified CI images loaded; running services and volumes were not changed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--ci-run-id", type=int, required=True)
    parser.add_argument("--cleanup-archive", action="store_true")
    args = parser.parse_args()
    load(
        args.directory,
        args.manifest_sha256,
        args.commit,
        args.ci_run_id,
        cleanup_archive=args.cleanup_archive,
    )


if __name__ == "__main__":
    main()
