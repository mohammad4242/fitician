#!/usr/bin/env python3
"""Recover only the existing owned Sentry proxy, including a lost Docker endpoint."""

import json
import socket
import subprocess

CONTAINER = "fitician-sentry-egress-proxy-1"
PROJECT = "fitician-sentry-egress"
NETWORK = PROJECT + "_default"
BINDING = {"3128/tcp": [{"HostIp": "100.108.24.126", "HostPort": "3188"}]}


def execute(*args: str) -> str:
    result = subprocess.run(
        args, capture_output=True, text=True, timeout=15, check=False
    )
    if result.returncode:
        raise RuntimeError("owned_proxy_recovery_command_failed")
    return result.stdout


def recover(*, command=execute, connect=socket.create_connection) -> dict:
    container = json.loads(command("docker", "inspect", CONTAINER))[0]
    host = container["HostConfig"]
    if (
        container["Config"]["Labels"].get("com.docker.compose.project") != PROJECT
        or host["NetworkMode"] != NETWORK
        or not host["ReadonlyRootfs"]
        or host["PortBindings"] != BINDING
        or set(container["NetworkSettings"]["Networks"]) - {NETWORK}
    ):
        raise ValueError("owned_private_proxy_configuration_required")
    network = json.loads(command("docker", "network", "inspect", NETWORK))[0]
    if (
        network["Labels"].get("com.docker.compose.project") != PROJECT
        or network["Driver"] != "bridge"
    ):
        raise ValueError("owned_proxy_network_required")
    identifier = container["Id"]
    if container["State"]["Status"] != "running":
        if container["State"]["Status"] not in {"created", "exited"}:
            raise ValueError("proxy_state_requires_inspection")
        command("docker", "start", identifier)
        container = json.loads(command("docker", "inspect", identifier))[0]
    restored = False
    if not container["NetworkSettings"]["Networks"]:
        command("docker", "network", "connect", NETWORK, identifier)
        restored = True
    container = json.loads(command("docker", "inspect", identifier))[0]
    if (
        set(container["NetworkSettings"]["Networks"]) != {NETWORK}
        or container["NetworkSettings"]["Ports"] != BINDING
    ):
        raise ValueError("proxy_listener_not_published")
    # Process health alone cannot detect an orphaned network. No credentials required.
    with connect(("100.108.24.126", 3188), timeout=5) as listener:
        listener.sendall(
            b"CONNECT us.sentry.io:443 HTTP/1.1\r\nHost: us.sentry.io\r\n\r\n"
        )
        if listener.recv(4096).split(b"\r\n", 1)[0].split()[1:2] != [b"407"]:
            raise ValueError("proxy_authentication_boundary_failed")
    return {
        "network_recovered": restored,
        "listener_verified": True,
        "container_id": identifier,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(recover()))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        raise SystemExit(
            "Owned proxy is not reachable; supervised retry remains enabled"
        ) from None
