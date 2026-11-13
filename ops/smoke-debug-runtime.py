#!/usr/bin/env python3
"""Exercise only a new, networkless runtime container and its own temporary volume."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from uuid import uuid4


def command(*args: str) -> str:
    result = subprocess.run(
        args, capture_output=True, text=True, timeout=60, check=False
    )
    if result.returncode:
        raise RuntimeError("isolated_runtime_smoke_command_failed")
    return result.stdout.strip()


def inspect(name: str) -> dict:
    return json.loads(command("docker", "inspect", name))[0]


def wait_healthy(name: str) -> None:
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        value = inspect(name)
        if value["State"].get("Health", {}).get("Status") == "healthy":
            return
        if not value["State"]["Running"]:
            break
        time.sleep(1)
    raise RuntimeError("isolated_runtime_liveness_failed")


def run(image: str, commit: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("exact_commit_required")
    metadata = json.loads(command("docker", "image", "inspect", image))[0]
    if (
        metadata["Config"].get("Labels", {}).get("org.opencontainers.image.revision")
        != commit
    ):
        raise ValueError("runtime_image_revision_mismatch")
    name = "fitician-debug-runtime-test-" + str(uuid4())
    command("docker", "volume", "create", name)
    try:
        command(
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--network",
            "none",
            "--init",
            "--read-only",
            "--user",
            "10001:10001",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "96",
            "--memory",
            "512m",
            "--memory-swap",
            "768m",
            "--cpus",
            "0.25",
            "--mount",
            f"type=volume,src={name},dst=/state",
            "--tmpfs",
            "/tmp:uid=10001,gid=10001,mode=0700,size=32m",
            "--health-cmd",
            "python -m app.debugging.server_runtime health",
            "--health-interval",
            "1s",
            "--health-timeout",
            "3s",
            metadata["Id"],
        )
        wait_healthy(name)
        config = inspect(name)
        host = config["HostConfig"]
        assert host["Memory"] == 512 * 1024**2 and host["NanoCpus"] == 250_000_000
        assert host["ReadonlyRootfs"] and config["Config"]["User"] == "10001:10001"
        assert host["CapDrop"] == ["ALL"] and not host["Privileged"]
        assert not host.get("PortBindings")
        assert {m["Destination"] for m in config["Mounts"]} <= {"/state", "/tmp"}
        status = json.loads(
            command(
                "docker",
                "exec",
                name,
                "python",
                "-m",
                "app.debugging.server_runtime",
                "status",
            )
        )
        assert status["state"] == "awaiting_enrollment" and not status["connected"]
        assert not status["auth_cache_present"] and status["authenticated"] is False
        protocol = (
            "from app.debugging.workspaces import prepare_workspace\n"
            "import asyncio; from app.debugging.appserver import AppServer\n"
            "async def run():\n"
            " async with AppServer() as server:\n"
            "  assert server.version == '0.167.2'\n"
            "  config = (await server.call('config/read', {'includeLayers':False}))['config']\n"
            "  assert config['features']['plugins'] is False\n"
            "asyncio.run(run())"
        )
        command("docker", "exec", name, "python", "-c", protocol)
        command(
            "docker",
            "exec",
            name,
            "python",
            "-c",
            "import sqlite3; c=sqlite3.connect('/state/restart-proof.db'); "
            "c.execute('create table proof (value integer)'); c.execute('insert into proof values (1)'); c.commit()",
        )
        command("docker", "restart", name)
        wait_healthy(name)
        retained = command(
            "docker",
            "exec",
            name,
            "python",
            "-c",
            "import sqlite3; print(sqlite3.connect('/state/restart-proof.db').execute('select value from proof').fetchone()[0])",
        )
        assert retained == "1"
        return {
            "commit": commit,
            "image_id": metadata["Id"],
            "cli_version": "0.167.2",
            "isolated": True,
            "liveness": True,
            "persistent_state_after_restart": True,
            "authenticated": False,
            "panel_connected": False,
            "inference_verified": False,
        }
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name], capture_output=True, timeout=30, check=False
        )
        command("docker", "volume", "rm", name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = run(args.image, args.commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        "Independent runtime: isolation, protocol, liveness and restart persistence passed"
    )


if __name__ == "__main__":
    main()
