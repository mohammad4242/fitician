#!/usr/bin/env python3
"""Bind an independent debug runtime to its actual CI smoke, rollback and image evidence."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import sys
import tarfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.debugging.image_identity import canonical_config_digest
from app.debugging.release_contract import validate_runtime_release


def build_manifest(
    directory: Path,
    commit: str,
    run_id: int,
    attempt: int,
    *,
    broker_directory: Path | None = None,
) -> dict[str, Any]:
    for name in (
        "smoke.json",
        "release-smoke.json",
        "image.tar.gz.sha256",
        "image.tar.gz",
    ):
        path = directory / name
        maximum = 536870912 if name == "image.tar.gz" else 65536
        if path.is_symlink() or not path.is_file():
            raise ValueError("runtime_evidence_required")
        if path.stat().st_size > maximum:
            raise ValueError("runtime_evidence_too_large")
    spec = importlib.util.spec_from_file_location(
        "runtime_proof", ROOT / "ops/release-manifest.py"
    )
    assert spec and spec.loader
    proof = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(proof)
    identity = proof.runtime_identity(directory, commit)
    with gzip.open(directory / "image.tar.gz", "rb") as archive:
        if canonical_config_digest(archive) != identity["image_id"]:
            raise ValueError("runtime_archive_image_mismatch")
    result: dict[str, Any] = {
        "version": 1,
        "kind": "debug-runtime",
        "repository": "mohammad4242/fitician",
        "commit": commit,
        "ci_run_id": run_id,
        "run_attempt": attempt,
        "debug_runtime": identity,
    }
    if broker_directory is not None:
        for name in ("image.tar.gz.sha256", "image.tar.gz"):
            path = broker_directory / name
            maximum = 536870912 if name == "image.tar.gz" else 65536
            if path.is_symlink() or not path.is_file():
                raise ValueError("runtime_evidence_required")
            if path.stat().st_size > maximum:
                raise ValueError("runtime_evidence_too_large")
        broker = proof.broker_identity(broker_directory, directory, commit)
        with gzip.open(broker_directory / "image.tar.gz", "rb") as archive:
            if canonical_config_digest(archive) != broker["image_id"]:
                raise ValueError("runtime_archive_image_mismatch")
        result["debug_broker"] = broker
    return validate_runtime_release(result, commit=commit, ci_run_id=run_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--broker-directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--ci-run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    args = parser.parse_args()
    try:
        result = build_manifest(
            args.directory,
            args.commit,
            args.ci_run_id,
            args.run_attempt,
            broker_directory=args.broker_directory,
        )
        raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
        descriptor = os.open(
            args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        print(
            json.dumps(
                {
                    "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                    "commit": args.commit,
                    "ci_run_id": args.ci_run_id,
                }
            )
        )
    except (OSError, ValueError, TypeError, KeyError, tarfile.TarError):
        raise SystemExit(
            "Runtime manifest verification failed; no deployment performed."
        ) from None


if __name__ == "__main__":
    main()
