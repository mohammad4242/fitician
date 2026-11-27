"""Canonical OCI config identity across classic and containerd Docker image stores."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
import threading
import zlib
from pathlib import Path, PurePosixPath
from typing import IO, Any, cast


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


class _HashingReader:
    def __init__(self, stream: IO[bytes], max_bytes: int) -> None:
        self.stream = stream
        self.max_bytes = max_bytes
        self.bytes_read = 0
        self.digest = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        chunk = self.stream.read(size)
        if chunk:
            self.bytes_read += len(chunk)
            if self.bytes_read > self.max_bytes:
                raise ValueError("image_archive_size_limit")
            self.digest.update(chunk)
        return chunk


class _CountingReader:
    def __init__(self, stream: IO[bytes], max_bytes: int) -> None:
        self.stream = stream
        self.max_bytes = max_bytes
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        chunk = self.stream.read(size)
        if chunk:
            self.bytes_read += len(chunk)
            if self.bytes_read > self.max_bytes:
                raise ValueError("image_archive_size_limit")
        return chunk


def _layer_member_sizes(
    stream: IO[bytes], declared_size: int, running_unpacked: int, max_unpacked: int
) -> tuple[int, int]:
    head = stream.read(2)
    if head != b"\x1f\x8b":
        if running_unpacked + declared_size > max_unpacked:
            raise ValueError("image_archive_size_limit")
        return declared_size, declared_size

    class _Prefixed:
        def __init__(self, prefix: bytes, rest: IO[bytes]) -> None:
            self._buf = prefix
            self._rest = rest

        def readable(self) -> bool:
            return True

        def read(self, size: int = -1) -> bytes:
            if size == 0:
                return b""
            if self._buf:
                if size is None or size < 0 or size >= len(self._buf):
                    out = self._buf
                    self._buf = b""
                    if size is not None and size > len(out):
                        out += self._rest.read(size - len(out))
                    return out
                out = self._buf[:size]
                self._buf = self._buf[size:]
                return out
            return self._rest.read(size)

    unpacked = 0
    with gzip.GzipFile(fileobj=cast(IO[bytes], _Prefixed(head, stream)), mode="rb") as inner:
        while chunk := inner.read(1048576):
            unpacked += len(chunk)
            if running_unpacked + unpacked > max_unpacked:
                raise ValueError("image_archive_size_limit")
    return declared_size, unpacked


def inspect_archive(
    archive: Path,
    *,
    max_archive_bytes: int = 8589934592,
    max_unpacked_bytes: int = 8589934592,
    existing_diff_ids: set[str] | None = None,
    require_single_config: bool = True,
    expected_sha256: str | None = None,
    mismatch_error: str = "image_archive_mismatch",
) -> dict[str, Any]:
    """Verify compressed SHA256 first, then inspect image identity and outer/inner layer bytes."""
    archive_hash = hashlib.sha256()
    compressed_bytes = 0
    with archive.open("rb") as raw_check:
        while chunk := raw_check.read(1048576):
            compressed_bytes += len(chunk)
            if compressed_bytes > max_archive_bytes:
                raise ValueError("image_archive_size_limit")
            archive_hash.update(chunk)
    archive_sha256 = archive_hash.hexdigest()
    if expected_sha256 is not None and archive_sha256 != expected_sha256:
        raise ValueError(mismatch_error)

    configs: dict[str, str | None] = {}
    config_diff_ids: dict[str, list[str]] = {}
    manifest: list[dict[str, Any]] | None = None
    index: object = None
    blobs: dict[str, tuple[dict[str, Any], int]] = {}
    member_sizes: dict[str, tuple[int, int]] = {}
    metadata_size = 0
    total_layer_unpacked = 0

    with archive.open("rb") as raw_file:
        hashing = _HashingReader(raw_file, max_archive_bytes)
        try:
            with gzip.GzipFile(fileobj=cast(IO[bytes], hashing), mode="rb") as gz_stream:
                counting = _CountingReader(cast(IO[bytes], gz_stream), max_unpacked_bytes)
                with tarfile.open(fileobj=cast(IO[bytes], counting), mode="r|") as tar:
                    for count, item in enumerate(tar):
                        if count > 10000:
                            raise ValueError("image_metadata_limit")
                        if not item.isfile():
                            continue
                        if item.name == "index.json":
                            if item.size > 32768:
                                raise ValueError("image_manifest_limit")
                            content = tar.extractfile(item)
                            assert content is not None
                            index = json.loads(content.read())
                        elif item.name == "manifest.json":
                            if item.size > 32768:
                                raise ValueError("image_manifest_limit")
                            content = tar.extractfile(item)
                            assert content is not None
                            parsed = json.loads(content.read())
                            if not isinstance(parsed, list) or not 1 <= len(parsed) <= 128:
                                raise ValueError("image_manifest_invalid")
                            paths = [entry["Config"] for entry in parsed]
                            if any(
                                not isinstance(path, str)
                                or len(path) > 240
                                or PurePosixPath(path).is_absolute()
                                or ".." in PurePosixPath(path).parts
                                for path in paths
                            ) or len(set(paths)) != len(paths):
                                raise ValueError("image_manifest_invalid")
                            manifest = parsed
                        elif re.fullmatch(
                            r"(?:[a-f0-9]{64}\.json|blobs/sha256/[a-f0-9]{64})", item.name
                        ):
                            content = tar.extractfile(item)
                            assert content is not None
                            if item.size <= 2097152:
                                raw = content.read()
                                metadata_size += len(raw)
                                if metadata_size > 16777216:
                                    raise ValueError("image_metadata_limit")
                                try:
                                    config = json.loads(raw)
                                except (ValueError, UnicodeDecodeError):
                                    config = None
                                if isinstance(config, dict) and (
                                    "schemaVersion" in config
                                    or "rootfs" in config
                                    or "architecture" in config
                                ):
                                    configs[item.name] = None
                                    digest = hashlib.sha256(raw).hexdigest()
                                    if (
                                        PurePosixPath(item.name).name.removesuffix(".json")
                                        != digest
                                    ):
                                        raise ValueError("image_config_checksum_mismatch")
                                    blobs["sha256:" + digest] = (config, len(raw))
                                    if (
                                        config.get("architecture") == "amd64"
                                        and config.get("os") == "linux"
                                        and isinstance(config.get("config"), dict)
                                        and isinstance(config.get("rootfs"), dict)
                                    ):
                                        configs[item.name] = "sha256:" + digest
                                        diff_ids = config["rootfs"].get("diff_ids")
                                        if isinstance(diff_ids, list):
                                            config_diff_ids[item.name] = [
                                                str(x) for x in diff_ids
                                            ]
                                    continue
                                # Small tar/gzip layer blob under blobs/sha256/
                                comp_sz, unp_sz = _layer_member_sizes(
                                    io.BytesIO(raw),
                                    len(raw),
                                    total_layer_unpacked,
                                    max_unpacked_bytes,
                                )
                                total_layer_unpacked += unp_sz
                                member_sizes[item.name] = (comp_sz, unp_sz)
                            else:
                                comp_sz, unp_sz = _layer_member_sizes(
                                    content, item.size, total_layer_unpacked, max_unpacked_bytes
                                )
                                total_layer_unpacked += unp_sz
                                member_sizes[item.name] = (comp_sz, unp_sz)
                        elif item.name.endswith((".tar", ".tar.gz", "/layer.tar")):
                            content = tar.extractfile(item)
                            assert content is not None
                            comp_sz, unp_sz = _layer_member_sizes(
                                content, item.size, total_layer_unpacked, max_unpacked_bytes
                            )
                            total_layer_unpacked += unp_sz
                            member_sizes[item.name] = (comp_sz, unp_sz)
                while counting.read(1048576):
                    pass
        except (
            OSError,
            tarfile.TarError,
            KeyError,
            TypeError,
            UnicodeDecodeError,
            zlib.error,
            EOFError,
        ):
            raise ValueError("canonical_image_config_invalid") from None
        while hashing.read(1048576):
            pass

    if hashing.digest.hexdigest() != archive_sha256:
        raise ValueError(mismatch_error)

    image_id: str | None = None
    if require_single_config:
        if manifest is None:
            raise ValueError("canonical_image_config_missing")
        paths = [entry["Config"] for entry in manifest]
        if all(path in configs for path in paths):
            selected = [configs[path] for path in paths if configs[path] is not None]
            if len(selected) != 1:
                raise ValueError("image_config_platform_missing_or_ambiguous")
            image_id = str(selected[0])
        elif index is not None:
            image_id = _descriptor_config(index, blobs, paths)
        else:
            raise ValueError("canonical_image_config_missing")

    seen_layers: set[str] = set()
    compressed_layers_bytes = 0
    unpacked_layers_bytes = 0
    new_compressed_layers_bytes = 0
    new_unpacked_layers_bytes = 0
    layer_entries: list[dict[str, Any]] = []
    known = existing_diff_ids or set()
    if manifest is not None:
        for entry in manifest:
            layers = entry.get("Layers") or []
            diff_ids = config_diff_ids.get(entry.get("Config", ""), [])
            for idx, layer_path in enumerate(layers):
                if not isinstance(layer_path, str) or layer_path in seen_layers:
                    continue
                seen_layers.add(layer_path)
                comp_sz, unp_sz = member_sizes.get(layer_path, (0, 0))
                compressed_layers_bytes += comp_sz
                unpacked_layers_bytes += unp_sz
                diff_id = diff_ids[idx] if idx < len(diff_ids) else None
                layer_entries.append(
                    {
                        "diff_id": diff_id,
                        "compressed_bytes": comp_sz,
                        "unpacked_bytes": unp_sz,
                    }
                )
                if diff_id is None or diff_id not in known:
                    new_compressed_layers_bytes += comp_sz
                    new_unpacked_layers_bytes += unp_sz

    return {
        "archive_sha256": hashing.digest.hexdigest(),
        "compressed_archive_bytes": hashing.bytes_read,
        "outer_tar_bytes": counting.bytes_read,
        "compressed_layers_bytes": compressed_layers_bytes,
        "unpacked_layers_bytes": unpacked_layers_bytes,
        "new_compressed_layers_bytes": new_compressed_layers_bytes,
        "new_unpacked_layers_bytes": new_unpacked_layers_bytes,
        "layer_entries": layer_entries,
        "effective_unpacked_bytes": max(counting.bytes_read, unpacked_layers_bytes),
        "image_id": image_id,
    }


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
