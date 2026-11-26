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
from contextlib import suppress
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
try:
    from app.debugging.image_identity import (
        canonical_config_digest,
        config_digest_for_image,
        inspect_archive,
    )
    from app.debugging.release_contract import (
        validate_release,
        validate_runtime_release,
    )
except ModuleNotFoundError:
    from image_identity import canonical_config_digest, config_digest_for_image, inspect_archive
    from release_contract import validate_release, validate_runtime_release

PROJECT = "fitician-debug-runtime"
MAX_UNPACKED = 2147483648


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


def unpacked_size(archive: Path) -> int:
    try:
        info = inspect_archive(
            archive,
            max_archive_bytes=536870912,
            max_unpacked_bytes=MAX_UNPACKED,
            require_single_config=False,
        )
        return int(info["effective_unpacked_bytes"])
    except ValueError as error:
        if str(error) == "image_archive_size_limit":
            raise ValueError("runtime_archive_size_limit") from None
        raise


def docker(*args: str, timeout: int = 60) -> str:
    value = subprocess.run(
        ["docker", *args], capture_output=True, timeout=timeout, check=False
    )
    if value.returncode:
        failure = value.stderr.lower()
        family = "unknown"
        for pattern, category in (
            (b"permission denied", "filesystem_access_denied"),
            (b"read-only file system", "filesystem_read_only"),
            (b"no such image", "image_missing"),
            (b"invalid mount", "mount_invalid"),
        ):
            if pattern in failure:
                family = category
                break
        operation = (
            args[0]
            if args
            and args[0]
            in {"run", "compose", "inspect", "image", "ps", "network", "exec"}
            else "other"
        )
        print(
            json.dumps(
                {
                    "operation": operation,
                    "exit_code": value.returncode,
                    "error_family": family,
                }
            ),
            file=sys.stderr,
        )
        raise ValueError("runtime_docker_operation_failed")
    return value.stdout.decode()


def _verify_bundle_details(
    directory: Path,
    expected: str,
    commit: str,
    run_id: int,
    *,
    automation_only: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
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
    target = (
        manifest["debug_broker"]
        if automation_only and "debug_broker" in manifest
        else manifest["debug_runtime"]
    )
    archive = directory / "image.tar.gz"
    if archive.is_symlink() or not 0 < archive.stat().st_size <= 536870912:
        raise ValueError("runtime_archive_size_limit")
    try:
        info = inspect_archive(
            archive,
            max_archive_bytes=536870912,
            max_unpacked_bytes=MAX_UNPACKED,
            require_single_config=True,
            expected_sha256=target["archive_sha256"],
            mismatch_error="runtime_archive_mismatch",
        )
    except ValueError as error:
        if str(error) == "image_archive_size_limit":
            raise ValueError("runtime_archive_size_limit") from None
        raise
    if info["image_id"] != target["image_id"]:
        raise ValueError("runtime_archive_image_mismatch")
    return manifest, info


def verify_bundle(
    directory: Path,
    expected: str,
    commit: str,
    run_id: int,
    *,
    automation_only: bool = False,
) -> dict[str, Any]:
    manifest, _ = _verify_bundle_details(
        directory, expected, commit, run_id, automation_only=automation_only
    )
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


def selected_services(automation: bool, automation_only: bool) -> list[str]:
    if automation and automation_only:
        raise ValueError("runtime_service_selection_invalid")
    return (
        ["automation"]
        if automation_only
        else (["connector", "automation"] if automation else ["connector"])
    )


def verify_automation_configuration(image: str, directory: Path) -> None:
    # The operator need not be UID10001 or able to traverse the private directory.
    # Check the worker's actual read access; never read or print credential contents.
    if (
        not re.fullmatch(r"sha256:[a-f0-9]{64}", image)
        or directory.is_symlink()
        or not directory.is_dir()
    ):
        raise ValueError("runtime_automation_configuration_required")
    script = (
        "import os,stat\n"
        "for name in ('github.json','worker.json'):\n"
        " fd=os.open('/credentials/'+name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)\n"
        " try:\n"
        "  s=os.fstat(fd)\n"
        "  if (not stat.S_ISREG(s.st_mode) or stat.S_IMODE(s.st_mode)!=0o600 "
        "or s.st_uid!=10001 or s.st_gid!=10001 or s.st_size>16384): raise SystemExit(1)\n"
        " finally: os.close(fd)\n"
    )
    try:
        docker(
            "run",
            "--rm",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--user=10001:10001",
            "--memory=64m",
            "--memory-swap=64m",
            "--cpus=0.1",
            "--pids-limit=16",
            "--mount",
            f"type=bind,src={directory},dst=/credentials,readonly",
            "--entrypoint=python",
            image,
            "-c",
            script,
            timeout=20,
        )
    except (ValueError, subprocess.SubprocessError):
        raise ValueError("runtime_automation_configuration_required") from None


def non_runtime_identity(services: list[str] | None = None) -> dict[str, Any]:
    selected = services if services is not None else ["connector", "automation"]
    ids = docker("ps", "-q").split()
    if not ids:
        return {}
    return {
        item["Id"]: {"started": item["State"]["StartedAt"], "image": item["Image"]}
        for item in json.loads(docker("inspect", *ids))
        if (
            item["Config"].get("Labels", {}).get("com.docker.compose.project")
            != PROJECT
            or item["Config"].get("Labels", {}).get("com.docker.compose.service")
            not in selected
        )
    }


def capacity_budget(
    total: int,
    available: int,
    cpus: int,
    others: list[dict[str, Any]],
    automation: bool,
    *,
    connector: bool = True,
) -> dict[str, Any]:
    required = ((512 if connector else 0) + (192 if automation else 0)) * 1024**2
    memory, cpu = required, (0.25 if connector else 0) + (0.1 if automation else 0)
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


def report_rollout_failure(error: Exception, services: list[str]) -> None:
    """Emit only closed diagnostic fields, never probe output or configuration."""
    reason = str(error)
    if reason not in {
        "runtime_docker_operation_failed",
        "runtime_readiness_failed",
        "runtime_running_image_mismatch",
        "runtime_cli_version_mismatch",
    }:
        reason = "runtime_rollout_failed"
    states = []
    for service in services:
        if service not in {"connector", "automation"}:
            continue
        try:
            state = service_metadata(service).get("State", {})
            health = state.get("Health", {})
            status = state.get("Status")
            health_status = health.get("Status")
            states.append(
                {
                    "service": service,
                    "status": status
                    if status
                    in {
                        "created",
                        "running",
                        "paused",
                        "restarting",
                        "removing",
                        "exited",
                        "dead",
                    }
                    else "unknown",
                    "exit_code": state.get("ExitCode")
                    if type(state.get("ExitCode")) is int
                    else None,
                    "oom_killed": state.get("OOMKilled") is True,
                    "health": health_status
                    if health_status in {"starting", "healthy", "unhealthy"}
                    else "unknown",
                    "probe_exit_codes": [
                        probe["ExitCode"]
                        for probe in health.get("Log", [])[-3:]
                        if type(probe.get("ExitCode")) is int
                    ],
                }
            )
        except (ValueError, subprocess.SubprocessError, KeyError, TypeError):
            states.append({"service": service, "status": "unavailable"})
    print(json.dumps({"reason": reason, "services": states}), file=sys.stderr)


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
    except (ValueError, subprocess.SubprocessError) as error:
        # Observation is best effort and must never prevent recovery.
        with suppress(Exception):
            report_rollout_failure(error, services)
        try:
            prior_services = prior.get("services", services)
            added = [name for name in services if name not in prior_services]
            if added:
                compose(candidate, "stop", "--timeout", "30", *added)
            # An empty Compose service list means "all services". Never use it when
            # rolling back the first broker enrollment; stop only the new service.
            if prior_services:
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
    automation_only: bool = False,
    cleanup_archive: bool = False,
) -> dict[str, Any]:
    if not owner_approved:
        raise ValueError("runtime_owner_approval_required")
    services = selected_services(automation, automation_only)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError("existing_managed_runtime_required")
    marker = root / "managed.json"
    if (
        marker.is_symlink()
        or json.loads(marker.read_text()).get("managed_by") != PROJECT
    ):
        raise ValueError("existing_managed_runtime_required")
    # Independent broker releases must not later be rolled back as if the legacy
    # inference connector shared the same image/contract. Use component releases.
    if automation and (root / "active-automation-release.json").exists():
        raise ValueError("runtime_automation_requires_independent_rollout")
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
        manifest, footprint = _verify_bundle_details(
            directory, expected, commit, run_id, automation_only=automation_only
        )
        target_broker = bool(automation_only and "debug_broker" in manifest)
        target_meta = (
            manifest["debug_broker"] if target_broker else manifest["debug_runtime"]
        )
        target_image_id = target_meta["image_id"]
        active = root / (
            "active-automation-release.json"
            if automation_only
            else "active-release.json"
        )
        previous_active = active
        if automation_only and not active.exists():
            previous_active = root / "active-release.json"
        previous = (
            Path(json.loads(previous_active.read_text())["contract"])
            if previous_active.exists()
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
        # On first broker enrollment the existing connector supplies only the
        # rollback image anchor. It is not selected, stopped, restarted or enrolled.
        prior_row = next(iter(prior_rows.values()), None) or service_metadata(
            "connector"
        )
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
        if "automation" in services:
            verify_automation_configuration(
                prior_row["Image"], root / "automation-private"
            )
        prior_identity = non_runtime_identity(services)
        release = root / "releases" / commit
        if automation_only:
            release = release / "automation"
        if any(path.is_symlink() for path in (release, release.parent)):
            raise ValueError("runtime_private_directory_required")
        journal = release / "deployment.json"
        if journal.exists():
            receipt = json.loads(journal.read_text())
            if (
                receipt.get("state") == "deployed"
                and receipt.get("manifest_sha256") == expected
            ):
                verify_running(services, target_image_id, commit)
                if cleanup_archive and (directory / "image.tar.gz").exists():
                    (directory / "image.tar.gz").unlink()
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
            "automation" in services,
            connector="connector" in services,
        )
        existing = _existing_diff_ids()
        new_compressed = sum(
            int(entry["compressed_bytes"])
            for entry in footprint.get("layer_entries", [])
            if entry.get("diff_id") not in existing
        )
        new_unpacked = sum(
            int(entry["unpacked_bytes"])
            for entry in footprint.get("layer_entries", [])
            if entry.get("diff_id") not in existing
        )
        new_layer_delta = (
            new_compressed + new_unpacked
            if footprint["unpacked_layers_bytes"] > 0
            else footprint["effective_unpacked_bytes"]
        )
        required_disk = max(3221225472, new_layer_delta + 1610612736)
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
            "target_role": "broker" if target_broker else "runtime",
            "disk_footprint": {
                "compressed_archive_bytes": footprint["compressed_archive_bytes"],
                "outer_tar_bytes": footprint["outer_tar_bytes"],
                "unpacked_layers_bytes": footprint["unpacked_layers_bytes"],
                "new_compressed_layers_bytes": new_compressed,
                "new_unpacked_layers_bytes": new_unpacked,
                "required_disk_bytes": required_disk,
            },
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
            reference = (
                "fitician-debug-broker:"
                if target_broker
                else "fitician-debug-runtime:"
            ) + commit
            image = json.loads(docker("image", "inspect", reference))[0]
            if (
                image["Config"]
                .get("Labels", {})
                .get("org.opencontainers.image.revision")
                != commit
                or config_digest_for_image(image["Id"]) != target_image_id
            ):
                raise ValueError("runtime_loaded_image_mismatch")
            if cleanup_archive and archive.exists():
                archive.unlink()
                receipt["archive_cleaned"] = True
            contract = release / "compose.debug-runtime.yaml"
            contract.write_bytes(
                (
                    Path(__file__).resolve().parents[1] / "compose.debug-runtime.yaml"
                ).read_bytes()
            )
            contract.chmod(0o600)
            environment = release / "runtime.env"
            if target_broker:
                connector_image = prior_row["Image"] if prior_row else image["Id"]
                environment.write_text(
                    f"FITICIAN_DEBUG_RUNTIME_IMAGE={connector_image}\n"
                    f"FITICIAN_DEBUG_BROKER_IMAGE={image['Id']}\n"
                    f"FITICIAN_DEBUG_RUNTIME_ROOT={root}\n"
                )
            else:
                environment.write_text(
                    f"FITICIAN_DEBUG_RUNTIME_IMAGE={image['Id']}\nFITICIAN_DEBUG_RUNTIME_ROOT={root}\n"
                )
            environment.chmod(0o600)
            receipt["services"] = rollout(
                contract,
                previous,
                services,
                target_image_id,
                commit,
                prior,
            )
            if non_runtime_identity(services) != prior_identity:
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
    parser.add_argument("--cleanup-archive", action="store_true")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--automation", action="store_true")
    selection.add_argument("--automation-only", action="store_true")
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
            automation_only=args.automation_only,
            cleanup_archive=args.cleanup_archive,
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
