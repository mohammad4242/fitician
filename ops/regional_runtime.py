"""Read-only regional runtime inspection and atomic marker registration."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REGIONS = {"iran": "iran", "alman": "germany"}
IRAN_SERVICES = (
    "db",
    "redis",
    "backend",
    "backend-2",
    "scheduler",
    "food-photo-worker",
    "body-analysis-worker",
    "notification-worker",
    "frontend",
    "caddy",
)
GERMANY_SERVICES = ("agent-service",)
LABEL_PROJECT = "com.docker.compose.project"
LABEL_SERVICE = "com.docker.compose.service"
LABEL_CONFIGS = "com.docker.compose.project.config_files"
WORKER_MODULES = {
    "scheduler": "app.scheduler.worker",
    "food-photo-worker": "app.nutrition.food_photo_worker",
    "body-analysis-worker": "app.body_analysis.worker",
    "notification-worker": "app.notifications.worker",
}
MAPPER_PROBE_TIMEOUT_SECONDS = 180
MAPPER_PROBE_MEMORY = "256m"
MAPPER_PROBE_CPUS = "0.25"
MAPPER_PROBE_PIDS_LIMIT = "128"
WORKER_OVERRIDE_SHA256 = (
    "95fccb2d1868926b2c2642a6b97b6ce2d833e465a90efd8e790a41aefd86e96e"
)
ROLE_SOURCE_PROOF_VERSION = "iran-worker-role-source-v1"
ROLE_SOURCE_PATHS = {
    "backend/app/body_analysis/worker.py",
    "backend/app/nutrition/food_photo_worker.py",
    "backend/app/notifications/worker.py",
    "backend/app/scheduler/worker.py",
}
IRAN_SHARED_ENV = (
    "DATABASE_URL",
    "AGENT_SERVICE_BASE_URL",
    "AGENT_SERVICE_TOKEN",
    "APP_ENV",
    "REDIS_HOST",
    "REDIS_PASSWORD",
)
WORKER_ENV = (
    "DATABASE_URL",
    "AGENT_SERVICE_BASE_URL",
    "AGENT_SERVICE_TOKEN",
    "APP_ENV",
    "REDIS_HOST",
    "REDIS_PASSWORD",
)


class RegistrationError(ValueError):
    """A runtime is not safe to adopt or its marker state conflicts."""


def _duration_ns(value: str) -> int:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(ns|us|µs|ms|s|m|h)", value)
    if not match:
        raise RegistrationError("Germany healthcheck duration is invalid")
    units = {
        "ns": 1,
        "us": 1_000,
        "µs": 1_000,
        "ms": 1_000_000,
        "s": 1_000_000_000,
        "m": 60_000_000_000,
        "h": 3_600_000_000_000,
    }
    return int(float(match.group(1)) * units[match.group(2)])


def _memory_bytes(value: str | int) -> int:
    if isinstance(value, int):
        return value
    match = re.fullmatch(r"([0-9]+)([kmg]i?|b)?", value.strip(), re.IGNORECASE)
    if not match:
        raise RegistrationError("Germany memory limit is invalid")
    scale = {
        None: 1,
        "b": 1,
        "k": 1024,
        "ki": 1024,
        "m": 1024**2,
        "mi": 1024**2,
        "g": 1024**3,
        "gi": 1024**3,
    }
    return (
        int(match.group(1)) * scale[match.group(2).lower() if match.group(2) else None]
    )


def _validate_germany_host_config(expected: dict, container: dict) -> None:
    host = container.get("HostConfig", {})
    config = container.get("Config", {})
    exact = {
        "Privileged": bool(expected.get("privileged", False)),
        "ReadonlyRootfs": bool(expected.get("read_only", False)),
        "PidsLimit": int(expected.get("pids_limit") or 0),
        "CapAdd": sorted(expected.get("cap_add") or []),
        "CapDrop": sorted(expected.get("cap_drop") or []),
        "SecurityOpt": sorted(expected.get("security_opt") or []),
    }
    for key, wanted in exact.items():
        actual = host.get(key)
        if key in {"CapAdd", "CapDrop", "SecurityOpt"}:
            actual = sorted(actual or [])
        elif key == "PidsLimit":
            actual = int(actual or 0)
        elif key in {"Privileged", "ReadonlyRootfs"}:
            actual = bool(actual)
        if actual != wanted:
            raise RegistrationError("Germany Agent host security differs from contract")

    expected_tmpfs = {}
    for mount in expected.get("tmpfs") or []:
        target, separator, options = mount.partition(":")
        expected_tmpfs[target] = options if separator else ""
    if (host.get("Tmpfs") or {}) != expected_tmpfs:
        raise RegistrationError("Germany Agent tmpfs differs from contract")
    if host.get("Devices") or host.get("DeviceRequests"):
        raise RegistrationError("Germany Agent has unexpected device access")

    if "mem_limit" in expected and int(host.get("Memory") or 0) != _memory_bytes(
        expected["mem_limit"]
    ):
        raise RegistrationError("Germany Agent memory limit differs from contract")
    if "cpus" in expected and int(host.get("NanoCpus") or 0) != round(
        float(expected["cpus"]) * 1_000_000_000
    ):
        raise RegistrationError("Germany Agent CPU limit differs from contract")
    expected_restart = expected.get("restart", "no")
    actual_restart = host.get("RestartPolicy", {}).get("Name") or "no"
    if actual_restart != expected_restart:
        raise RegistrationError("Germany Agent restart policy differs from contract")
    if "init" in expected and bool(host.get("Init")) != bool(expected["init"]):
        raise RegistrationError("Germany Agent init setting differs from contract")

    health = expected.get("healthcheck")
    if health:
        actual = config.get("Healthcheck") or {}
        if actual.get("Test") != health.get("test") or int(
            actual.get("Retries") or 0
        ) != int(health.get("retries") or 0):
            raise RegistrationError("Germany Agent healthcheck differs from contract")
        for key, actual_key in (
            ("interval", "Interval"),
            ("timeout", "Timeout"),
            ("start_period", "StartPeriod"),
        ):
            if key in health and int(actual.get(actual_key) or 0) != _duration_ns(
                str(health[key])
            ):
                raise RegistrationError(
                    "Germany Agent healthcheck differs from contract"
                )


def _runtime_config_paths(
    raw: str, app_dir: Path, region: str
) -> tuple[set[str], bool]:
    releases: set[str] = set()
    has_worker_override = False
    for value in (part.strip() for part in raw.split(",")):
        if not value:
            continue
        path = Path(value)
        override = (
            app_dir / "artifacts/request-tracing-20261018/worker-startup.override.yaml"
        )
        if region == "iran" and path == override:
            _reject_symlink_components(path, app_dir)
            if (
                not path.is_file()
                or digest(path.read_bytes()) != WORKER_OVERRIDE_SHA256
            ):
                raise RegistrationError("Historical worker startup override is invalid")
            has_worker_override = True
        else:
            releases.add(str(validate_contract_path(value, app_dir, region)))
    return releases, has_worker_override


def digest(value: bytes | str) -> str:
    data = value.encode() if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def validate_region(alias: str) -> str:
    try:
        return REGIONS[alias]
    except KeyError as error:
        raise RegistrationError("SSH alias must be iran or alman") from error


def _is_beneath(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _reject_symlink_components(path: Path, stop: Path) -> None:
    current = path
    while _is_beneath(current, stop):
        if current.is_symlink():
            raise RegistrationError("Runtime paths cannot contain symlinks")
        if current == stop:
            break
        current = current.parent


def marker_paths(app_dir: Path, region: str) -> tuple[Path, Path]:
    return (
        app_dir / f".regional-{region}-active-contract",
        app_dir / ".scalability-foundation-accepted",
    )


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in values:
            raise RegistrationError("Marker format is invalid")
        values[key] = value
    return values


def validate_contract_path(value: str, app_dir: Path, region: str) -> Path:
    root = app_dir / "releases"
    path = Path(value)
    match = re.fullmatch(r"([0-9a-f]{40})", path.parent.name)
    if (
        not path.is_absolute()
        or not match
        or path.name != f"compose.prod.{region}.yaml"
        or not _is_beneath(path, root)
    ):
        raise RegistrationError("Active contract path is invalid")
    _reject_symlink_components(path, app_dir)
    if not path.is_file():
        raise RegistrationError("Active contract file is missing")
    return path


def read_active_contract_marker(
    app_dir: Path, region: str, discovered: set[str]
) -> str | None:
    marker, _ = marker_paths(app_dir, region)
    if marker.is_symlink():
        raise RegistrationError("Active contract marker cannot be a symlink")
    if not marker.exists():
        return None
    if not marker.is_file():
        raise RegistrationError("Active contract marker is unsafe")
    value = marker.read_text(encoding="utf-8").strip()
    validate_contract_path(value, app_dir, region)
    if value not in discovered:
        raise RegistrationError(
            "Active contract marker conflicts with running services"
        )
    return value


def _container_env(container: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in container.get("Config", {}).get("Env", []):
        key, separator, value = item.partition("=")
        if separator:
            result[key] = value
    return result


def _labels(container: dict) -> dict[str, str]:
    return container.get("Config", {}).get("Labels") or {}


def _full_sha_from_ref(ref: str) -> str | None:
    tag = ref.rsplit(":", 1)[-1]
    return tag if SHA_RE.fullmatch(tag) else None


def validate_runtime_snapshot(
    *,
    alias: str,
    app_dir: Path,
    containers: list[dict],
    rendered: dict,
    image_details: dict[str, dict],
    volume_details: dict[str, dict],
    live_checks: dict,
) -> dict:
    """Validate sanitized Docker/API facts and return a safe adoption summary."""

    region = validate_region(alias)
    app_dir = Path(os.path.abspath(app_dir))
    if not app_dir.is_absolute() or app_dir.is_symlink():
        raise RegistrationError("Application directory is unsafe")
    services = IRAN_SERVICES if region == "iran" else GERMANY_SERVICES
    expected_running = [
        item
        for item in containers
        if item.get("State", {}).get("Status") == "running"
        and _labels(item).get(LABEL_SERVICE) in services
    ]
    projects = {_labels(item).get(LABEL_PROJECT) for item in expected_running}
    if len(projects) != 1 or not next(iter(projects), None):
        raise RegistrationError("Running Compose project is missing or mixed")
    project = next(iter(projects))
    running = [
        item
        for item in containers
        if item.get("State", {}).get("Status") == "running"
        and _labels(item).get(LABEL_PROJECT) == project
    ]
    if any(_labels(item).get(LABEL_SERVICE) not in services for item in running):
        raise RegistrationError(
            "Unexpected running service shares the regional project"
        )
    by_service: dict[str, list[dict]] = {}
    for container in running:
        by_service.setdefault(_labels(container)[LABEL_SERVICE], []).append(container)
    if set(by_service) != set(services) or any(
        len(by_service[name]) != 1 for name in services
    ):
        raise RegistrationError("Required regional services are missing or duplicated")

    contract_paths: set[str] = set()
    has_worker_override = False
    for container in running:
        raw = _labels(container).get(LABEL_CONFIGS, "")
        configs = [part.strip() for part in raw.split(",") if part.strip()]
        if not configs:
            raise RegistrationError("Compose service contract label is missing")
        found, has_override = _runtime_config_paths(raw, app_dir, region)
        contract_paths.update(found)
        has_worker_override |= has_override

    service_config = rendered.get("services", {})
    volumes_config = rendered.get("volumes", {})
    if set(services) - set(service_config):
        raise RegistrationError("Rendered regional service contract is incomplete")

    image_tags: dict[str, str] = {}
    image_ids: dict[str, str] = {}
    volume_names: set[str] = set()
    env_hashes: dict[str, str] = {}
    for service in services:
        item = by_service[service][0]
        expected = service_config[service]
        actual_ref = item.get("Config", {}).get("Image", "")
        expected_ref = expected.get("image", "")
        if not actual_ref or actual_ref != expected_ref:
            raise RegistrationError("Running image differs from the rendered contract")
        image_id = item.get("Image")
        if not image_id or image_details.get(actual_ref, {}).get("Id") != image_id:
            raise RegistrationError(
                "Running image identity does not match its local image"
            )
        if item.get("State", {}).get("Status") != "running":
            raise RegistrationError("A required service is not running")
        health = item.get("State", {}).get("Health", {}).get("Status")
        if expected.get("healthcheck") and health != "healthy":
            raise RegistrationError("A required service is unhealthy")
        sha = _full_sha_from_ref(actual_ref)
        if service in {
            "backend",
            "backend-2",
            "scheduler",
            "food-photo-worker",
            "body-analysis-worker",
            "notification-worker",
        }:
            if not sha:
                raise RegistrationError(
                    "Iran application image is not pinned to a full SHA"
                )
            image_tags[service] = sha
        elif service == "agent-service":
            if not sha:
                raise RegistrationError(
                    "Germany Agent image is not pinned to a full SHA"
                )
            image_tags[service] = sha
        image_ids[service] = image_id

        actual_env = _container_env(item)
        expected_env = expected.get("environment") or {}
        keys = ()
        if region == "iran" and service in {"backend", "backend-2"}:
            keys = IRAN_SHARED_ENV
        elif region == "iran" and service in {
            "body-analysis-worker",
            "food-photo-worker",
            "scheduler",
        }:
            keys = WORKER_ENV
        elif region == "germany" and service == "agent-service":
            keys = ("AGENT_SERVICE_TOKEN",)
        for key in keys:
            actual_value = actual_env.get(key)
            contract_value = expected_env.get(key)
            if (
                region == "iran"
                and service
                in {"body-analysis-worker", "food-photo-worker", "scheduler"}
                and key == "REDIS_HOST"
                and key not in actual_env
                and key not in expected_env
            ):
                continue
            if not actual_value or actual_value != contract_value:
                raise RegistrationError(
                    "A critical runtime setting differs from its contract"
                )
            env_hashes[f"{service}.{key}"] = digest(actual_value)

        mounts = {mount.get("Destination"): mount for mount in item.get("Mounts", [])}
        declared_volumes = {
            mount.get("target"): mount
            for mount in expected.get("volumes", [])
            if mount.get("type") == "volume"
        }
        for target, declared in declared_volumes.items():
            mount = mounts.get(target)
            source = declared.get("source")
            configured = volumes_config.get(source, {})
            expected_name = configured.get("name", source)
            if (
                not mount
                or mount.get("Type") != "volume"
                or mount.get("Name") != expected_name
                or mount.get("RW", not declared.get("read_only", False))
                is not (not declared.get("read_only", False))
                or volume_details.get(expected_name, {}).get("Name") != expected_name
            ):
                raise RegistrationError(
                    "A declared persistent volume does not match runtime"
                )
            if configured.get("external") is not True:
                raise RegistrationError(
                    "Regional data volumes must be declared external"
                )
            volume_names.add(expected_name)
        if region == "germany":
            if set(mounts) != set(declared_volumes):
                raise RegistrationError("Germany Agent has unexpected runtime mounts")
            _validate_germany_host_config(expected, item)

    if region == "iran":
        worker_mappers = live_checks.get("worker_mappers")
        if worker_mappers != {name: True for name in WORKER_MODULES}:
            raise RegistrationError("A worker mapper configuration probe failed")
        if has_worker_override and any(
            service_config[name].get("healthcheck", {}).get("start_period") != "120s"
            for name in WORKER_MODULES
        ):
            raise RegistrationError(
                "Canonical worker health grace differs from override"
            )
        api_sha = image_tags["backend"]
        if image_tags["backend-2"] != api_sha:
            raise RegistrationError("Iran API replicas use different image SHAs")
        worker_shas = {
            image_tags[name]
            for name in (
                "scheduler",
                "food-photo-worker",
                "body-analysis-worker",
                "notification-worker",
            )
        }
        if len(worker_shas) != 1:
            raise RegistrationError("Iran workers use different image SHAs")
        worker_sha = next(iter(worker_shas))
        app_sha = worker_sha
        if live_checks.get("api_statuses") != {
            "backend": {"livez": 200, "readyz": 200},
            "backend-2": {"livez": 200, "readyz": 200},
        }:
            raise RegistrationError("Iran API liveness or readiness check failed")
        if live_checks.get("schema_revision") != live_checks.get(
            "alembic_head"
        ) or not live_checks.get("schema_revision"):
            raise RegistrationError("Iran database schema does not match Alembic heads")
        if live_checks.get("origin_status") != 200 or not live_checks.get(
            "agent_capabilities"
        ):
            raise RegistrationError(
                "Iran origin or private Agent capability check failed"
            )
        ports = by_service["caddy"][0].get("HostConfig", {}).get("PortBindings", {})
        for port in ("80/tcp", "443/tcp"):
            bindings = ports.get(port, [])
            if not bindings or any(
                str(item.get("HostPort")) != port.split("/")[0] for item in bindings
            ):
                raise RegistrationError("Iran Caddy host port mapping is incomplete")
        domain = live_checks.get("domain")
        if not isinstance(domain, str) or not domain or "://" not in domain:
            raise RegistrationError("Iran origin domain is missing")
    else:
        app_sha = image_tags["agent-service"]
        if live_checks.get("agent_capabilities") is not True:
            raise RegistrationError("Germany Agent capability check failed")
        agent = by_service["agent-service"][0]
        all_bindings = agent.get("HostConfig", {}).get("PortBindings", {})
        bindings = all_bindings.get("9001/tcp", [])
        if (
            set(all_bindings) != {"9001/tcp"}
            or len(bindings) != 1
            or not (
                bindings[0].get("HostIp") == "127.0.0.1"
                and str(bindings[0].get("HostPort")) == "9001"
            )
        ):
            raise RegistrationError(
                "Germany Agent must bind only to loopback port 9001"
            )
        home_mount = next(
            (
                mount
                for mount in agent.get("Mounts", [])
                if mount.get("Destination") == "/home/agent"
            ),
            None,
        )
        if not home_mount or home_mount.get("Type") != "volume":
            raise RegistrationError("Germany Agent authentication volume is missing")

    summary = {
        "region": region,
        "project": project,
        "app_sha": app_sha,
        "api_sha": image_tags.get("backend", image_tags.get("agent-service")),
        "worker_sha": next(iter({image_tags[name] for name in WORKER_MODULES}))
        if region == "iran"
        else None,
        "role_versions": (
            {
                "api": image_tags["backend"],
                "worker": next(iter({image_tags[name] for name in WORKER_MODULES})),
            }
            if region == "iran"
            else {"agent": image_tags["agent-service"]}
        ),
        "contract_paths": sorted(contract_paths),
        "service_image_tags": image_tags,
        "service_image_ids": image_ids,
        "external_volumes": sorted(volume_names),
        "historical_worker_override_sha256": (
            WORKER_OVERRIDE_SHA256 if has_worker_override else None
        ),
        "critical_env_sha256": env_hashes,
        "live_checks": live_checks,
        "rendered_contract_env_sha256": digest(
            json.dumps(rendered, sort_keys=True, separators=(",", ":"))
        ),
    }
    return summary


def _run(
    args: list[str],
    *,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 45,
) -> str:
    try:
        result = subprocess.run(
            args,
            input=input_text,
            text=True,
            capture_output=True,
            check=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RegistrationError("Read-only runtime inspection failed") from error
    return result.stdout.strip()


def _docker_json(args: list[str]) -> object:
    try:
        return json.loads(_run(["docker", *args]))
    except json.JSONDecodeError as error:
        raise RegistrationError("Docker returned invalid inspection data") from error


def _container_probe(region: str, item: dict, env: dict[str, str]) -> dict:
    container_id = item["Id"]
    if region == "germany":
        code = (
            "import json,os,urllib.request; "
            "r=urllib.request.Request('http://127.0.0.1:9001/v1/capabilities', "
            "headers={'Authorization':'Bearer '+os.environ['AGENT_SERVICE_TOKEN']}); "
            "x=urllib.request.urlopen(r,timeout=8); "
            "p=json.loads(x.read()); "
            "print(json.dumps({'ok':x.status==200 and isinstance(p.get('runners'),list)}))"
        )
        result = json.loads(
            _run(["docker", "exec", container_id, "python", "-c", code])
        )
        return {"agent_capabilities": bool(result.get("ok"))}

    code = (
        "import json,urllib.request; out={}; "
        "[(out.__setitem__(p,urllib.request.urlopen('http://127.0.0.1:8000/'+p,timeout=5).status)) "
        "for p in ('livez','readyz')]; print(json.dumps(out))"
    )
    statuses = json.loads(_run(["docker", "exec", container_id, "python", "-c", code]))
    return {"api_statuses": statuses}


def _probe_worker_mappers(selected: list[dict]) -> dict[str, bool]:
    by_image: dict[str, list[str]] = {}
    for service in WORKER_MODULES:
        worker = next(i for i in selected if _labels(i)[LABEL_SERVICE] == service)
        image_id = worker.get("Image", "")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            by_image.setdefault("", []).append(service)
        else:
            by_image.setdefault(image_id, []).append(service)

    checks: dict[str, bool] = {}
    modules = "; ".join(
        f"importlib.import_module({module!r})" for module in WORKER_MODULES.values()
    )
    code = (
        "import importlib; importlib.import_module('app.main'); "
        f"{modules}; "
        "from sqlalchemy.orm import configure_mappers; configure_mappers()"
    )
    for image_id, services in by_image.items():
        if not image_id:
            checks.update({service: False for service in services})
            continue
        name = f"fitician-regional-mapper-{uuid4().hex}"
        command = [
            "docker",
            "run",
            "--pull",
            "never",
            "--name",
            name,
            "--network",
            "none",
            "--read-only",
            "--memory",
            MAPPER_PROBE_MEMORY,
            "--cpus",
            MAPPER_PROBE_CPUS,
            "--pids-limit",
            MAPPER_PROBE_PIDS_LIMIT,
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/app/var:rw,noexec,nosuid,size=16m,mode=1777",
            "--env",
            "APP_ENV=test",
            "--env",
            "DATABASE_URL=sqlite://",
            "--env",
            "TMPDIR=/app/var",
            "--entrypoint",
            "python",
            image_id,
            "-c",
            code,
        ]
        success = False
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=MAPPER_PROBE_TIMEOUT_SECONDS,
            )
            success = result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            success = False
        finally:
            try:
                cleanup = subprocess.run(
                    ["docker", "rm", "--force", name],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                success = success and cleanup.returncode == 0
            except (OSError, subprocess.SubprocessError):
                success = False
        checks.update({service: success for service in services})
    return checks


def _worker_probe_signature(item: dict) -> tuple:
    state = item.get("State", {})
    health = state.get("Health") or {}
    return (
        item.get("Id"),
        item.get("Image"),
        state.get("Status"),
        state.get("StartedAt"),
        health.get("Status"),
        item.get("RestartCount", 0),
    )


def _verify_worker_containers_unchanged(selected: list[dict]) -> None:
    for service in WORKER_MODULES:
        before = next(i for i in selected if _labels(i)[LABEL_SERVICE] == service)
        inspected = _docker_json(["inspect", before["Id"]])
        if (
            not isinstance(inspected, list)
            or len(inspected) != 1
            or _worker_probe_signature(inspected[0]) != _worker_probe_signature(before)
        ):
            raise RegistrationError(
                "Worker changed during isolated mapper qualification"
            )


def inspect_runtime(app_dir: Path, alias: str) -> dict:
    region = validate_region(alias)
    app_dir = Path(os.path.abspath(app_dir))
    _reject_symlink_components(app_dir, Path("/"))
    if not app_dir.is_dir():
        raise RegistrationError("Application directory is missing")

    raw_containers = _run(["docker", "ps", "--no-trunc", "--format", "{{json .}}"])
    try:
        containers = [
            json.loads(line) for line in raw_containers.splitlines() if line.strip()
        ]
    except json.JSONDecodeError as error:
        raise RegistrationError("Docker returned invalid container listing") from error
    items = []
    for row in containers:
        item = _docker_json(["inspect", row["ID"]])
        items.extend(item if isinstance(item, list) else [])
    wanted = IRAN_SERVICES if region == "iran" else GERMANY_SERVICES
    candidates = [
        item for item in items if item.get("State", {}).get("Status") == "running"
    ]
    expected = [
        item for item in candidates if _labels(item).get(LABEL_SERVICE) in wanted
    ]
    projects = {_labels(item).get(LABEL_PROJECT) for item in expected}
    if len(projects) != 1 or not next(iter(projects), None):
        raise RegistrationError("Unable to identify a single running regional project")
    project = next(iter(projects))
    selected = [
        item for item in candidates if _labels(item).get(LABEL_PROJECT) == project
    ]
    if any(_labels(item).get(LABEL_SERVICE) not in wanted for item in selected):
        raise RegistrationError(
            "Unexpected running service shares the regional project"
        )

    discovered = set()
    has_worker_override = False
    for item in selected:
        paths, has_override = _runtime_config_paths(
            _labels(item).get(LABEL_CONFIGS, ""), app_dir, region
        )
        discovered.update(paths)
        has_worker_override |= has_override
    if not discovered:
        raise RegistrationError(
            "Running Compose labels do not identify a release contract"
        )
    _active_marker, foundation_marker = marker_paths(app_dir, region)
    active_contract = read_active_contract_marker(app_dir, region, discovered)
    # Use the active marker when present; otherwise the primary runtime service's label.
    service_name = "backend" if region == "iran" else "agent-service"
    primary = next(
        item for item in selected if _labels(item).get(LABEL_SERVICE) == service_name
    )
    primary_configs, _ = _runtime_config_paths(
        _labels(primary).get(LABEL_CONFIGS, ""), app_dir, region
    )
    contract_path = active_contract or min(primary_configs)
    contract = validate_contract_path(contract_path, app_dir, region)
    env_file = app_dir / ".env"
    if env_file.is_symlink() or not env_file.is_file():
        raise RegistrationError("Regional environment file is unsafe or missing")
    env_hash = digest(env_file.read_bytes())
    try:
        raw_config = _run(
            [
                "docker",
                "compose",
                "-p",
                project,
                "--env-file",
                str(env_file),
                "-f",
                str(contract),
                "config",
                "--format",
                "json",
            ],
            env={
                **os.environ,
                "COMPOSE_PROJECT_NAME": project,
                "FITICIAN_ENV_FILE": str(env_file),
            },
        )
        rendered = json.loads(raw_config)
    except json.JSONDecodeError as error:
        raise RegistrationError("Rendered Compose contract is invalid") from error

    image_refs = {item.get("Config", {}).get("Image", "") for item in selected}
    image_details = {
        ref: (_docker_json(["image", "inspect", ref])[0]) for ref in image_refs if ref
    }
    volume_names = {
        mount.get("Name")
        for item in selected
        for mount in item.get("Mounts", [])
        if mount.get("Type") == "volume" and mount.get("Name")
    }
    volume_details = {
        name: (_docker_json(["volume", "inspect", name])[0]) for name in volume_names
    }
    live_checks: dict = {}
    if region == "iran":
        # Repeat API probes per replica and capture schema/origin checks without returning payloads.
        api_statuses = {}
        for item in selected:
            service = _labels(item)[LABEL_SERVICE]
            if service in {"backend", "backend-2"}:
                api_statuses[service] = _container_probe(
                    region, item, _container_env(item)
                )["api_statuses"]
        live_checks["api_statuses"] = api_statuses
        live_checks["worker_mappers"] = _probe_worker_mappers(selected)
        _verify_worker_containers_unchanged(selected)
        db = next(item for item in selected if _labels(item)[LABEL_SERVICE] == "db")
        backend = next(
            item for item in selected if _labels(item)[LABEL_SERVICE] == "backend"
        )
        revision = _run(
            [
                "docker",
                "exec",
                db["Id"],
                "sh",
                "-c",
                'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"',
            ]
        )
        heads = _run(["docker", "exec", backend["Id"], "alembic", "heads"])
        head_values = re.findall(r"(?m)^([A-Za-z0-9_]+)(?:\s|$)", heads)
        if len(head_values) != 1:
            raise RegistrationError("Alembic heads are missing or ambiguous")
        live_checks["schema_revision"] = revision
        live_checks["alembic_head"] = head_values[0]
        domain = _container_env(backend).get("FITICIAN_DOMAIN")
        if not domain:
            domain = _container_env(
                next(i for i in selected if _labels(i)[LABEL_SERVICE] == "caddy")
            ).get("FITICIAN_DOMAIN")
        if not domain:
            raise RegistrationError("FITICIAN_DOMAIN is missing")
        try:
            status = _run(
                [
                    "curl",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--output",
                    "/dev/null",
                    "--write-out",
                    "%{http_code}",
                    "--resolve",
                    f"{domain}:443:127.0.0.1",
                    "--connect-timeout",
                    "5",
                    "--max-time",
                    "15",
                    f"https://{domain}/healthz",
                ]
            )
            live_checks["origin_status"] = int(status)
        except (RegistrationError, ValueError):
            live_checks["origin_status"] = 0
        live_checks["domain"] = f"https://{domain}"
        agent = next(
            item for item in selected if _labels(item)[LABEL_SERVICE] == "backend"
        )
        env = _container_env(agent)
        base_url = env.get("AGENT_SERVICE_BASE_URL", "")
        parsed = urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise RegistrationError("Iran backend Agent mapping is not private HTTPS")
        code = (
            "import ipaddress,json,os,socket,urllib.request; "
            "u=os.environ['AGENT_SERVICE_BASE_URL']; h=__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(u).hostname; "
            "ips={x[4][0] for x in socket.getaddrinfo(h,None)}; "
            "private=bool(ips) and all(ipaddress.ip_address(x).is_private or ipaddress.ip_address(x) in ipaddress.ip_network('100.64.0.0/10') for x in ips); "
            "r=urllib.request.Request(u.rstrip('/')+'/v1/capabilities',headers={'Authorization':'Bearer '+os.environ['AGENT_SERVICE_TOKEN']}); "
            "x=urllib.request.urlopen(r,timeout=10); p=json.loads(x.read()); "
            "print(json.dumps({'ok':x.status==200 and isinstance(p.get('runners'),list) and private}))"
        )
        try:
            result = json.loads(
                _run(["docker", "exec", agent["Id"], "python", "-c", code])
            )
            live_checks["agent_capabilities"] = bool(result.get("ok"))
        except (RegistrationError, json.JSONDecodeError):
            live_checks["agent_capabilities"] = False
    else:
        agent = next(
            item for item in selected if _labels(item)[LABEL_SERVICE] == "agent-service"
        )
        live_checks.update(_container_probe(region, agent, _container_env(agent)))

    summary = validate_runtime_snapshot(
        alias=alias,
        app_dir=app_dir,
        containers=selected,
        rendered=rendered,
        image_details=image_details,
        volume_details=volume_details,
        live_checks=live_checks,
    )
    summary["active_contract"] = active_contract
    summary["discovered_contracts"] = sorted(discovered)
    summary["registration_contract"] = contract_path
    summary["env_file_sha256"] = env_hash
    summary["rendered_contract_env_sha256"] = digest(
        summary["rendered_contract_env_sha256"] + env_hash
    )
    legacy_tag = None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if key == "IMAGE_TAG" and separator:
            cleaned = value.strip().strip("\"'")
            legacy_tag = cleaned if SHA_RE.fullmatch(cleaned) else "invalid-or-non-sha"
            break
    summary["legacy_image_tag"] = legacy_tag
    summary["legacy_image_tag_stale"] = legacy_tag != summary["app_sha"]
    foundation_present = _validate_foundation_marker(
        foundation_marker, summary["app_sha"]
    )
    summary["markers"] = {
        "active_contract": "present" if active_contract else "missing",
        "scalability_acceptance": "present" if foundation_present else "missing",
    }
    summary["invariant_sha256"] = digest(
        json.dumps(summary, sort_keys=True, separators=(",", ":"))
    )
    return summary


def _active_marker_content(summary: dict, app_dir: Path, region: str) -> str:
    current = summary.get("active_contract")
    if current:
        return current
    contract = summary.get("registration_contract")
    if not contract:
        raise RegistrationError("No immutable Compose release can be registered")
    return contract


def _validate_foundation_marker(path: Path, app_sha: str) -> bool:
    if path.is_symlink():
        raise RegistrationError("Scalability marker cannot be a symlink")
    if not path.exists():
        return False
    values = parse_key_values(path.read_text(encoding="utf-8"))
    if set(values) != {
        "foundation_version",
        "image_tag",
        "evidence_run_id",
        "accepted_at",
    }:
        raise RegistrationError("Scalability marker format is invalid")
    if (
        values["foundation_version"] != "1"
        or values["image_tag"] != app_sha
        or not values["evidence_run_id"].isdigit()
    ):
        raise RegistrationError("Scalability marker conflicts with the running app")
    try:
        accepted = datetime.fromisoformat(values["accepted_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise RegistrationError("Scalability marker timestamp is invalid") from error
    if accepted.tzinfo is None or accepted > datetime.now(UTC):
        raise RegistrationError("Scalability marker timestamp is invalid")
    return True


def _validate_role_proof(current: dict, proof: dict | None) -> None:
    if current.get("region") != "iran" or current.get("api_sha") == current.get(
        "worker_sha"
    ):
        return
    changed_paths = (
        proof.get("backend_image_inputs") if isinstance(proof, dict) else None
    )
    if (
        not isinstance(proof, dict)
        or proof.get("version") != ROLE_SOURCE_PROOF_VERSION
        or proof.get("api_sha") != current.get("api_sha")
        or proof.get("worker_sha") != current.get("worker_sha")
        or proof.get("ancestor_verified") is not True
        or proof.get("entrypoint_ast_equivalent") is not True
        or not isinstance(changed_paths, list)
        or any(not isinstance(path, str) for path in changed_paths)
        or len(changed_paths) != len(set(changed_paths))
        or set(changed_paths) - ROLE_SOURCE_PATHS
    ):
        raise RegistrationError(
            "Mixed Iran API and worker roles require matching source proof"
        )


def _atomic_create(path: Path, content: str) -> bool:
    if path.is_symlink():
        raise RegistrationError("Registration target cannot be a symlink")
    if path.exists():
        if path.is_file() and path.read_text(encoding="utf-8") == content:
            return False
        raise RegistrationError(
            "Registration target already exists with different content"
        )
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temp_name)
    linked = False
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path, follow_symlinks=False)
            linked = True
        except FileExistsError as error:
            raise RegistrationError(
                "Registration target appeared during adoption"
            ) from error
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        return True
    except OSError:
        if linked:
            path.unlink(missing_ok=True)
        raise
    finally:
        temp.unlink(missing_ok=True)


def apply_registration(
    *,
    app_dir: Path,
    alias: str,
    expected_invariant_sha256: str,
    evidence: dict | None,
    accepted_at: str,
    role_proof: dict | None = None,
) -> dict:
    region = validate_region(alias)
    app_dir = Path(os.path.abspath(app_dir))
    current = inspect_runtime(app_dir, alias)
    if current["invariant_sha256"] != expected_invariant_sha256:
        raise RegistrationError("Runtime changed after read-only proof")
    _validate_role_proof(current, role_proof)
    if evidence is not None and (
        region != "iran" or evidence.get("sha") != current["app_sha"]
    ):
        raise RegistrationError("Scalability evidence does not match the live app")
    active_marker, foundation_marker = marker_paths(app_dir, region)
    active_content = _active_marker_content(current, app_dir, region) + "\n"
    foundation_exists = False
    foundation_content = ""
    if region == "iran":
        foundation_exists = _validate_foundation_marker(
            foundation_marker, current["app_sha"]
        )
        if not foundation_exists and evidence is None:
            raise RegistrationError(
                "Verified scalability evidence is required for Iran"
            )
        if not foundation_exists:
            foundation_content = (
                "foundation_version=1\n"
                f"image_tag={current['app_sha']}\n"
                f"evidence_run_id={evidence['run_id']}\n"
                f"accepted_at={accepted_at}\n"
            )
    else:
        if foundation_marker.is_symlink():
            raise RegistrationError("Scalability marker cannot be a symlink")

    backup_dir = app_dir / "backups" / "regional-runtime-registration"
    _reject_symlink_components(backup_dir, app_dir)
    if backup_dir.exists() and not backup_dir.is_dir():
        raise RegistrationError("Registration evidence directory is unsafe")
    backup_dir_created = not backup_dir.exists()
    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(backup_dir, 0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence_path = backup_dir / f"{region}-{current['app_sha']}-{stamp}.json"
    evidence_record = {
        "registered_at": accepted_at,
        "runtime": current,
        "foundation_evidence": evidence,
        "role_source_compatibility": role_proof,
    }
    evidence_content = json.dumps(evidence_record, sort_keys=True, indent=2) + "\n"
    created: list[Path] = []
    try:
        _atomic_create(evidence_path, evidence_content)
        created.append(evidence_path)
        if not active_marker.exists() and _atomic_create(active_marker, active_content):
            created.append(active_marker)
        if (
            region == "iran"
            and not foundation_exists
            and _atomic_create(foundation_marker, foundation_content)
        ):
            created.append(foundation_marker)
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        if backup_dir_created:
            backup_dir.rmdir()
        raise
    return {
        "registered": True,
        "active_contract_created": active_marker in created,
        "scalability_marker_created": foundation_marker in created,
        "evidence_path": str(evidence_path),
        "runtime_invariant_sha256": current["invariant_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alias", required=True, choices=tuple(REGIONS))
    parser.add_argument("--app-dir", required=True, type=Path)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--owner-approved", action="store_true")
    parser.add_argument("--expected-invariant-sha256")
    parser.add_argument("--evidence-b64")
    parser.add_argument("--role-proof-b64")
    parser.add_argument("--accepted-at")
    args = parser.parse_args()
    try:
        if args.probe == args.apply or args.apply != args.owner_approved:
            raise RegistrationError("Select exactly one operation")
        if args.probe:
            result = inspect_runtime(args.app_dir, args.alias)
        else:
            if not args.expected_invariant_sha256 or not args.accepted_at:
                raise RegistrationError("Apply proof inputs are incomplete")
            evidence = (
                json.loads(base64.urlsafe_b64decode(args.evidence_b64).decode("utf-8"))
                if args.evidence_b64
                else None
            )
            role_proof = (
                json.loads(
                    base64.urlsafe_b64decode(args.role_proof_b64).decode("utf-8")
                )
                if args.role_proof_b64
                else None
            )
            result = apply_registration(
                app_dir=args.app_dir,
                alias=args.alias,
                expected_invariant_sha256=args.expected_invariant_sha256,
                evidence=evidence,
                accepted_at=args.accepted_at,
                role_proof=role_proof,
            )
        print(json.dumps(result, sort_keys=True))
    except (RegistrationError, OSError, json.JSONDecodeError):
        print("Regional runtime adoption blocked", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
