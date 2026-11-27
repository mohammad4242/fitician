#!/usr/bin/env python3
"""Check all saved image layers, including deleted files, without revealing credential values."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import BinaryIO


def _scan(stream: BinaryIO, credentials: list[bytes]) -> None:
    tail = b""
    overlap = max((len(value) for value in credentials), default=1) - 1
    while chunk := stream.read(65536):
        content = tail + chunk
        if any(value in content for value in credentials):
            raise ValueError("privileged_credential_in_image")
        tail = content[-overlap:] if overlap else b""


def check_archive(stream: BinaryIO, credentials: list[bytes]) -> None:
    with tarfile.open(fileobj=stream, mode="r:*") as image:
        manifest_stream = image.extractfile("manifest.json")
        if manifest_stream is None:
            raise ValueError("image_manifest_missing")
        manifest = json.load(manifest_stream)
        for entry in manifest:
            config = image.extractfile(entry["Config"])
            if config:
                _scan(config, credentials)
            for name in entry["Layers"]:
                layer_stream = image.extractfile(name)
                if layer_stream is None:
                    raise ValueError("image_layer_missing")
                with tarfile.open(fileobj=layer_stream, mode="r|*") as layer:
                    for member in layer:
                        if member.name.endswith(".map") and not Path(
                            member.name
                        ).name.startswith(".wh."):
                            raise ValueError("private_source_map_in_image_layer")
                        if member.isfile():
                            source = layer.extractfile(member)
                            if source:
                                _scan(source, credentials)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    arguments = parser.parse_args()
    credentials = [
        value.encode()
        for name in ("SENTRY_AUTH_TOKEN", "SENTRY_API_TOKEN")
        if (value := os.environ.get(name))
    ]
    root = Path(".codex-tmp/private-release-image")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryFile(dir=root) as stream:
        subprocess.run(
            ["docker", "image", "save", arguments.image], stdout=stream, check=True
        )
        stream.seek(0)
        check_archive(stream, credentials)
    print(
        "Image layers verified: no private source maps or configured privileged credentials"
    )


if __name__ == "__main__":
    main()
