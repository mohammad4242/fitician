import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from app.debugging.github_automation import GitHubAutomation
from tests.test_debug_automation import request as validation_request


def test_candidate_and_policy_are_pinned_without_force_updates_or_model_commands():
    operation_id = uuid4()
    snapshot = validation_request()["snapshot"]
    requests = []
    refs = {}

    def handle(request):
        requests.append(request)
        path = request.url.path
        payload = json.loads(request.content) if request.content else None
        assert request.headers["Authorization"] == "Bearer private-test-credential"
        assert request.url.host == "api.github.com"
        if request.method == "GET" and path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "a" * 40}})
        if request.method == "GET" and "/git/ref/" in path:
            value = refs.get(path.split("/git/ref/")[1])
            return httpx.Response(200 if value else 404, json={"object": {"sha": value}})
        if request.method == "GET" and "/git/commits/" in path:
            return httpx.Response(200, json={"sha": "a" * 40, "tree": {"sha": "b" * 40}})
        if request.method == "GET" and "/git/trees/" in path:
            return httpx.Response(
                200,
                json={
                    "truncated": False,
                    "tree": [{"path": "bug.py", "mode": "100644", "type": "blob"}],
                },
            )
        if path.endswith("/git/blobs"):
            assert payload == {"content": snapshot["files"][0]["content"], "encoding": "utf-8"}
            return httpx.Response(201, json={"sha": "c" * 40})
        if path.endswith("/git/trees"):
            assert payload["base_tree"] == "b" * 40
            return httpx.Response(201, json={"sha": "d" * 40})
        if path.endswith("/git/commits"):
            assert payload["parents"] == ["a" * 40]
            assert "private" not in payload["message"]
            return httpx.Response(201, json={"sha": "e" * 40})
        if path.endswith("/git/refs"):
            assert request.method == "POST" and payload["ref"].startswith(
                ("refs/heads/debug/ci-", "refs/tags/debug-policy/")
            )
            refs[payload["ref"].removeprefix("refs/")] = payload["sha"]
            return httpx.Response(201, json={"object": {"sha": payload["sha"]}})
        raise AssertionError(path)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            broker = GitHubAutomation(client, "private-test-credential")
            date = datetime(2026, 11, 13, tzinfo=UTC)
            first = await broker.prepare_candidate(operation_id, snapshot, date)
            assert first["candidate_commit"] == "e" * 40
            assert first["policy_commit"] == "a" * 40
            assert first["snapshot_digest"] == snapshot["snapshot_digest"]
            assert await broker.prepare_candidate(operation_id, snapshot, date) == first

    asyncio.run(run())
    assert not any(r.method in {"PATCH", "PUT", "DELETE"} for r in requests)
    assert len([r for r in requests if r.url.path.endswith("/git/refs")]) == 2


def test_dispatch_binds_the_selected_candidate_and_returns_only_confirmed_run_identity():
    identifier = uuid4()

    def handle(request):
        assert request.url.path.endswith("/actions/workflows/debug-validation.yml/dispatches")
        payload = json.loads(request.content)
        assert payload["ref"] == "debug-policy/" + "a" * 40
        assert payload["inputs"]["candidate_sha"] == "b" * 40
        assert payload["inputs"]["request_id"] == str(identifier)
        assert payload["return_run_details"] is True
        return httpx.Response(
            200,
            json={
                "workflow_run_id": 123,
                "html_url": "https://github.com/mohammad4242/fitician/actions/runs/123",
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await GitHubAutomation(client, "private-test-credential").dispatch_validation(
                identifier, "a" * 40, "b" * 40, "backend", ["backend/tests/test_debug_runs.py"]
            )
            assert result == 123

    asyncio.run(run())


def test_dispatch_timeout_is_uncertain_and_never_retried_by_the_transport():
    calls = []

    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout("private transport fixture", request=request)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(ValueError, match="github_mutation_uncertain"):
                await GitHubAutomation(client, "private-test-credential").dispatch_validation(
                    uuid4(), "a" * 40, "b" * 40, "migrations", []
                )

    asyncio.run(run())
    assert len(calls) == 1


def test_artifact_bytes_are_verified_and_api_authorization_is_not_forwarded():
    import hashlib
    import io
    import zipfile

    operation_id = uuid4()
    metadata = {"candidate_commit": "a" * 40, "policy_commit": "b" * 40, "profile": "backend"}
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("validation.json", json.dumps(metadata))
    payload = archive.getvalue()
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()

    def handle(request):
        if request.url.host == "artifacts.example.blob.core.windows.net":
            assert "authorization" not in request.headers
            return httpx.Response(200, content=payload)
        if request.url.path.endswith("/artifacts/100/zip"):
            return httpx.Response(
                302,
                headers={
                    "location": "https://artifacts.example.blob.core.windows.net/test?private-signed-fixture"
                },
            )
        return httpx.Response(
            200,
            json={
                "artifacts": [
                    {
                        "id": 100,
                        "name": f"debug-validation-{operation_id}-backend",
                        "digest": digest,
                        "size_in_bytes": len(payload),
                        "expired": False,
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await GitHubAutomation(client, "private-test-credential").validation_artifact(
                123, operation_id, "backend"
            )
            assert result == {"artifact_id": 100, "artifact_digest": digest, "validation": metadata}

    asyncio.run(run())
