import asyncio
import json
import subprocess
from uuid import uuid4

import httpx
import pytest

from app.debugging.connector import LaptopConnector
from app.debugging.tools import RepositoryTools
from tests.test_debug_tools import repository


def newer_main(path):
    release = repository(path)
    (path / "version.py").write_text("VERSION='new-main'\n")
    subprocess.run(["git", "-C", str(path), "add", "version.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "test: retain unrelated newer work",
        ],
        check=True,
    )
    current = subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()
    return release, current


def test_repair_uses_current_main_but_can_inspect_exact_old_release(tmp_path, monkeypatch):
    original = tmp_path / "original"
    release, current = newer_main(original)
    fetches = []

    def resolve(path):
        fetches.append(path)
        return current

    monkeypatch.setattr("app.debugging.connector.current_main_commit", resolve, raising=False)
    config = {
        "server": "https://fitician.example",
        "id": str(uuid4()),
        "token": "synthetic-only",
        "repository_name": "mohammad4242/fitician",
        "environment": "test",
        "repository": str(original),
        "workspace_root": str(tmp_path / "runtime"),
        "fetch_missing_releases": True,
        "repair_on_current_main": True,
        "github_enabled": False,
        "ci_enabled": True,
    }

    def response(request):
        return httpx.Response(
            200,
            json={"sequence": json.loads(request.content)["sequence"], "evidence_id": str(uuid4())},
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
            c = LaptopConnector(config, client)
            job = {
                "id": str(uuid4()),
                "run_id": str(uuid4()),
                "thread_id": str(uuid4()),
                "lease_token": str(uuid4()),
                "repository": config["repository_name"],
                "environment": "test",
                "release_commit": release,
                "action": "prepare_fix",
                "config": {},
                "tool": "fitician_read_file",
                "arguments": {"path": "version.py"},
            }
            first = await c.execute(job)
            assert "new-main" in first.get("output", "")
            second = await c.execute(
                {
                    **job,
                    "id": str(uuid4()),
                    "tool": "fitician_read_release_file",
                    "arguments": {"path": "bug.py"},
                }
            )
            assert "return a - b" in second.get("output", "")
            assert release in second["output"]

    asyncio.run(run())
    assert len(fetches) == 1
    assert (
        subprocess.check_output(
            ["git", "-C", str(original), "rev-parse", "HEAD"], text=True
        ).strip()
        == current
    )


def test_exact_release_reader_rejects_secrets_even_when_they_were_tracked(tmp_path):
    original = tmp_path / "original"
    release, current = newer_main(original)
    tools = RepositoryTools.create(
        original,
        tmp_path / "worktrees",
        str(uuid4()),
        current,
        allow_write=True,
        evidence_commit=release,
    )
    with pytest.raises(ValueError):
        tools.read_release_file(".env")
    with pytest.raises(ValueError):
        tools.read_release_file("../original/.env")
    assert release in tools.read_release_file("bug.py")


def test_controlled_ci_does_not_offer_competing_local_commit_or_pr_tools():
    from app.debugging.catalog import tool_catalog

    names = {
        t["name"]
        for t in tool_catalog(
            allow_write=True, supports_tests=True, supports_github=True, supports_ci=True
        )
    }
    assert "fitician_ci_publish_pr" in names
    assert not names.intersection({"fitician_commit", "fitician_create_pr"})


def test_main_fetch_uses_fixed_origin_and_does_not_checkout_primary(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from app.debugging import runtime_storage

    calls = []

    def git(root, *args, **kwargs):
        calls.append(args)
        return "a" * 40 if args[0] == "rev-parse" else ""

    monkeypatch.setattr(runtime_storage, "_git", git)
    monkeypatch.setattr(
        runtime_storage.shutil, "disk_usage", lambda _: SimpleNamespace(free=3 * 1024**3)
    )
    assert runtime_storage.current_main_commit(tmp_path) == "a" * 40
    assert runtime_storage.ORIGIN in calls[0] and calls[0][-1] == "refs/heads/main"
    assert not any("checkout" in call or "reset" in call or "update-ref" in call for call in calls)


def test_timed_out_git_fetch_reaps_its_helper_process(tmp_path, monkeypatch):
    import os
    import sys
    from pathlib import Path

    from app.debugging.tools import _git

    binary = tmp_path / "git"
    child = tmp_path / "helper.pid"
    binary.write_text(
        "#!"
        + sys.executable
        + "\nimport subprocess,sys,time\n"
        + 'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"])\nopen('
        + repr(str(child))
        + ',"w").write(str(p.pid))\ntime.sleep(60)\n'
    )
    binary.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))
    try:
        with pytest.raises(ValueError, match="repository_operation_timed_out"):
            _git(tmp_path, "fetch", timeout_seconds=0.5)
    finally:
        if child.exists():
            pid = int(child.read_text())
            status = Path("/proc") / str(pid) / "stat"
            import time

            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                try:
                    if status.read_text().split()[2] == "Z":
                        break
                except (FileNotFoundError, ProcessLookupError):
                    break
                time.sleep(0.01)
            else:
                try:
                    os.kill(pid, 9)
                except ProcessLookupError:
                    pass
                else:
                    pytest.fail("Git helper survived timeout")


def test_git_timeout_kills_a_helper_that_ignores_termination(tmp_path, monkeypatch):
    import os
    import sys
    import time

    from app.debugging.tools import _git

    child = tmp_path / "ignoring.pid"
    binary = tmp_path / "git"
    program = (
        "import signal,time,pathlib,os;signal.signal(signal.SIGTERM,signal.SIG_IGN);"
        f"pathlib.Path({str(child)!r}).write_text(str(os.getpid()));time.sleep(60)"
    )
    binary.write_text(
        "#!"
        + sys.executable
        + "\nimport subprocess,sys,time\n"
        + f'subprocess.Popen([sys.executable,"-c",{program!r}],'
        + "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\ntime.sleep(60)\n"
    )
    binary.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))
    try:
        with pytest.raises(ValueError, match="repository_operation_timed_out"):
            _git(tmp_path, "fetch", timeout_seconds=0.5)
        assert child.exists()
        status = __import__("pathlib").Path("/proc") / child.read_text() / "stat"
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            try:
                if status.read_text().split()[2] == "Z":
                    break
            except (FileNotFoundError, ProcessLookupError):
                break
            time.sleep(0.01)
        else:
            pytest.fail("Git helper ignored termination and survived group cleanup")
    finally:
        if child.exists():
            try:
                os.kill(int(child.read_text()), 9)
            except ProcessLookupError:
                pass
