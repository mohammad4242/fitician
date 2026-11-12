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
