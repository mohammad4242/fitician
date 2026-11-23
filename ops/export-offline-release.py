#!/usr/bin/env python3
"""Export the already built Iran images; never rebuild or include runtime volumes."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.debugging.image_identity import config_digest_for_image
from app.debugging.release_contract import validate_release


def export(manifest: Path, directory: Path) -> None:
    content = manifest.read_bytes()
    if len(content) > 16384:
        raise ValueError("release_manifest_invalid")
    value = json.loads(content)
    validate_release(value, commit=value["commit"], ci_run_id=value["ci_run_id"])
    directory.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(directory).free < 1610612736:
        raise ValueError("offline_export_disk_capacity_required")
    aliases = []
    for role in ("backend", "frontend"):
        image = value["images"][role]
        observed = config_digest_for_image(image["reference"])
        if observed != image["image_id"]:
            raise ValueError("offline_export_image_mismatch")
        alias = "mohammad4242/fitician-" + role + ":" + value["commit"]
        subprocess.run(
            ["docker", "tag", image["reference"], alias],
            capture_output=True,
            check=True,
            timeout=30,
        )
        aliases.append(alias)
    archive = directory / "image.tar.gz"
    with archive.open("xb") as output:
        process = subprocess.Popen(
            ["docker", "save", *aliases],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        try:
            assert process.stdout is not None
            with gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as compressed:
                size = 0
                while chunk := process.stdout.read(1048576):
                    size += len(chunk)
                    if size > 8589934592:
                        raise ValueError("offline_export_size_limit")
                    compressed.write(chunk)
            if process.wait(timeout=30):
                raise ValueError("offline_export_failed")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            process.stdout.close()
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        while chunk := stream.read(1048576):
            digest.update(chunk)
    (directory / "image.tar.gz.sha256").write_text(
        digest.hexdigest() + "  image.tar.gz\n"
    )
    (directory / "manifest.json").write_bytes(content)
    print(
        "Exact Iran application images exported; production volumes were not accessed"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    export(args.manifest, args.directory)


if __name__ == "__main__":
    main()
