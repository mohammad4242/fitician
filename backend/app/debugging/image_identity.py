"""Canonical OCI config identity across classic and containerd Docker image stores."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tarfile
import threading
from pathlib import PurePosixPath
from typing import IO, Any


def _descriptor_config(
    index: object, blobs: dict[str, tuple[dict[str, Any], int]], paths: list[str]
) -> str:
    """Follow hashed OCI descriptors when containerd omitted an unpacked config blob."""
    selected: list[str] = []
    visited: set[str] = set()

    def visit(descriptor: dict[str, Any], platform: bool, depth: int) -> None:
        digest = descriptor.get("digest")
        if depth > 8 or len(visited) > 128 or not isinstance(digest, str):
            raise ValueError("image_descriptor_invalid")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest) or digest in visited:
            raise ValueError("image_descriptor_invalid")
        visited.add(digest)
        declared = descriptor.get("platform")
        if declared is not None:
            platform = declared == {"architecture": "amd64", "os": "linux"}
            if not platform:
                return
        content, size = blobs[digest]
        if descriptor.get("size") != size or content.get("schemaVersion") != 2:
            raise ValueError("image_descriptor_invalid")
        if isinstance(content.get("manifests"), list):
            for child in content["manifests"]:
                visit(child, platform, depth + 1)
        elif platform and isinstance(content.get("config"), dict):
            config = content["config"]
            if config.get("mediaType") not in {
                "application/vnd.oci.image.config.v1+json",
                "application/vnd.docker.container.image.v1+json",
            } or not re.fullmatch(r"sha256:[a-f0-9]{64}", str(config.get("digest"))):
                raise ValueError("image_descriptor_invalid")
            value = str(config["digest"])
            if "blobs/sha256/" + value.removeprefix("sha256:") not in paths:
                raise ValueError("image_descriptor_invalid")
            selected.append(value)

    if not isinstance(index, dict) or not isinstance(index.get("manifests"), list):
        raise ValueError("image_descriptor_invalid")
    for descriptor in index["manifests"]:
        visit(descriptor, False, 0)
    if len(selected) != 1:
        raise ValueError("image_descriptor_invalid")
    return selected[0]


def canonical_config_digest(stream: IO[bytes]) -> str:
    """Read only bounded image metadata; never return environment or source content."""
    configs: dict[str, str | None] = {}
    paths: list[str] | None = None
    index: object = None
    blobs: dict[str, tuple[dict[str, Any], int]] = {}
    metadata_size = 0
    size = 0
    try:
        with tarfile.open(fileobj=stream, mode="r|") as archive:
            for count, item in enumerate(archive):
                size += item.size
                if count > 10000 or size > 8589934592:
                    raise ValueError("image_metadata_limit")
                if not item.isfile():
                    continue
                if item.name == "index.json":
                    if item.size > 32768:
                        raise ValueError("image_manifest_limit")
                    content = archive.extractfile(item)
                    assert content is not None
                    index = json.loads(content.read())
                elif item.name == "manifest.json":
                    if item.size > 32768:
                        raise ValueError("image_manifest_limit")
                    content = archive.extractfile(item)
                    assert content is not None
                    manifest = json.loads(content.read())
                    if not isinstance(manifest, list) or not 1 <= len(manifest) <= 128:
                        raise ValueError("image_manifest_invalid")
                    paths = [entry["Config"] for entry in manifest]
                    if any(
                        not isinstance(path, str)
                        or len(path) > 240
                        or PurePosixPath(path).is_absolute()
                        or ".." in PurePosixPath(path).parts
                        for path in paths
                    ) or len(set(paths)) != len(paths):
                        raise ValueError("image_manifest_invalid")
                elif re.fullmatch(r"(?:[a-f0-9]{64}\.json|blobs/sha256/[a-f0-9]{64})", item.name):
                    if item.size <= 2097152:
                        content = archive.extractfile(item)
                        assert content is not None
                        raw = content.read()
                        metadata_size += len(raw)
                        if metadata_size > 16777216:
                            raise ValueError("image_metadata_limit")
                        try:
                            config = json.loads(raw)
                        except (ValueError, UnicodeDecodeError):
                            config = None
                        configs[item.name] = None
                        digest = hashlib.sha256(raw).hexdigest()
                        if isinstance(config, dict):
                            if PurePosixPath(item.name).name.removesuffix(".json") != digest:
                                raise ValueError("image_config_checksum_mismatch")
                            blobs["sha256:" + digest] = (config, len(raw))
                        if (
                            isinstance(config, dict)
                            and config.get("architecture") == "amd64"
                            and config.get("os") == "linux"
                            and isinstance(config.get("config"), dict)
                            and isinstance(config.get("rootfs"), dict)
                        ):
                            configs[item.name] = "sha256:" + digest
                    else:
                        configs[item.name] = None
                if paths is not None and all(path in configs for path in paths):
                    selected = [configs[path] for path in paths if configs[path] is not None]
                    if len(selected) != 1:
                        raise ValueError("image_config_platform_missing_or_ambiguous")
                    return str(selected[0])
        if paths is not None and index is not None:
            return _descriptor_config(index, blobs, paths)
    except (tarfile.TarError, KeyError, TypeError, ValueError, UnicodeDecodeError):
        raise ValueError("canonical_image_config_invalid") from None
    raise ValueError("canonical_image_config_missing")


def config_digest_for_image(reference: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/_.:@-]{0,254}", reference):
        raise ValueError("image_reference_invalid")
    process = subprocess.Popen(
        ["docker", "image", "save", reference], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    timer = threading.Timer(180, process.kill)
    timer.start()
    try:
        assert process.stdout is not None
        return canonical_config_digest(process.stdout)
    finally:
        timer.cancel()
        if process.stdout:
            process.stdout.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
