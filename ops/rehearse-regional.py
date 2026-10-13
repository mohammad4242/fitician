#!/usr/bin/env python3
"""Run an offline Iran rehearsal with an explicit, separate Compose project."""

from __future__ import annotations

import argparse
import json
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "fitician-offline-rehearsal"
SERVICES = {
    "db",
    "redis",
    "migrations",
    "backend",
    "backend-2",
    "food-photo-worker",
    "body-analysis-worker",
    "scheduler",
    "notification-worker",
    "frontend",
    "caddy",
}


def compose_command(env_file: Path) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-name",
        PROJECT,
        "--env-file",
        str(env_file),
        "-f",
        str(ROOT / "compose.prod.iran.yaml"),
        "-f",
        str(ROOT / "ops/compose.offline-rehearsal.yaml"),
    ]


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("name") != PROJECT:
        raise ValueError("a separate rehearsal project is required")
    networks = config.get("networks", {})
    if set(networks) != {"default"} or networks["default"].get("internal") is not True:
        raise ValueError("the rehearsal requires one internal network")
    services = config.get("services", {})
    if set(services) != SERVICES:
        raise ValueError("unexpected rehearsal service topology")
    volumes = config.get("volumes", {})
    if len(volumes) != 4 or any(
        not volume.get("external")
        or not volume.get("name", "").startswith("fitician_offline_rehearsal_")
        for volume in volumes.values()
    ):
        raise ValueError("only explicitly provisioned rehearsal volumes are allowed")
    if len({volume["name"] for volume in volumes.values()}) != len(volumes):
        raise ValueError("storage roles require distinct rehearsal volumes")
    storage_targets = {
        "db": {"/var/lib/postgresql"},
        "redis": {"/data"},
        "caddy": {"/data", "/config"},
    }
    memory = 0
    cpus = 0.0
    for name, service in services.items():
        if set(service.get("networks", {})) != {"default"}:
            raise ValueError("every rehearsal service must remain on its internal network")
        if service.get("container_name"):
            raise ValueError("explicit shared container names are forbidden")
        required_targets = storage_targets.get(name, set())
        found_targets = set()
        for mount in service.get("volumes", []):
            if mount.get("type") == "volume" and mount.get("source") not in volumes:
                raise ValueError("every named mount must use a dedicated rehearsal volume")
            if mount.get("target") in required_targets:
                if mount.get("type") != "volume" or mount.get("source") not in volumes:
                    raise ValueError("persistent storage must use a dedicated rehearsal volume")
                found_targets.add(mount["target"])
        if found_targets != required_targets:
            raise ValueError("persistent storage requires a dedicated rehearsal volume")
        ports = service.get("ports", [])
        if name != "caddy" and ports:
            raise ValueError("only loopback Caddy ports may be published")
        if name == "caddy" and (
            len(ports) != 2
            or {str(port.get("published")) for port in ports} != {"18080", "18443"}
            or any(port.get("host_ip") != "127.0.0.1" for port in ports)
        ):
            raise ValueError("Caddy publication must remain loopback-only")
        if name in SERVICES - {"db", "redis", "frontend", "caddy"}:
            url = urlsplit(service.get("environment", {}).get("DATABASE_URL", ""))
            if url.hostname != "db" or url.path != "/fitician_offline_rehearsal":
                raise ValueError("application commands must use only the synthetic rehearsal DB")
        budget = int(service.get("mem_limit", 0))
        cpu = float(service.get("cpus", 0))
        if budget <= 0 or cpu <= 0:
            raise ValueError("all services require explicit memory and CPU limits")
        memory += budget
        cpus += cpu
    if services["db"]["environment"].get("POSTGRES_DB") != "fitician_offline_rehearsal":
        raise ValueError("PostgreSQL must use the synthetic rehearsal DB")
    return {"project": PROJECT, "memory_mib": memory // (1024 * 1024), "cpu_caps": cpus}


def rendered_config(env_file: Path) -> dict[str, Any]:
    if env_file.is_symlink() or not env_file.is_file():
        raise ValueError("a protected rehearsal env file is required")
    if stat.S_IMODE(env_file.stat().st_mode) != 0o600:
        raise ValueError("rehearsal env permissions must be 0600")
    result = subprocess.run(
        [*compose_command(env_file), "config", "--format", "json"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Compose render failed; environment values are suppressed")
    return json.loads(result.stdout)


def verify_capacity(budget: dict[str, Any]) -> None:
    info = subprocess.run(
        ["docker", "info", "--format", "{{json .}}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    host = json.loads(info.stdout)
    others = 0
    running = subprocess.check_output(["docker", "ps", "--quiet"], text=True).split()
    if running:
        containers = json.loads(subprocess.check_output(["docker", "inspect", *running]))
        for container in containers:
            labels = container["Config"].get("Labels") or {}
            if labels.get("com.docker.compose.project") == PROJECT:
                continue
            limit = container["HostConfig"].get("Memory", 0)
            if limit <= 0:
                raise ValueError("another running container has an unbounded memory limit")
            others += limit
    capacity = int(host["MemTotal"]) // (1024 * 1024)
    if budget["memory_mib"] + others // (1024 * 1024) + 750 > capacity:
        raise ValueError("rehearsal plus existing containers exceeds memory headroom")
    if budget["cpu_caps"] > int(host["NCPU"]) * 1.5:
        raise ValueError("rehearsal exceeds the bounded CPU envelope")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("config", "start"))
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        config = rendered_config(args.env_file)
        budget = validate_config(config)
        verify_capacity(budget)
        if args.action == "start":
            result = subprocess.run(
                [
                    *compose_command(args.env_file),
                    "up",
                    "-d",
                    "--pull",
                    "never",
                    "--wait",
                    "--wait-timeout",
                    "300",
                ],
                capture_output=True,
                timeout=360,
                check=False,
            )
            if result.returncode:
                raise RuntimeError("rehearsal startup failed; inspect only its isolated services")
        print(json.dumps({**budget, "action": args.action, "source_or_dns_changed": False}))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"BLOCKED: {type(error).__name__}", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
