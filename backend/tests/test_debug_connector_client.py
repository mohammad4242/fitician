import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from app.debugging.connector import LaptopConnector, load_configuration
from app.debugging.github import publish_tested_pr
from app.debugging.tools import RepositoryTools
from tests.test_debug_tools import repository


def test_connector_requires_private_explicit_https_configuration(tmp_path):
    path = tmp_path / "configuration.json"
    config = {
        "server": "http://untrusted.invalid",
        "id": str(uuid4()),
        "token": "a" * 48,
        "repository_name": "mohammad4242/fitician",
    }
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    with pytest.raises(ValueError, match="trusted_https_server_required"):
        load_configuration(path)
    config["server"] = "https://fitician.example"
    path.write_text(json.dumps(config))
    path.chmod(0o644)
    with pytest.raises(ValueError, match="configuration_must_be_private"):
        load_configuration(path)


def test_connector_executes_once_and_recovers_the_ack_without_repeating_action(tmp_path):
    original = tmp_path / "original"
    commit = repository(original)
    config = {
        "id": str(uuid4()),
        "token": "a" * 48,
        "server": "https://fitician.example",
        "repository_name": "mohammad4242/fitician",
        "repository": str(original),
        "workspace_root": str(tmp_path / "runtime"),
        "environment": "test",
    }
    requests = []

    def handle(request):
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer " + "a" * 48
        return httpx.Response(200, json={"sequence": 1})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            connector = LaptopConnector(config, client)
            job = {
                "id": str(uuid4()),
                "run_id": str(uuid4()),
                "thread_id": str(uuid4()),
                "lease_token": str(uuid4()),
                "tool": "fitician_write_file",
                "arguments": {"path": "bug.py", "content": "def add(a, b):\n    return a + b\n"},
                "repository": config["repository_name"],
                "environment": "test",
                "release_commit": commit,
                "action": "prepare_fix",
                "config": {},
            }
            first = await connector.execute(job)
            assert first["output"] == "file_written"
            count = len(requests)
            job["lease_token"] = str(uuid4())
            assert await connector.execute(job) == first
            assert len(requests) == count
            assert "return a - b" in (original / "bug.py").read_text()

    asyncio.run(run())


def test_github_publication_requires_matching_tests_before_any_network(tmp_path):
    original = tmp_path / "original"
    commit = repository(original)
    tools = RepositoryTools.create(
        original, tmp_path / "worktrees", str(uuid4()), commit, allow_write=True
    )
    with pytest.raises(ValueError, match="matching_successful_tests_required"):
        publish_tested_pr(tools, "fix(fixture): repair addition")


def test_followup_runs_reuse_repair_workspace_but_other_issues_and_releases_do_not(tmp_path):
    original = tmp_path / "original"
    commit = repository(original)
    config = {
        "id": str(uuid4()),
        "token": "a" * 48,
        "server": "https://fitician.example",
        "repository_name": "mohammad4242/fitician",
        "repository": str(original),
        "workspace_root": str(tmp_path / "runtime"),
        "environment": "test",
    }

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"sequence": 1}))
        ) as client:
            connector = LaptopConnector(config, client)
            job = {
                "id": str(uuid4()),
                "run_id": str(uuid4()),
                "thread_id": str(uuid4()),
                "lease_token": str(uuid4()),
                "tool": "fitician_write_file",
                "arguments": {"path": "bug.py", "content": "def add(a, b):\n    return a + b\n"},
                "repository": config["repository_name"],
                "environment": "test",
                "release_commit": commit,
                "action": "prepare_fix",
                "config": {},
            }
            assert (await connector.execute(job))["output"] == "file_written"
            job.update(
                id=str(uuid4()),
                run_id=str(uuid4()),
                tool="fitician_read_file",
                arguments={"path": "bug.py"},
            )
            assert "return a + b" in (await connector.execute(job))["output"]
            job.update(id=str(uuid4()), run_id=str(uuid4()), thread_id=str(uuid4()))
            assert "return a - b" in (await connector.execute(job))["output"]
            # A new exact release must not inherit a previous repair or runtime history.
            import subprocess

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(original),
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "--allow-empty",
                    "-qm",
                    "test: second release",
                ],
                check=True,
            )
            release = subprocess.check_output(
                ["git", "-C", str(original), "rev-parse", "HEAD"], text=True
            ).strip()
            job.update(id=str(uuid4()), run_id=str(uuid4()), release_commit=release)
            assert "return a - b" in (await connector.execute(job))["output"]

    asyncio.run(run())


def test_missing_codex_auth_does_not_disable_api_model_repository_tools(tmp_path):
    original = tmp_path / "original"
    repository(original)
    home = tmp_path / "codex"
    home.mkdir(mode=0o700)
    config = {
        "id": str(uuid4()),
        "server": "https://fitician.example",
        "repository": str(original),
        "workspace_root": str(tmp_path / "runtime"),
        "codex_home": str(home),
    }

    async def run():
        async with httpx.AsyncClient() as client:
            connector = LaptopConnector(config, client)
            await connector.discover()
            assert connector.models == []
            assert connector.cli_version is None

    asyncio.run(run())
