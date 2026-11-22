#!/usr/bin/env python3
"""Owner-gated replacement of the existing independent runtime, never the generation service."""

from __future__ import annotations

import argparse
import fcntl
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
try:
    from app.debugging.image_identity import (
        canonical_config_digest,
        config_digest_for_image,
    )
    from app.debugging.release_contract import (
        validate_release,
        validate_runtime_release,
    )
except ModuleNotFoundError:
    from image_identity import canonical_config_digest, config_digest_for_image
    from release_contract import validate_release, validate_runtime_release

PROJECT = "fitician-debug-runtime"
MAX_UNPACKED = 2147483648


def unpacked_size(archive: Path) -> int:
    size = 0
    with gzip.open(archive, "rb") as stream:
        while chunk := stream.read(1048576):
            size += len(chunk)
            if size > MAX_UNPACKED:
                raise ValueError("runtime_archive_size_limit")
    return size


def docker(*args: str, timeout: int = 60) -> str:
    value = subprocess.run(
        ["docker", *args], capture_output=True, timeout=timeout, check=False
    )
    if value.returncode:
        raise ValueError("runtime_docker_operation_failed")
    return value.stdout.decode()


def verify_bundle(
    directory: Path, expected: str, commit: str, run_id: int
) -> dict[str, Any]:
    file = directory / "manifest.json"
    if file.is_symlink() or file.stat().st_size > 16384:
        raise ValueError("runtime_manifest_invalid")
    raw = file.read_bytes()
    if (
        not re.fullmatch(r"[a-f0-9]{64}", expected)
        or hashlib.sha256(raw).hexdigest() != expected
    ):
        raise ValueError("runtime_manifest_mismatch")
    value = json.loads(raw)
    validator = (
        validate_runtime_release
        if isinstance(value, dict) and value.get("kind") == "debug-runtime"
        else validate_release
    )
    manifest = validator(value, commit=commit, ci_run_id=run_id)
    archive = directory / "image.tar.gz"
    if archive.is_symlink() or not 0 < archive.stat().st_size <= 536870912:
        raise ValueError("runtime_archive_size_limit")
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        while chunk := stream.read(1048576):
            digest.update(chunk)
    if digest.hexdigest() != manifest["debug_runtime"]["archive_sha256"]:
        raise ValueError("runtime_archive_mismatch")
    unpacked_size(archive)
    with gzip.open(archive, "rb") as stream:
        identity = canonical_config_digest(stream)
    if identity != manifest["debug_runtime"]["image_id"]:
        raise ValueError("runtime_archive_image_mismatch")
    return manifest


def compose(contract: Path, *args: str) -> str:
    return docker(
        "compose",
        "-p",
        PROJECT,
        "--env-file",
        str(contract.parent / "runtime.env"),
        "-f",
        str(contract),
        "--profile",
        "automation",
        *args,
        timeout=120,
    )


def compose_up(contract: Path, services: list[str]) -> None:
    compose(contract, "up", "-d", "--no-deps", "--pull", "never", *services)


def service_metadata(service: str) -> dict[str, Any]:
    rows = docker(
        "ps",
        "-a",
        "--filter",
        f"label=com.docker.compose.project={PROJECT}",
        "--filter",
        f"label=com.docker.compose.service={service}",
        "--format",
        "{{.ID}}",
    ).split()
    if len(rows) != 1:
        raise ValueError("runtime_service_identity_unavailable")
    return json.loads(docker("inspect", rows[0]))[0]


def non_runtime_identity() -> dict[str, Any]:
    ids = docker("ps", "-q").split()
    if not ids:
        return {}
    return {
        item["Id"]: {"started": item["State"]["StartedAt"], "image": item["Image"]}
        for item in json.loads(docker("inspect", *ids))
        if item["Config"].get("Labels", {}).get("com.docker.compose.project") != PROJECT
    }


def capacity_budget(
    total: int,
    available: int,
    cpus: int,
    others: list[dict[str, Any]],
    automation: bool,
) -> dict[str, Any]:
    required = (512 + (192 if automation else 0)) * 1024**2
    memory, cpu = required, 0.25 + (0.1 if automation else 0)
    for row in others:
        host = row["HostConfig"]
        limit = host.get("Memory", 0)
        quota = host.get("NanoCpus", 0) / 1e9
        if not quota and host.get("CpuQuota", 0) > 0:
            quota = host["CpuQuota"] / (host.get("CpuPeriod") or 100000)
        if limit <= 0 or quota <= 0:
            raise ValueError("runtime_existing_resource_budget_unknown")
        memory += limit
        cpu += quota
    if memory + 384 * 1024**2 > total or available < required + 128 * 1024**2:
        raise ValueError("runtime_memory_capacity_required")
    if cpu > cpus * 1.5:
        raise ValueError("runtime_cpu_capacity_required")
    return {
        "planned_memory_mib": memory // 1024**2,
        "planned_cpu_limits": round(cpu, 3),
    }


def verify_running(services: list[str], image_id: str, commit: str) -> dict[str, Any]:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        rows = {name: service_metadata(name) for name in services}
        if any(
            row["State"].get("Status") in {"exited", "dead"} for row in rows.values()
        ):
            raise ValueError("runtime_readiness_failed")
        if all(
            v["State"].get("Health", {}).get("Status") == "healthy"
            for v in rows.values()
        ):
            break
        time.sleep(1)
    else:
        raise ValueError("runtime_readiness_failed")
    result: dict[str, Any] = {}
    for name, row in rows.items():
        if (
            not row["State"]["Running"]
            or row["HostConfig"].get("Privileged")
            or row["Config"].get("User") != "10001:10001"
            or not row["HostConfig"].get("ReadonlyRootfs")
            or row["Config"].get("Labels", {}).get("org.opencontainers.image.revision")
            != commit
            or config_digest_for_image(row["Image"]) != image_id
        ):
            raise ValueError("runtime_running_image_mismatch")
        result[name] = {
            "container_id": row["Id"],
            "image_id": image_id,
            "commit": commit,
            "healthy": True,
        }
    if "connector" in rows:
        version = docker(
            "exec", rows["connector"]["Id"], "/usr/local/bin/codex", "--version"
        ).strip()
        if version != "codex-cli 0.167.2":
            raise ValueError("runtime_cli_version_mismatch")
    return result


def rollout(
    candidate: Path,
    previous: Path,
    services: list[str],
    image_id: str,
    commit: str,
    prior: dict[str, Any],
) -> dict[str, Any]:
    try:
        compose_up(candidate, services)
        return verify_running(services, image_id, commit)
    except (ValueError, subprocess.SubprocessError):
        try:
            prior_services = prior.get("services", services)
            added = [name for name in services if name not in prior_services]
            if added:
                compose(candidate, "stop", "--timeout", "30", *added)
            compose_up(previous, prior_services)
            verify_running(prior_services, prior["image_id"], prior["commit"])
        except (ValueError, subprocess.SubprocessError):
            raise ValueError("runtime_rollback_unconfirmed") from None
        raise ValueError("runtime_rollout_rolled_back") from None


def save(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".new")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(value, output, sort_keys=True)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def deploy(
    root: Path,
    directory: Path,
    expected: str,
    commit: str,
    run_id: int,
    regional_lock: Path,
    *,
    owner_approved: bool,
    automation: bool = False,
) -> dict[str, Any]:
    if not owner_approved:
        raise ValueError("runtime_owner_approval_required")
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError("existing_managed_runtime_required")
    marker = root / "managed.json"
    if (
        marker.is_symlink()
        or json.loads(marker.read_text()).get("managed_by") != PROJECT
    ):
        raise ValueError("existing_managed_runtime_required")
    for name in (
        "state",
        "private",
        "automation-state",
        "automation-private",
        "releases",
    ):
        if (root / name).is_symlink():
            raise ValueError("runtime_private_directory_required")
    if (
        not regional_lock.is_absolute()
        or regional_lock.is_symlink()
        or not regional_lock.parent.is_dir()
    ):
        raise ValueError("regional_deployment_lock_required")
    lock = os.open(regional_lock, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("regional_deployment_in_progress") from None
        manifest = verify_bundle(directory, expected, commit, run_id)
        services = ["connector", "automation"] if automation else ["connector"]
        if automation:
            for name in ("github.json", "worker.json"):
                file = root / "automation-private" / name
                if (
                    file.is_symlink()
                    or not file.is_file()
                    or file.stat().st_mode & 0o077
                ):
                    raise ValueError("runtime_automation_configuration_required")
        active = root / "active-release.json"
        previous = (
            Path(json.loads(active.read_text())["contract"])
            if active.exists()
            else root / "current/compose.debug-runtime.yaml"
        )
        if (
            root not in previous.resolve().parents
            or not previous.is_file()
            or not previous.with_name("runtime.env").is_file()
        ):
            raise ValueError("runtime_previous_contract_required")
        prior_rows = {
            name: service_metadata(name)
            for name in services
            if name == "connector"
            or docker(
                "ps",
                "-a",
                "--filter",
                f"label=com.docker.compose.project={PROJECT}",
                "--filter",
                f"label=com.docker.compose.service={name}",
                "-q",
            ).strip()
        }
        prior_row = prior_rows["connector"]
        prior_commit = (
            prior_row["Config"]
            .get("Labels", {})
            .get("org.opencontainers.image.revision", "")
        )
        if not re.fullmatch(r"[a-f0-9]{40}", prior_commit):
            raise ValueError("runtime_previous_image_identity_required")
        prior = {
            "commit": prior_commit,
            "image_id": config_digest_for_image(prior_row["Image"]),
            "services": list(prior_rows),
        }
        prior_identity = non_runtime_identity()
        release = root / "releases" / commit
        journal = release / "deployment.json"
        if journal.exists():
            receipt = json.loads(journal.read_text())
            if (
                receipt.get("state") == "deployed"
                and receipt.get("manifest_sha256") == expected
            ):
                verify_running(services, manifest["debug_runtime"]["image_id"], commit)
                return receipt
            raise ValueError("runtime_previous_attempt_requires_reconciliation")
        memory = {
            line.split()[0].rstrip(":"): int(line.split()[1]) * 1024
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith(("MemAvailable:", "MemTotal:"))
        }
        ids = list(prior_identity)
        others = json.loads(docker("inspect", *ids)) if ids else []
        capacity_budget(
            memory["MemTotal"],
            memory["MemAvailable"],
            os.cpu_count() or 1,
            others,
            automation,
        )
        required_disk = max(
            3221225472, unpacked_size(directory / "image.tar.gz") + 1610612736
        )
        if shutil.disk_usage(root).free < required_disk:
            raise ValueError("runtime_disk_capacity_required")
        release.mkdir(mode=0o700, parents=True, exist_ok=False)
        receipt = {
            "commit": commit,
            "ci_run_id": run_id,
            "manifest_sha256": expected,
            "state": "preparing",
            "production_application_changed": False,
            "business_outcome_verified": False,
            "panel_execution_verified": False,
            "previous_contract": str(previous),
        }
        save(journal, receipt)
        try:
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
                    raise ValueError("runtime_image_load_failed")
            finally:
                timer.cancel()
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
            reference = "fitician-debug-runtime:" + commit
            image = json.loads(docker("image", "inspect", reference))[0]
            if (
                image["Config"]
                .get("Labels", {})
                .get("org.opencontainers.image.revision")
                != commit
                or config_digest_for_image(image["Id"])
                != manifest["debug_runtime"]["image_id"]
            ):
                raise ValueError("runtime_loaded_image_mismatch")
            contract = release / "compose.debug-runtime.yaml"
            contract.write_bytes(
                (
                    Path(__file__).resolve().parents[1] / "compose.debug-runtime.yaml"
                ).read_bytes()
            )
            contract.chmod(0o600)
            environment = release / "runtime.env"
            environment.write_text(
                f"FITICIAN_DEBUG_RUNTIME_IMAGE={image['Id']}\nFITICIAN_DEBUG_RUNTIME_ROOT={root}\n"
            )
            environment.chmod(0o600)
            receipt["services"] = rollout(
                contract,
                previous,
                services,
                manifest["debug_runtime"]["image_id"],
                commit,
                prior,
            )
            if non_runtime_identity() != prior_identity:
                raise ValueError("unrelated_service_identity_changed")
            save(
                active,
                {
                    "contract": str(contract),
                    "commit": commit,
                    "manifest_sha256": expected,
                },
            )
            receipt["state"] = "deployed"
        except Exception as error:  # noqa: BLE001 - persist only closed secret-safe failure codes
            # Never store raw Docker output, auth paths, environment values or exception text.
            allowed = {
                "runtime_rollout_rolled_back",
                "runtime_rollback_unconfirmed",
                "runtime_loaded_image_mismatch",
                "runtime_image_load_failed",
                "unrelated_service_identity_changed",
            }
            receipt.update(
                state="failed_or_uncertain",
                error_code=str(error)
                if str(error) in allowed
                else "runtime_release_interrupted",
            )
            save(journal, receipt)
            raise ValueError(receipt["error_code"]) from None
        save(journal, receipt)
        return receipt
    finally:
        os.close(lock)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--ci-run-id", type=int, required=True)
    parser.add_argument("--regional-lock", type=Path, required=True)
    parser.add_argument("--owner-approved", action="store_true")
    parser.add_argument("--automation", action="store_true")
    args = parser.parse_args()
    try:
        result = deploy(
            args.root,
            args.directory,
            args.manifest_sha256,
            args.commit,
            args.ci_run_id,
            args.regional_lock,
            owner_approved=args.owner_approved,
            automation=args.automation,
        )
        print(json.dumps(result))
    except Exception as error:  # noqa: BLE001 - never emit raw subprocess/metadata error bodies
        # Only controlled codes reach stderr; never subprocess/error bodies.
        code = str(error)
        raise SystemExit(
            code
            if re.fullmatch(r"[a-z_]{1,80}", code)
            else "runtime_release_unavailable"
        ) from None


if __name__ == "__main__":
    main()
