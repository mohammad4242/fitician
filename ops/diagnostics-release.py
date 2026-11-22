#!/usr/bin/env python3
"""Fixed worker lifecycle inside the existing locked regional release transaction.

No secret provisioning, network creation, image pull, volume deletion or arbitrary command API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

SERVICES = {
    "debug-worker": (512, 1.0, {"DATABASE_URL", "AI_CREDENTIAL_ENCRYPTION_KEY"}),
    "diagnostics-sync-worker": (
        256,
        0.5,
        {"DATABASE_URL", "SENTRY_ORG", "SENTRY_PROJECT", "SENTRY_API_TOKEN"},
    ),
    "diagnostics-alert-worker": (
        256,
        0.25,
        {
            "DATABASE_URL",
            "FARAZSMS_API_KEY",
            "FARAZSMS_FROM_NUMBER",
            "DIAGNOSTICS_ALERT_PHONE",
            "DIAGNOSTICS_ALERT_ENABLED",
            "DIAGNOSTICS_ALERT_ENABLED_AT",
            "FRONTEND_ORIGIN",
        },
    ),
}
ACTIVE = ".diagnostics-active.json"


def private_bytes(path: Path, limit: int = 65536) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise ValueError("diagnostics_private_file_required") from error
    with os.fdopen(descriptor, "rb") as source:
        info = os.fstat(source.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > limit
        ):
            raise ValueError("diagnostics_private_file_required")
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("diagnostics_private_file_required")
    return raw


def write_private(path: Path, value: dict) -> None:
    pending = path.with_name(path.name + ".pending")
    descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as output:
        os.fchmod(output.fileno(), 0o600)
        json.dump(value, output, sort_keys=True)
        output.flush()
        os.fsync(output.fileno())
    if path.is_symlink():
        raise ValueError("diagnostics_private_file_required")
    os.replace(pending, path)


def load_policy(app: Path) -> list[str]:
    path = app / "diagnostics-workers.json"
    if not path.exists() and not path.is_symlink():
        if (app / ACTIVE).exists():
            raise ValueError("diagnostics_policy_missing_for_active_workers")
        return []
    value = json.loads(private_bytes(path, 4096))
    if (
        not isinstance(value, dict)
        or not (
            (
                set(value) == {"version", "services"}
                and type(value.get("version")) is int
                and value["version"] == 1
            )
            or (
                set(value) == {"version", "mode", "services"}
                and type(value.get("version")) is int
                and value["version"] == 2
                and value["mode"] == "shared"
            )
        )
        or not isinstance(value["services"], list)
        or any(not isinstance(name, str) or name not in SERVICES for name in value["services"])
        or len(set(value["services"])) != len(value["services"])
        or (
            value.get("mode") == "shared"
            and "diagnostics-alert-worker" in value["services"]
            and "diagnostics-sync-worker" not in value["services"]
        )
    ):
        raise ValueError("diagnostics_policy_invalid")
    return sorted(value["services"])


def policy_mode(app: Path) -> str:
    # Validate first, including file ownership boundary and the closed schema.
    load_policy(app)
    path = app / "diagnostics-workers.json"
    if not path.exists():
        return "standalone"
    return json.loads(private_bytes(path, 4096)).get("mode", "standalone")


def shared_fingerprints(app: Path, services: list[str]) -> dict[str, str]:
    raw = private_bytes(app / "diagnostics-shared.env")
    values = {}
    allowed = {
        "DIAGNOSTICS_ENVIRONMENT",
        "DEBUG_REMOTE_DISPATCH_ENABLED",
        "DIAGNOSTICS_MAINTENANCE_ENABLED",
        "DIAGNOSTICS_ALERT_ENABLED",
        "DIAGNOSTICS_ALERT_ENABLED_AT",
        "DIAGNOSTICS_ALERT_PHONE",
        "FRONTEND_ORIGIN",
        "FARAZSMS_API_KEY",
        "FARAZSMS_FROM_NUMBER",
        "FARAZSMS_BASE_URL",
        "SENTRY_ORG",
        "SENTRY_PROJECT",
        "SENTRY_WEB_PROJECT",
        "SENTRY_MOBILE_PROJECT",
        "SENTRY_API_TOKEN",
        "SENTRY_HTTPS_PROXY",
    }
    for line in raw.decode().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in allowed or key in values or not value.strip():
            raise ValueError("diagnostics_configuration_invalid")
        values[key] = value
    expected = {
        "DIAGNOSTICS_ENVIRONMENT": "production-iran",
        "DEBUG_REMOTE_DISPATCH_ENABLED": str("debug-worker" in services).lower(),
        "DIAGNOSTICS_MAINTENANCE_ENABLED": str(bool(set(services) - {"debug-worker"})).lower(),
        "DIAGNOSTICS_ALERT_ENABLED": str("diagnostics-alert-worker" in services).lower(),
    }
    if any(values.get(key) != value for key, value in expected.items()):
        raise ValueError("diagnostics_configuration_incomplete")
    if "diagnostics-sync-worker" in services:
        if not all(values.get(key) for key in ("SENTRY_ORG", "SENTRY_PROJECT", "SENTRY_API_TOKEN")):
            raise ValueError("diagnostics_configuration_incomplete")
    elif any(values.get(key) for key in allowed if key.startswith("SENTRY_")):
        raise ValueError("diagnostics_secret_scope_invalid")
    if "diagnostics-alert-worker" in services:
        if not all(
            values.get(key)
            for key in (
                "FARAZSMS_API_KEY",
                "FARAZSMS_FROM_NUMBER",
                "DIAGNOSTICS_ALERT_PHONE",
                "DIAGNOSTICS_ALERT_ENABLED_AT",
                "FRONTEND_ORIGIN",
            )
        ):
            raise ValueError("diagnostics_configuration_incomplete")
        try:
            origin = urlsplit(values["FRONTEND_ORIGIN"])
            activation = datetime.fromisoformat(values["DIAGNOSTICS_ALERT_ENABLED_AT"])
            valid = (
                origin.scheme == "https"
                and bool(origin.hostname)
                and not origin.username
                and not origin.password
                and not origin.query
                and not origin.fragment
                and origin.path in {"", "/"}
                and activation.tzinfo is not None
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("diagnostics_configuration_incomplete")
    elif any(
        values.get(key)
        for key in allowed
        if key.startswith("FARAZSMS_")
        or key in {"DIAGNOSTICS_ALERT_PHONE", "DIAGNOSTICS_ALERT_ENABLED_AT"}
    ):
        raise ValueError("diagnostics_secret_scope_invalid")
    return {"scheduler": hashlib.sha256(raw).hexdigest()}


def scheduler_env_file(app: Path) -> str:
    if policy_mode(app) != "shared":
        environment = app / ".env"
        if environment.exists():
            # The base env keeps its existing regional permission contract. Only the new
            # diagnostics secret files require 0600. Never export or log base env values.
            with environment.open("rb") as source:
                raw = source.read(65537)
            if len(raw) > 65536:
                raise ValueError("diagnostics_configuration_invalid")
            for line in raw.decode().splitlines():
                key, separator, value = line.partition("=")
                if separator and key in {
                    "DEBUG_REMOTE_DISPATCH_ENABLED",
                    "DIAGNOSTICS_MAINTENANCE_ENABLED",
                }:
                    flag = value.split("#", 1)[0].strip().strip("\"'").lower()
                    if flag in {"1", "true", "yes", "on"}:
                        raise ValueError("diagnostics_unapproved_shared_activation")
        return "/dev/null"
    shared_fingerprints(app, load_policy(app))
    return str(app / "diagnostics-shared.env")


def desired_state(app: Path, commit: str) -> dict:
    services = load_policy(app)
    if policy_mode(app) == "shared":
        return {
            "version": 2,
            "mode": "shared",
            "commit": commit,
            "services": services,
            "config_sha256": shared_fingerprints(app, services),
        }
    return {
        "version": 1,
        "commit": commit,
        "services": services,
        "config_sha256": config_fingerprints(app, services),
    }


def state_fingerprints(app: Path, state: dict) -> dict[str, str]:
    return (
        shared_fingerprints(app, state["services"])
        if state.get("mode") == "shared"
        else config_fingerprints(app, state["services"])
    )


def check_shared_capacity(
    *,
    available_mib: float,
    load_average: float,
    cpus: int,
    scheduler_remaining_mib: float,
    disk_free: int,
) -> None:
    # Actual availability and measured cgroup consumption, not summed reservation limits.
    # Preserve 750MiB host reserve plus 256MiB uncertainty and 64MiB within the scheduler.
    if (
        available_mib < 1006
        or load_average > cpus * 0.85
        or scheduler_remaining_mib < 64
        or disk_free < 2 * 1024**3
    ):
        raise ValueError("diagnostics_capacity_exceeded")


def shared_capacity(app: Path, release: Path, project: str) -> None:
    command(
        [
            "python3",
            str(release / "ops/check-db-connection-budget.py"),
            "--compose-file",
            str(release / "compose.prod.iran.yaml"),
            "--env-file",
            str(app / ".env"),
            "--additional-worker-connections",
            "1",
        ],
        env={
            **os.environ,
            "IMAGE_TAG": release.name,
            "FITICIAN_ENV_FILE": str(app / ".env"),
            "FITICIAN_DIAGNOSTICS_ENV_FILE": scheduler_env_file(app),
        },
    )
    ids = command(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            "label=com.docker.compose.project=" + project,
            "--filter",
            "label=com.docker.compose.service=scheduler",
        ]
    ).splitlines()
    if len(ids) != 1 or not re.fullmatch("[a-f0-9]{12,64}", ids[0]):
        raise ValueError("diagnostics_service_missing_or_ambiguous")
    maximum = int(command(["docker", "inspect", "--format", "{{.HostConfig.Memory}}", ids[0]]))
    current = int(command(["docker", "exec", ids[0], "cat", "/sys/fs/cgroup/memory.current"]))
    mem = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    check_shared_capacity(
        available_mib=int(mem["MemAvailable"].split()[0]) / 1024,
        load_average=os.getloadavg()[0],
        cpus=len(os.sched_getaffinity(0)),
        scheduler_remaining_mib=(maximum - current) / 1024**2,
        disk_free=shutil.disk_usage(app).free,
    )


def config_fingerprints(app: Path, services: list[str]) -> dict[str, str]:
    result = {}
    for service in services:
        raw = private_bytes(app / (service + ".env"))
        values = {}
        for line in raw.decode().splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or not re.fullmatch("[A-Z][A-Z0-9_]*", key) or key in values:
                raise ValueError("diagnostics_configuration_invalid")
            values[key] = value
        if any(not values.get(key, "").strip() for key in SERVICES[service][2]):
            raise ValueError("diagnostics_configuration_incomplete")
        if service == "diagnostics-alert-worker":
            try:
                origin = urlsplit(values["FRONTEND_ORIGIN"])
                activation = datetime.fromisoformat(values["DIAGNOSTICS_ALERT_ENABLED_AT"])
                valid = (
                    values["DIAGNOSTICS_ALERT_ENABLED"].lower() == "true"
                    and origin.scheme == "https"
                    and bool(origin.hostname)
                    and not origin.username
                    and not origin.password
                    and not origin.query
                    and not origin.fragment
                    and origin.path in {"", "/"}
                    and activation.tzinfo is not None
                )
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("diagnostics_configuration_incomplete")
        # Each file carries only its own privileged provider credentials.
        forbidden = {
            "SENTRY_AUTH_TOKEN",
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "AWS_SECRET_ACCESS_KEY",
        }
        if service != "diagnostics-sync-worker":
            forbidden.add("SENTRY_API_TOKEN")
        if service != "diagnostics-alert-worker":
            forbidden |= {"FARAZSMS_API_KEY", "DIAGNOSTICS_ALERT_PHONE"}
        if service != "debug-worker":
            forbidden.add("AI_CREDENTIAL_ENCRYPTION_KEY")
        if any(values.get(key) for key in forbidden):
            raise ValueError("diagnostics_secret_scope_invalid")
        result[service] = hashlib.sha256(raw).hexdigest()
    return result


def command(args: list[str], *, env: dict | None = None, timeout: int = 240) -> str:
    result = subprocess.run(
        args, env=env, capture_output=True, text=True, timeout=timeout, check=False
    )
    if result.returncode:
        # Compose stderr can contain interpolated credentials. Never relay it.
        raise ValueError("diagnostics_command_failed")
    return result.stdout.strip()


def compose(
    app: Path,
    release: Path,
    project: str,
    commit: str,
    services: list[str],
    args: list[str],
) -> str:
    env = {key: os.environ[key] for key in ("PATH", "HOME", "DOCKER_CONFIG") if key in os.environ}
    env.update(
        FITICIAN_DEBUG_IMAGE="mohammad4242/fitician-backend:" + commit,
        FITICIAN_DEBUG_ENV_FILE=str(app / "debug-worker.env")
        if "debug-worker" in services
        else "/dev/null",
        FITICIAN_SYNC_ENV_FILE=str(app / "diagnostics-sync-worker.env")
        if "diagnostics-sync-worker" in services
        else "/dev/null",
        FITICIAN_ALERT_ENV_FILE=str(app / "diagnostics-alert-worker.env")
        if "diagnostics-alert-worker" in services
        else "/dev/null",
        FITICIAN_DEBUG_NETWORK=project + "_default",
        DIAGNOSTICS_ENVIRONMENT="production-iran",
    )
    return command(
        [
            "docker",
            "compose",
            "-p",
            project + "-diagnostics",
            "--env-file",
            "/dev/null",
            "-f",
            str(release / "compose.debugging.yaml"),
            *args,
            *services,
        ],
        env=env,
    )


def check_capacity(
    services: list[str],
    *,
    core_memory: float,
    other_memory: float,
    host_memory: float,
    core_cpu: float,
    other_cpu: float,
    host_cpus: float,
    disk_free: int,
) -> None:
    if (
        core_memory + other_memory + sum(SERVICES[name][0] for name in services) + 750 > host_memory
        or core_cpu + other_cpu + sum(SERVICES[name][1] for name in services) > host_cpus * 1.5
        or disk_free < 2 * 1024**3
    ):
        raise ValueError("diagnostics_capacity_exceeded")


def capacity(app: Path, release: Path, project: str, services: list[str]) -> None:
    env = {
        **os.environ,
        "IMAGE_TAG": release.name,
        "FITICIAN_ENV_FILE": str(app / ".env"),
    }
    # The overlay fixes each dedicated worker to one DB connection with no overflow.
    # Reuse the regional connection-budget contract instead of silently adding pools.
    try:
        command(
            [
                "python3",
                str(release / "ops/check-db-connection-budget.py"),
                "--compose-file",
                str(release / "compose.prod.iran.yaml"),
                "--env-file",
                str(app / ".env"),
                "--additional-worker-connections",
                str(len(services)),
            ],
            env=env,
        )
    except ValueError:
        raise ValueError("diagnostics_database_budget_check_failed") from None
    rendered = json.loads(
        command(
            [
                "docker",
                "compose",
                "--env-file",
                str(app / ".env"),
                "-f",
                str(release / "compose.prod.iran.yaml"),
                "config",
                "--format",
                "json",
            ],
            env=env,
        )
    )
    core = [value for name, value in rendered["services"].items() if name != "migrations"]
    ids = command(["docker", "ps", "-q"]).splitlines()
    others = []
    if ids:
        # Format excludes all container environment and arbitrary log content.
        raw = command(
            [
                "docker",
                "inspect",
                "--format",
                "{{json .HostConfig.Memory}} {{json .HostConfig.NanoCpus}} "
                '{{json (index .Config.Labels "com.docker.compose.project")}}',
                *ids,
            ]
        )
        for line in raw.splitlines():
            memory, cpu, owner = line.split(" ", 2)
            if json.loads(owner) not in {project, project + "-diagnostics"}:
                if int(memory) <= 0 or int(cpu) <= 0:
                    raise ValueError("diagnostics_unbounded_existing_service")
                others.append((int(memory) / 1024**2, int(cpu) / 10**9))
    mem = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    check_capacity(
        services,
        core_memory=sum(int(value["mem_limit"]) / 1024**2 for value in core),
        core_cpu=sum(float(value["cpus"]) for value in core),
        other_memory=sum(value[0] for value in others),
        other_cpu=sum(value[1] for value in others),
        host_memory=int(mem["MemTotal"].split()[0]) / 1024,
        host_cpus=len(os.sched_getaffinity(0)),
        disk_free=shutil.disk_usage(app).free,
    )


def load_state(app: Path, path: Path | None = None) -> dict | None:
    path = path or app / ACTIVE
    if not path.exists() and not path.is_symlink():
        return None
    value = json.loads(private_bytes(path))
    if (
        not isinstance(value, dict)
        or not (
            (
                set(value) == {"version", "commit", "services", "config_sha256"}
                and value.get("version") == 1
            )
            or (
                set(value) == {"version", "mode", "commit", "services", "config_sha256"}
                and value.get("version") == 2
                and value["mode"] == "shared"
            )
        )
        or not isinstance(value["commit"], str)
        or not re.fullmatch("[a-f0-9]{40}", value["commit"])
        or not isinstance(value["services"], list)
        or any(name not in SERVICES for name in value["services"])
        or len(set(value["services"])) != len(value["services"])
        or set(value["config_sha256"])
        != ({"scheduler"} if value.get("mode") == "shared" else set(value["services"]))
    ):
        raise ValueError("diagnostics_state_invalid")
    return value


def save_previous(app: Path, commit: str) -> None:
    path = app / (".diagnostics-before-" + commit + ".json")
    if path.exists():
        raise ValueError("diagnostics_release_requires_reconciliation")
    write_private(path, {"previous": load_state(app)})


def pause(app: Path, project: str, state: dict | None) -> None:
    if state and state["services"]:
        shared = state.get("mode") == "shared"
        # Called only inside the explicitly authorized full release transaction.
        # Quiesce shared loops before schema changes; core rollback owns restart.
        for name in ["scheduler"] if shared else state["services"]:
            ids = command(
                [
                    "docker",
                    "ps",
                    "-q",
                    "--filter",
                    "label=com.docker.compose.project="
                    + (project if shared else project + "-diagnostics"),
                    "--filter",
                    "label=com.docker.compose.service=" + name,
                ]
            ).splitlines()
            if any(not re.fullmatch("[a-f0-9]{12,64}", identifier) for identifier in ids):
                raise ValueError("diagnostics_service_identity_invalid")
            if ids:
                command(["docker", "stop", "--time", "30", *ids])


def verify(app: Path, project: str, state: dict) -> None:
    if state_fingerprints(app, state) != state["config_sha256"]:
        raise ValueError("diagnostics_configuration_changed")
    if not state["services"]:
        return
    image = "mohammad4242/fitician-backend:" + state["commit"]
    image_id = command(["docker", "image", "inspect", "--format", "{{.Id}}", image])
    shared = state.get("mode") == "shared"
    for name in ["scheduler"] if shared else state["services"]:
        ids = command(
            [
                "docker",
                "ps",
                "-q",
                "--filter",
                "label=com.docker.compose.project="
                + (project if shared else project + "-diagnostics"),
                "--filter",
                "label=com.docker.compose.service=" + name,
            ]
        ).splitlines()
        if len(ids) != 1:
            raise ValueError("diagnostics_service_missing_or_ambiguous")
        observed = command(
            [
                "docker",
                "inspect",
                "--format",
                "{{.Image}} {{.State.Status}} "
                "{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}",
                ids[0],
            ]
        )
        if observed != image_id + " running healthy":
            raise ValueError("diagnostics_running_release_unverified")

    if shared:
        for role in state["services"]:
            heartbeat = "debug-dispatch" if role == "debug-worker" else role
            command(
                [
                    "docker",
                    "exec",
                    ids[0],
                    "python",
                    "-m",
                    "app.jobs.heartbeat",
                    "--path",
                    "/run/fitician/" + heartbeat + ".json",
                    "--service",
                    heartbeat,
                    "--max-age-seconds",
                    "45",
                ]
            )


def activate(app: Path, project: str, state: dict) -> None:
    if state_fingerprints(app, state) != state["config_sha256"]:
        raise ValueError("diagnostics_configuration_changed")
    if not state["services"]:
        return
    if state.get("mode") == "shared":
        # Core regional deployment already started the exact scheduler image.
        # Allow bounded startup without ever starting independent diagnostics services.
        for attempt in range(30):
            try:
                verify(app, project, state)
                return
            except ValueError:
                if attempt == 29:
                    raise
                time.sleep(1)
        return
    release = app / "releases" / state["commit"]
    manifest = json.loads((release / "manifest.json").read_bytes())
    command(
        [
            "python3",
            str(release / "ops/release-image-guard.py"),
            "--manifest",
            str(release / "manifest.json"),
            "--commit",
            state["commit"],
            "--ci-run-id",
            str(manifest["ci_run_id"]),
            "--target",
            "iran",
            "--kind",
            "full",
            "--mode",
            "verify-local",
            "--project",
            project,
        ]
    )
    compose(
        app,
        release,
        project,
        state["commit"],
        state["services"],
        ["up", "-d", "--pull", "never", "--no-deps", "--wait", "--wait-timeout", "180"],
    )
    verify(app, project, state)


def rollback(app: Path, project: str, commit: str) -> None:
    snapshot = app / (".diagnostics-before-" + commit + ".json")
    previous = json.loads(private_bytes(snapshot))["previous"]
    pause(app, project, load_state(app))
    if previous:
        # Validate the stored previous state before it can select a release path.
        previous_path = app / (".diagnostics-restore-" + commit + ".json")
        write_private(previous_path, previous)
        previous = load_state(app, previous_path)
        activate(app, project, previous)
        write_private(app / ACTIVE, previous)
        previous_path.unlink()
    else:
        (app / ACTIVE).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=(
            "preflight",
            "pause",
            "start",
            "rollback",
            "quiesce",
            "verify",
            "env-file",
        ),
    )
    parser.add_argument("--app-dir", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    try:
        if (
            not re.fullmatch("[a-f0-9]{40}", args.commit)
            or not re.fullmatch("[A-Za-z0-9][A-Za-z0-9_-]{0,60}", args.project)
            or not args.app_dir.is_absolute()
        ):
            raise ValueError("diagnostics_target_invalid")
        app = args.app_dir
        if args.mode == "env-file":
            print(scheduler_env_file(app))
            return 0
        if args.mode == "quiesce":
            pause(app, args.project, load_state(app))
            return 0
        if args.mode == "rollback":
            snapshot = app / (".diagnostics-before-" + args.commit + ".json")
            if snapshot.exists():
                rollback(app, args.project, args.commit)
                return 0
            if (app / ACTIVE).exists():
                raise ValueError("diagnostics_release_requires_reconciliation")
            return 0
        services = load_policy(app)
        if not services and not (app / ACTIVE).exists():
            print("Diagnostics workers disabled; no explicit activation policy")
            return 0
        state = desired_state(app, args.commit)
        previous = load_state(app)
        if previous and previous.get("mode", "standalone") != state.get("mode", "standalone"):
            raise ValueError("diagnostics_mode_transition_requires_reconciliation")
        if args.mode == "preflight":
            if state.get("mode") == "shared":
                shared_capacity(app, app / "releases" / args.commit, args.project)
            else:
                capacity(app, app / "releases" / args.commit, args.project, services)
        elif args.mode == "pause":
            save_previous(app, args.commit)
            pause(app, args.project, load_state(app))
        elif args.mode == "start":
            # Persist intent before external I/O; rollback can stop partially started workers.
            write_private(app / ACTIVE, state)
            activate(app, args.project, state)
        elif args.mode == "verify":
            active = load_state(app)
            if active != state:
                raise ValueError("diagnostics_running_release_unverified")
            verify(app, args.project, state)
        print("Diagnostics worker lifecycle verified: " + args.mode)
        return 0
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as error:
        # No exception bodies: filesystem/configuration/provider output may contain secrets.
        code = (
            str(error)
            if re.fullmatch("diagnostics_[a-z_]+", str(error))
            else "diagnostics_lifecycle_failed"
        )
        print(code)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
