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
    from app.debugging.release_contract import validate_release
except ModuleNotFoundError:
    from release_contract import validate_release


def archive_size(
    directory: Path, expected_manifest: str, commit: str, run_id: int
) -> int:
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
    digest = hashlib.sha256()
    with (directory / "image.tar.gz").open("rb") as stream:
        while chunk := stream.read(1048576):
            digest.update(chunk)
    if digest.hexdigest() != checksum.split()[0]:
        raise ValueError("offline_release_archive_mismatch")
    size = 0
    with gzip.open(directory / "image.tar.gz", "rb") as stream:
        while chunk := stream.read(1048576):
            size += len(chunk)
            if size > 8589934592:
                raise ValueError("offline_release_size_limit")
    return size


def load(directory: Path, expected_manifest: str, commit: str, run_id: int) -> None:
    size = archive_size(directory, expected_manifest, commit, run_id)
    if shutil.disk_usage(directory).free < size + 1073741824:
        raise ValueError("offline_release_disk_capacity_required")
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
        with gzip.open(directory / "image.tar.gz", "rb") as stream:
            shutil.copyfileobj(stream, process.stdin, length=1048576)
        process.stdin.close()
        if process.wait(timeout=600):
            raise ValueError("offline_release_load_failed")
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    print("Verified CI images loaded; running services and volumes were not changed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--ci-run-id", type=int, required=True)
    args = parser.parse_args()
    load(args.directory, args.manifest_sha256, args.commit, args.ci_run_id)


if __name__ == "__main__":
    main()
