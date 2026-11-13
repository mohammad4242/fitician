"""Supervise a dedicated outbound server connector without application credentials."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

from .connector import (
    LaptopConnector,
    read_private_configuration,
    save_private,
    validate_configuration,
)
from .runtime_storage import initialize_repository

EXECUTABLE = "/usr/local/bin/codex"
STATE = Path("/state")
CONFIG = Path("/run/fitician-connector/connector.json")


def configuration(path: Path, state: Path) -> dict[str, Any]:
    value = read_private_configuration(path)
    # Storage, binary and authority are service policy, never downloaded laptop paths.
    value.update(
        repository=str(state / "repository"),
        workspace_root=str(state / "runtime"),
        codex_home=str(state / "codex"),
        codex_executable=EXECUTABLE,
        max_workspaces=2,
        workspace_min_free_bytes=1_610_612_736,
        fetch_missing_releases=True,
        evict_readonly=True,
        test_image="",
        github_enabled=False,
        ci_enabled=True,
    )
    return validate_configuration(value)


def healthy(path: Path) -> bool:
    try:
        stamp = json.loads(path.read_text())["heartbeat"]
        return isinstance(stamp, (int, float)) and 0 <= time.time() - stamp < 45
    except (OSError, ValueError, KeyError, TypeError):
        return False


class Supervisor:
    def __init__(self, config: Path = CONFIG, state: Path = STATE) -> None:
        self.config = config
        self.root = state
        if state.is_symlink():
            raise ValueError("private_runtime_state_required")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.home = self.root / "codex"
        self.home.mkdir(mode=0o700, exist_ok=True)
        self.status_file = self.root / "status.json"
        self.phase = "starting"
        self.connector: LaptopConnector | None = None

    def status(self) -> dict[str, Any]:
        client = self.connector
        connected = bool(
            client
            and client.connection_error is None
            and time.monotonic() - client.last_contact < 30
        )
        phase = self.phase
        if client:
            phase = "connected" if connected else "connecting"
            if client.connection_error:
                phase = client.connection_error
            elif connected and not client.models:
                phase = "codex_not_verified"
        return {
            "heartbeat": time.time(),
            "state": phase,
            "connected": connected,
            "authenticated": client.authenticated if client else False,
            "auth_cache_present": (self.home / "auth.json").is_file(),
            "cli_version": client.cli_version if client else None,
            "models": client.models if client else [],
            "max_workspaces": 2,
            "test_execution": "github_actions_delegated"
            if connected and client and client.ci_available
            else "github_actions_connection_unverified",
            "release_commit": os.environ.get("FITICIAN_RUNTIME_COMMIT", "unknown"),
        }

    async def pulse(self) -> None:
        while True:
            save_private(self.status_file, self.status())
            await asyncio.sleep(5)

    async def run(self) -> None:
        pulse = asyncio.create_task(self.pulse())
        try:
            while True:
                self.phase = "awaiting_enrollment"
                if not self.config.is_file():
                    await asyncio.sleep(5)
                    continue
                try:
                    value = configuration(self.config, self.root)
                    self.phase = "preparing_repository"
                    await asyncio.to_thread(
                        initialize_repository,
                        Path(value["repository"]),
                        os.environ.get("FITICIAN_RUNTIME_COMMIT", ""),
                    )
                    async with httpx.AsyncClient(
                        timeout=15,
                        follow_redirects=False,
                        trust_env=False,
                        proxy=value.get("proxy"),
                    ) as http:
                        self.connector = LaptopConnector(value, http)
                        await self.connector.run()
                except (
                    OSError,
                    ValueError,
                    KeyError,
                    TypeError,
                    RuntimeError,
                    httpx.HTTPError,
                    subprocess.SubprocessError,
                ):
                    # Never serialize raw errors, URLs, credentials or provider output.
                    self.phase = "configuration_or_repository_blocked"
                    self.connector = None
                    save_private(self.status_file, self.status())
                    await asyncio.sleep(15)
        finally:
            pulse.cancel()
            await asyncio.gather(pulse, return_exceptions=True)


def device_login(state: Path = STATE) -> int:
    home = state / "codex"
    home.mkdir(mode=0o700, exist_ok=True)
    with (state / "login.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (home / "auth.json").exists():
            raise ValueError("independent_authentication_already_exists")
        result_file = state / "login-result.json"
        save_private(result_file, {"state": "pending", "succeeded": False})
        path = state / "device-login.txt"
        # Device challenge and errors stay private, never in container logs.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as output:
            os.fchmod(output.fileno(), 0o600)
            try:
                result = subprocess.run(
                    [EXECUTABLE, "login", "--device-auth"],
                    stdout=output,
                    stderr=output,
                    timeout=900,
                    env={
                        "PATH": "/usr/local/bin:/usr/bin:/bin",
                        "HOME": str(state),
                        "CODEX_HOME": str(home),
                    },
                )
            except subprocess.TimeoutExpired:
                save_private(result_file, {"state": "expired", "succeeded": False})
                return 124
            except OSError:
                save_private(result_file, {"state": "runtime_unavailable", "succeeded": False})
                return 1
        succeeded = result.returncode == 0 and (home / "auth.json").is_file()
        save_private(
            result_file,
            {
                "state": "authenticated" if succeeded else "failed",
                "succeeded": succeeded,
            },
        )
        return 0 if succeeded else result.returncode or 1


def main() -> None:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("serve", "health", "status", "login"))
    arguments = parser.parse_args()
    if arguments.action == "health":
        raise SystemExit(0 if healthy(STATE / "status.json") else 1)
    if arguments.action == "status":
        print((STATE / "status.json").read_text())
        return
    if arguments.action == "login":
        raise SystemExit(device_login())
    with (STATE / "supervisor.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(Supervisor().run())


if __name__ == "__main__":
    main()
