#!/usr/bin/env python3
"""Drain and replace API replicas without restarting Caddy or other services."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

REPLICAS = {"backend", "backend-2"}


class RolledBack(RuntimeError):
    """Candidate failed and both previous replicas were restored."""


class ProxyDrift(RuntimeError):
    """A concurrent proxy edit must never be overwritten."""


class RollbackFailed(RuntimeError):
    """Manual intervention needed; retain the last safe routing configuration."""


def upstream_groups(config):
    if isinstance(config, dict):
        upstreams = config.get("upstreams")
        if isinstance(upstreams, list) and any(
            item.get("dial") in {"backend:8000", "backend-2:8000"}
            for item in upstreams
            if isinstance(item, dict)
        ):
            yield upstreams
        for value in config.values():
            yield from upstream_groups(value)
    elif isinstance(config, list):
        for value in config:
            yield from upstream_groups(value)


def backend_upstreams(config):
    return [
        {item.get("dial", "").removesuffix(":8000") for item in group}
        for group in upstream_groups(config)
    ]


def validate_proxy(config):
    groups = list(upstream_groups(config))
    if (
        not groups
        or any(len(group) != 2 for group in groups)
        or any(group != REPLICAS for group in backend_upstreams(config))
    ):
        raise RuntimeError(
            "Caddy must route each API upstream group to both known replicas"
        )


def drained_config(config, service):
    validate_proxy(config)
    result = deepcopy(config)
    for group in upstream_groups(result):
        group[:] = [item for item in group if item["dial"] != service + ":8000"]
    return result


def roll(runtime):
    original = runtime.read_config()
    validate_proxy(original)
    for service in sorted(REPLICAS):
        runtime.ready(service)
    changed = []
    try:
        for service in ("backend", "backend-2"):
            runtime.ready(next(iter(REPLICAS - {service})))
            runtime.load_config(drained_config(original, service))
            changed.append(service)
            runtime.recreate(service)
            runtime.ready(service)
            runtime.load_config(original)
        verify = getattr(runtime, "verify", None)
        if verify is not None:
            verify()
    except ProxyDrift as error:
        raise RollbackFailed(
            "Proxy changed concurrently; manual reconciliation required"
        ) from error
    except BaseException as error:
        try:
            # Restore the failed replica first; the healthy peer keeps serving.
            for service in reversed(changed):
                runtime.ready(next(iter(REPLICAS - {service})))
                runtime.load_config(drained_config(original, service))
                runtime.recreate(service, rollback=True)
                runtime.ready(service)
                runtime.load_config(original)
            if not changed:
                runtime.load_config(original)
        except BaseException as rollback_error:
            raise RollbackFailed(
                "Rollback failed; unhealthy replica remains drained"
            ) from rollback_error
        raise RolledBack(
            "Candidate failed; previous API replicas and proxy restored"
        ) from error


class DockerRuntime:
    def __init__(self, args):
        self.args = args
        self.project = os.environ["COMPOSE_PROJECT_NAME"]
        self.env_file = os.environ["FITICIAN_ENV_FILE"]
        self.caddy = self.command(self.compose(False) + ["ps", "-q", "caddy"]).strip()
        if not self.caddy or "\n" in self.caddy:
            raise RuntimeError("Expected exactly one Caddy container")

    @staticmethod
    def command(argv, *, input_text=None, env=None):
        result = subprocess.run(
            argv,
            input=input_text,
            text=True,
            capture_output=True,
            env=env,
            timeout=360,
            check=False,
        )
        if result.returncode:
            # Command output may include expanded operator settings; do not print it.
            raise RuntimeError("Regional runtime command failed")
        return result.stdout

    def environment(self, rollback):
        result = dict(os.environ)
        result["BACKEND_API_IMAGE_TAG"] = (
            self.args.rollback_tag if rollback else self.args.candidate_tag
        )
        return result

    def compose(self, rollback):
        contract = (
            self.args.rollback_contract if rollback else self.args.candidate_contract
        )
        return [
            "docker",
            "compose",
            "-p",
            self.project,
            "--env-file",
            self.env_file,
            "-f",
            contract,
        ]

    def read_config(self):
        config = json.loads(
            self.command(
                [
                    "docker",
                    "exec",
                    self.caddy,
                    "wget",
                    "-qO-",
                    "http://127.0.0.1:2019/config/",
                ]
            )
        )
        validate_proxy(config)
        directory = Path(self.args.backup_dir)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or directory.stat().st_mode & 0o077:
            raise RuntimeError("Proxy backup directory must be private")
        path = directory / (
            "caddy-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
        )
        with path.open("x", opener=lambda p, flags: os.open(p, flags, 0o600)) as target:
            json.dump(config, target)
        self.expected_config = deepcopy(config)
        return config

    def load_config(self, config):
        current = json.loads(
            self.command(
                [
                    "docker",
                    "exec",
                    self.caddy,
                    "wget",
                    "-qO-",
                    "http://127.0.0.1:2019/config/",
                ]
            )
        )
        if current != self.expected_config:
            raise ProxyDrift("Proxy changed concurrently")
        self.command(
            ["docker", "exec", "-i", self.caddy, "caddy", "reload", "--config", "-"],
            input_text=json.dumps(config),
        )
        observed = json.loads(
            self.command(
                [
                    "docker",
                    "exec",
                    self.caddy,
                    "wget",
                    "-qO-",
                    "http://127.0.0.1:2019/config/",
                ]
            )
        )
        if observed != config:
            raise ProxyDrift("Caddy reload did not preserve the requested routing")
        self.expected_config = deepcopy(config)

    def ready(self, service):
        code = (
            "import urllib.request; "
            "urllib.request.urlopen('http://127.0.0.1:8000/readyz',timeout=5).read()"
        )
        self.command(
            self.compose(False) + ["exec", "-T", service, "python", "-c", code]
        )

    def recreate(self, service, rollback=False):
        self.command(
            self.compose(rollback)
            + [
                "up",
                "-d",
                "--no-deps",
                "--pull",
                "never",
                "--wait",
                "--wait-timeout",
                "240",
                service,
            ],
            env=self.environment(rollback),
        )

    def verify(self):
        if not self.args.verify_script:
            return
        environment = dict(os.environ)
        environment["BACKEND_API_IMAGE_TAG"] = self.args.candidate_tag
        environment["COMPOSE_FILE"] = self.args.candidate_contract
        result = subprocess.run(
            ["sh", self.args.verify_script],
            text=True,
            capture_output=True,
            env=environment,
            timeout=360,
            check=False,
        )
        if result.returncode:
            raise RuntimeError("Regional release verification failed")


def terminate(*_):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-contract", required=True)
    parser.add_argument("--rollback-contract", required=True)
    parser.add_argument("--candidate-tag", required=True)
    parser.add_argument("--rollback-tag", required=True)
    parser.add_argument("--backup-dir", required=True)
    parser.add_argument("--verify-script")
    parser.add_argument("--owner-approved", action="store_true")
    args = parser.parse_args()
    if not args.owner_approved or not all(
        re.fullmatch(r"[0-9a-f]{40}", value)
        for value in (args.candidate_tag, args.rollback_tag)
    ):
        print(
            "Rolling deployment requires owner authorization and full image SHAs",
            file=sys.stderr,
        )
        return 75
    signal.signal(signal.SIGTERM, terminate)
    try:
        runtime = DockerRuntime(args)
        roll(runtime)
    except RolledBack as error:
        print(str(error), file=sys.stderr)
        return 73
    except RollbackFailed as error:
        print(str(error), file=sys.stderr)
        return 74
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError):
        print("Rolling API preflight failed; no release was accepted", file=sys.stderr)
        return 75
    print("Both API replicas healthy; original Caddy routing restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
