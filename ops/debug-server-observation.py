#!/usr/bin/env python3
"""Fixed read-only regional evidence. Never expose Docker env, arbitrary commands or raw logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path

TARGETS = {
    "iran": (
        "fitician-iran",
        (
            "backend",
            "backend-2",
            "frontend",
            "db",
            "redis",
            "body-analysis-worker",
            "food-photo-worker",
            "notification-worker",
            "scheduler",
            "caddy",
        ),
    ),
    "germany": ("fitician-agent", ("agent-service",)),
}
FORMAT = (
    '{"container_id":{{json .Id}},"image_id":{{json .Image}},'
    '"status":{{json .State.Status}},"restart_count":{{json .RestartCount}},'
    '"health":{{if index .State "Health"}}{{json (index (index .State "Health") "Status")}}{{else}}null{{end}}}'
)
WORKERS = {"debug-worker", "diagnostics-sync-worker", "diagnostics-alert-worker"}


def optional_workers(
    path: Path = Path("/opt/fitician-iran/diagnostics-workers.json"),
) -> list[str]:
    if not path.exists() and not path.is_symlink():
        return []
    try:
        if (
            path.is_symlink()
            or not path.is_file()
            or stat.S_IMODE(path.stat().st_mode) != 0o600
        ):
            raise ValueError
        if path.stat().st_size > 4096:
            raise ValueError
        value = json.loads(path.read_bytes())
        names = value["services"]
        if (
            set(value) != {"version", "services"}
            or type(value["version"]) is not int
            or value["version"] != 1
            or not isinstance(names, list)
            or any(not isinstance(name, str) or name not in WORKERS for name in names)
            or len(set(names)) != len(names)
        ):
            raise ValueError
        return sorted(names)
    except (ValueError, KeyError, TypeError, OSError):
        raise ValueError("observation_worker_policy_invalid") from None


def command(args: list[str], *, limit: int = 65536) -> str:
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    timer = threading.Timer(8, process.kill)
    timer.start()
    try:
        assert process.stdout is not None
        data = process.stdout.read(limit + 1)
        if len(data) > limit:
            raise ValueError("observation_output_limit")
        if process.wait(timeout=3):
            raise ValueError("observation_command_failed")
        return data.decode("utf-8", errors="replace").strip()
    finally:
        timer.cancel()
        if process.stdout is not None:
            process.stdout.close()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=3)


def correlated_logs(raw: str, trace: str | None) -> list[dict[str, str]]:
    if trace is None:
        return []
    rows = []
    for line in raw.splitlines()[-60:]:
        # Docker timestamps precede JSON logger records. Unstructured messages are omitted.
        line = line[line.find("{") :] if "{" in line else ""
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if not isinstance(item, dict) or item.get("trace_id") != trace:
            continue
        row = {"trace_id": trace}
        for key in ("request_id", "operation_id", "job_id"):
            value = item.get(key)
            if isinstance(value, str) and re.fullmatch(
                r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", value
            ):
                row[key] = value
        code = item.get("error_code")
        if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", code):
            row["error_code"] = code
        level = item.get("level")
        if level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            row["level"] = level
        rows.append(row)
    return rows[-20:]


def baseline(services: list[dict], revision: list[str]) -> str:
    identity = [
        {key: service.get(key) for key in ("service", "container_id", "image_id")}
        for service in services
    ]
    identity.sort(key=lambda row: row["service"])
    return hashlib.sha256(
        json.dumps(
            [identity, sorted(revision)], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def observe(target: str, trace: str | None = None) -> dict:
    if target not in TARGETS or (
        trace is not None and not re.fullmatch("[a-f0-9]{32}", trace)
    ):
        raise ValueError("observation_target_or_trace_invalid")
    project, names = TARGETS[target]
    if target == "iran":
        names += tuple(optional_workers())
    services = []
    revision = []
    missing = []
    remaining_log_events = 20
    for service in names:
        row = {
            "service": service,
            "status": "unavailable",
            "logs": [],
            "logs_state": "correlation_required" if trace is None else "not_collected",
        }
        try:
            identifiers = command(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    "label=com.docker.compose.project="
                    + (project + "-diagnostics" if service in WORKERS else project),
                    "--filter",
                    "label=com.docker.compose.service=" + service,
                    "--format",
                    "{{.ID}}",
                ]
            ).splitlines()
            if len(identifiers) != 1 or not re.fullmatch(
                "[a-f0-9]{12,64}", identifiers[0]
            ):
                raise ValueError("observation_service_missing_or_ambiguous")
            identifier = identifiers[0]
            metadata = json.loads(
                command(["docker", "inspect", "--format", FORMAT, identifier])
            )
            if not re.fullmatch(
                "sha256:[a-f0-9]{64}", metadata.get("image_id", "")
            ) or not re.fullmatch("[a-f0-9]{64}", metadata.get("container_id", "")):
                raise ValueError("observation_identity_invalid")
            row.update(metadata)
            try:
                label = command(
                    [
                        "docker",
                        "image",
                        "inspect",
                        "--format",
                        '{{index .Config.Labels "org.opencontainers.image.revision"}}',
                        row["image_id"],
                    ]
                )
            except (ValueError, subprocess.SubprocessError):
                label = ""
            row["commit"] = label if re.fullmatch("[a-f0-9]{40}", label) else None
            row["release_provenance"] = "image_label" if row["commit"] else "unknown"
            if target == "iran" and service == "db":
                text = command(
                    [
                        "docker",
                        "exec",
                        identifier,
                        "sh",
                        "-c",
                        'exec psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version_num FROM alembic_version ORDER BY version_num"',
                    ]
                )
                revision = text.splitlines()
                if not revision or any(
                    not re.fullmatch("[A-Za-z0-9_]{1,64}", version)
                    for version in revision
                ):
                    raise ValueError("observation_database_revision_invalid")
            if trace is not None and service not in ("db", "redis", "caddy"):
                try:
                    row["logs"] = correlated_logs(
                        command(
                            ["docker", "logs", "--since=15m", "--tail=60", identifier]
                        ),
                        trace,
                    )
                    row["logs"] = row["logs"][:remaining_log_events]
                    remaining_log_events -= len(row["logs"])
                    row["logs_state"] = "filtered_json_only"
                except ValueError:
                    row["logs_state"] = "unavailable_or_limit_exceeded"
        except (ValueError, KeyError, TypeError, subprocess.SubprocessError):
            missing.append(service)
        services.append(row)
    memory = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("MemAvailable", "MemTotal"):
            memory[key] = int(value.strip().split()[0]) * 1024
    return {
        "schema_version": 1,
        "target_environment": "production-" + target,
        "captured_at": datetime.now(UTC).isoformat(),
        "services": services,
        "database_revision": revision,
        "baseline_sha256": baseline(services, revision),
        "complete": not missing,
        "missing_services": missing,
        "capacity": {
            "cpu_count": os.cpu_count(),
            "memory": memory,
            "root_disk_free_bytes": shutil.disk_usage("/").free,
        },
        "provenance": "fixed_read_only_host_collector",
        "business_outcome_verified": False,
        "limitations": [
            "Image labels are not registry-digest verification.",
            "Only correlated allowlisted JSON log fields are exported; unstructured logs are omitted.",
            "Service health does not prove a business workflow succeeded.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=tuple(TARGETS), required=True)
    parser.add_argument("--trace-id")
    args = parser.parse_args()
    print(json.dumps(observe(args.target, args.trace_id), sort_keys=True))


if __name__ == "__main__":
    main()
