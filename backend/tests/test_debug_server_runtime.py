import asyncio
import json
import time
from uuid import uuid4

import pytest

from app.debugging import server_runtime
from app.debugging.catalog import tool_catalog
from tests.test_debug_tools import repository


def test_server_configuration_pins_private_storage_and_never_inherits_laptop_access(
    tmp_path, monkeypatch
):
    binary = tmp_path / "codex-pinned"
    binary.write_text("fixture")
    binary.chmod(0o700)
    monkeypatch.setattr(server_runtime, "EXECUTABLE", str(binary))
    config = tmp_path / "connector.json"
    config.write_text(
        json.dumps(
            {
                "server": "https://fitician.example",
                "id": str(uuid4()),
                "token": "a" * 48,
                "environment": "production",
                "repository_name": "mohammad4242/fitician",
                "repository": "/personal/checkout",
                "workspace_root": "/personal/work",
                "test_image": "private-production-image",
                "codex_home": "/personal/auth",
                "codex_executable": "/personal/codex",
            }
        )
    )
    config.chmod(0o600)
    state = tmp_path / "server-state"
    value = server_runtime.configuration(config, state)
    assert value["repository"] == str(state / "repository")
    assert value["workspace_root"] == str(state / "runtime")
    assert value["codex_home"] == str(state / "codex")
    assert value["codex_executable"] == str(binary)
    assert value["max_workspaces"] == 2
    assert value["workspace_min_free_bytes"] >= 2**30
    assert value["fetch_missing_releases"] is True
    assert value["evict_readonly"] is True
    assert not value["test_image"] and not value["github_enabled"]


def test_unconfigured_supervisor_is_alive_but_honestly_unenrolled(tmp_path):
    async def run():
        supervisor = server_runtime.Supervisor(tmp_path / "missing.json", tmp_path / "state")
        task = asyncio.create_task(supervisor.run())
        try:
            for _ in range(50):
                await asyncio.sleep(0.01)
                if supervisor.status_file.exists():
                    break
            result = json.loads(supervisor.status_file.read_text())
            assert result["state"] == "awaiting_enrollment"
            assert result["connected"] is False
            assert result["authenticated"] is False
            assert server_runtime.healthy(supervisor.status_file)
            assert "token" not in json.dumps(result)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(run())


def test_health_rejects_stale_missing_and_future_heartbeat(tmp_path):
    path = tmp_path / "status.json"
    assert not server_runtime.healthy(path)
    for stamp in [time.time() - 120, time.time() + 120]:
        path.write_text(json.dumps({"heartbeat": stamp}))
        assert not server_runtime.healthy(path)
    path.write_text(json.dumps({"heartbeat": time.time()}))
    assert server_runtime.healthy(path)


def test_revoked_connector_is_not_reported_connected_from_a_recent_success(tmp_path):
    from types import SimpleNamespace

    runtime = server_runtime.Supervisor(tmp_path / "config.json", tmp_path / "state")
    runtime.connector = SimpleNamespace(
        last_contact=time.monotonic(),
        connection_error="connector_authorization_rejected",
        authenticated=False,
        cli_version=None,
        models=[],
    )
    assert runtime.status()["connected"] is False
    assert runtime.status()["state"] == "connector_authorization_rejected"


def test_exact_release_fetch_is_fixed_origin_and_refuses_model_remote_or_ref(tmp_path, monkeypatch):
    from app.debugging.runtime_storage import ensure_release

    root = tmp_path / "source"
    root.mkdir()
    calls = []

    def command(path, *arguments):
        calls.append(arguments)
        if arguments[:2] == ("cat-file", "-e"):
            raise ValueError("missing")
        if arguments[:2] == ("rev-parse", "--verify"):
            return "a" * 40
        return ""

    monkeypatch.setattr("app.debugging.runtime_storage._git", command)
    commit = "a" * 40
    ensure_release(root, commit)
    fetch = next(args for args in calls if "fetch" in args)
    assert "https://github.com/mohammad4242/fitician.git" in fetch
    assert fetch[-1] == commit
    assert "--depth=1" in fetch and "--no-tags" in fetch
    assert "credential.helper=" in fetch
    calls.clear()
    for ref in ["main", "--upload-pack=bad", "https://attacker.invalid/repo", "a" * 39]:
        with pytest.raises(ValueError, match="exact_release_commit_required"):
            ensure_release(root, ref)
    assert not calls


def test_available_release_is_reused_without_network_or_primary_checkout_changes(tmp_path):
    from app.debugging.runtime_storage import ensure_release

    root = tmp_path / "source"
    commit = repository(root)
    before = (root / "bug.py").read_text()
    ensure_release(root, commit)
    assert (root / "bug.py").read_text() == before


def test_server_catalog_hides_unconfigured_docker_and_github_authority():
    names = {
        t["name"]
        for t in tool_catalog(allow_write=True, supports_tests=False, supports_github=False)
    }
    assert {"fitician_read_file", "fitician_write_file", "fitician_record_finding"} <= names
    assert not names & {"fitician_run_tests", "fitician_commit", "fitician_create_pr"}


def test_device_login_timeout_is_recorded_without_exposing_the_challenge(tmp_path, monkeypatch):
    import subprocess

    state = tmp_path / "private-state"
    state.mkdir(mode=0o700)
    calls = []

    def expired(command, **options):
        calls.append((command, options))
        assert json.loads((state / "login-result.json").read_text())["state"] == "pending"
        options["stdout"].write("private-device-challenge-fixture")
        raise subprocess.TimeoutExpired(command, options["timeout"], output="private-challenge")

    monkeypatch.setattr(server_runtime.subprocess, "run", expired)
    assert server_runtime.device_login(state) == 124
    result = json.loads((state / "login-result.json").read_text())
    assert result == {"state": "expired", "succeeded": False}
    assert "challenge" not in json.dumps(result)
    assert (state / "device-login.txt").stat().st_mode & 0o777 == 0o600
    assert (state / "login-result.json").stat().st_mode & 0o777 == 0o600
    assert calls[0][1]["env"]["CODEX_HOME"] == str(state / "codex")


def test_device_login_requires_auth_file_and_preserves_existing_authentication(
    tmp_path, monkeypatch
):
    import subprocess

    state = tmp_path / "private-state"
    state.mkdir(mode=0o700)
    monkeypatch.setattr(
        server_runtime.subprocess,
        "run",
        lambda command, **options: subprocess.CompletedProcess(command, 0),
    )
    assert server_runtime.device_login(state) != 0
    assert json.loads((state / "login-result.json").read_text())["state"] == "failed"
    auth = state / "codex" / "auth.json"
    auth.write_text("private-existing-auth")
    with pytest.raises(ValueError, match="independent_authentication_already_exists"):
        server_runtime.device_login(state)
    assert auth.read_text() == "private-existing-auth"
