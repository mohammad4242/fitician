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


def test_codex_configuration_requires_an_explicit_executable_instead_of_mutable_path(tmp_path):
    config = {
        "server": "https://fitician.example",
        "id": str(uuid4()),
        "token": "a" * 48,
        "repository_name": "mohammad4242/fitician",
        "codex_home": str(tmp_path / "auth"),
    }
    path = tmp_path / "connector.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    with pytest.raises(ValueError, match="pinned_codex_executable_required"):
        load_configuration(path)
    binary = tmp_path / "codex-pinned"
    binary.write_text("fixture")
    binary.chmod(0o700)
    config["codex_executable"] = str(binary)
    path.write_text(json.dumps(config))
    assert load_configuration(path)["codex_executable"] == str(binary)
    config["codex_executable"] = "codex"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="pinned_codex_executable_required"):
        load_configuration(path)


def test_codex_discovery_uses_the_explicit_binary(tmp_path, monkeypatch):
    opened = []

    class Runtime:
        version = "0.167.2"

        def __init__(self, **options):
            opened.append(options)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def call(self, method, params):
            if method == "account/read":
                return {"account": {"type": "chatgpt"}, "requiresOpenaiAuth": True}
            return {"data": [{"model": "selected-model"}]}

    monkeypatch.setattr("app.debugging.connector.AppServer", Runtime)
    config = {
        "server": "https://fitician.example",
        "id": str(uuid4()),
        "token": "a" * 48,
        "repository_name": "mohammad4242/fitician",
        "repository": str(tmp_path),
        "workspace_root": str(tmp_path / "runtime"),
        "codex_home": str(tmp_path / "auth"),
        "codex_executable": "/operator-owned/codex-0.167.2",
    }

    async def run():
        async with httpx.AsyncClient() as client:
            connector = LaptopConnector(config, client)
            await connector.discover()
            assert connector.models == ["selected-model"]

    asyncio.run(run())
    assert opened[0]["executable"] == config["codex_executable"]


def test_unauthenticated_cached_catalog_does_not_advertise_codex(tmp_path, monkeypatch):
    calls = []

    class Runtime:
        version = "0.167.2"

        def __init__(self, **options):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def call(self, method, params):
            calls.append(method)
            if method == "account/read":
                return {"account": None, "requiresOpenaiAuth": True}
            return {"data": [{"model": "cached-only-model"}]}

    monkeypatch.setattr("app.debugging.connector.AppServer", Runtime)

    async def run():
        async with httpx.AsyncClient() as client:
            connector = LaptopConnector(
                {
                    "id": str(uuid4()),
                    "server": "https://fitician.example",
                    "repository": str(tmp_path),
                    "workspace_root": str(tmp_path / "runtime"),
                    "codex_home": str(tmp_path / "auth"),
                    "codex_executable": "/pinned/codex",
                },
                client,
            )
            await connector.discover()
            assert connector.models == []
            assert connector.authenticated is False

    asyncio.run(run())
    assert calls == ["account/read"]


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
            assert json.loads(first["output"])["output"] == "file_written"
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


def test_connector_records_a_finding_through_authenticated_progress_without_a_shell(tmp_path):
    original = tmp_path / "original"
    commit = repository(original)
    identifier = str(uuid4())
    requests = []
    config = {
        "id": str(uuid4()),
        "token": "a" * 48,
        "server": "https://fitician.example",
        "repository_name": "mohammad4242/fitician",
        "repository": str(original),
        "workspace_root": str(tmp_path / "runtime"),
        "environment": "test",
    }

    def handle(request):
        payload = json.loads(request.content)
        requests.append(payload)
        return httpx.Response(
            200, json={"sequence": payload["sequence"], "evidence_id": identifier}
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            connector = LaptopConnector(config, client)
            return await connector.execute(
                {
                    "id": str(uuid4()),
                    "run_id": str(uuid4()),
                    "thread_id": str(uuid4()),
                    "lease_token": str(uuid4()),
                    "tool": "fitician_record_finding",
                    "arguments": {
                        "classification": "hypothesis",
                        "text": "Check input validation",
                        "evidence_ids": [str(uuid4())],
                    },
                    "repository": config["repository_name"],
                    "environment": "test",
                    "release_commit": commit,
                    "action": "analyze",
                    "config": {},
                }
            )

    result = asyncio.run(run())
    assert identifier in result["output"]
    assert [item["kind"] for item in requests] == [
        "tool_started",
        "finding_proposed",
        "tool_completed",
    ]


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
            assert json.loads((await connector.execute(job))["output"])["output"] == "file_written"
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


@pytest.mark.parametrize(
    "base", ["feature/untrusted", "main;sh", "https://example.invalid", "debug/seed-invalid"]
)
def test_pr_base_is_trusted_configuration_with_a_narrow_allowlist(tmp_path, base):
    original = tmp_path / "original"
    commit = repository(original)
    tools = RepositoryTools.create(
        original, tmp_path / "worktrees", str(uuid4()), commit, allow_write=True
    )
    with pytest.raises(ValueError, match="pull_request_base_not_authorized"):
        publish_tested_pr(tools, "fix(fixture): repair addition", base=base)


def test_pr_publication_rejects_a_base_with_unrelated_newer_commits(tmp_path, monkeypatch):
    import subprocess

    from app.debugging import github

    original = tmp_path / "original"
    commit = repository(original)
    tools = RepositoryTools.create(
        original, tmp_path / "worktrees", str(uuid4()), commit, allow_write=True
    )
    # A fixture journal binds this broker check; container execution is tested separately.
    (tools.workspace.parent / (tools.workspace.name + ".tested.json")).write_text(
        json.dumps({"commit": commit})
    )
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
            "test: newer main",
        ],
        check=True,
    )
    advanced = subprocess.check_output(
        ["git", "-C", str(original), "rev-parse", "HEAD"], text=True
    ).strip()
    monkeypatch.setattr(github, "_gh", lambda arguments: {"object": {"sha": advanced}})
    original_run = subprocess.run
    pushes = []

    def guarded(command, **kwargs):
        if "push" in command:
            pushes.append(command)
            raise AssertionError("A stale branch must not be pushed")
        return original_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded)
    with pytest.raises(ValueError, match="repair_requires_current_base"):
        publish_tested_pr(tools, "fix(fixture): repair addition")
    assert pushes == []
