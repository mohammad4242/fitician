import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from app.debugging.github_automation import GitHubAutomation
from tests.test_debug_automation import request as validation_request


def test_host_dispatch_only_uses_current_protected_main_and_fixed_inputs():
    identifier = uuid4()
    posted = []

    def handle(request):
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "a" * 40}})
        if request.url.path.endswith("/dispatches"):
            payload = json.loads(request.content)
            assert payload == {
                "ref": "main",
                "inputs": {
                    "operation_id": str(identifier),
                    "policy_commit": "a" * 40,
                    "target": "germany",
                    "trace_id": "b" * 32,
                },
            }
            posted.append(payload)
            return httpx.Response(204)
        if request.url.path.endswith("/runs"):
            return httpx.Response(
                200,
                json={
                    "workflow_runs": [
                        {
                            "id": 123,
                            "display_title": "Debug observation " + str(identifier),
                            "head_sha": "a" * 40,
                            "path": ".github/workflows/debug-server-observation.yml",
                            "event": "workflow_dispatch",
                            "head_repository": {"full_name": "mohammad4242/fitician"},
                        }
                    ]
                },
            )
        raise AssertionError(request.url.path)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            github = GitHubAutomation(client, "private-test-credential")
            assert (
                await github.dispatch_observation(
                    identifier, "a" * 40, "production-germany", "b" * 32
                )
                == 123
            )
            with pytest.raises(ValueError, match="github_invalid_identity"):
                await github.dispatch_observation(identifier, "c" * 40, "production-germany", None)
            with pytest.raises(ValueError, match="github_invalid_identity"):
                await github.dispatch_observation(identifier, "a" * 40, "ssh other-host", None)

    asyncio.run(run())
    assert len(posted) == 1


def test_host_artifact_is_private_hash_verified_and_rejects_tampering():
    import hashlib
    import io
    import zipfile

    identifier = uuid4()
    data = {"schema_version": 1, "target_environment": "production-germany"}
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("observation.json", json.dumps(data))
    payload = archive.getvalue()
    tampered = False

    def handle(request):
        if request.url.host == "artifacts.example.blob.core.windows.net":
            assert "Authorization" not in request.headers
            return httpx.Response(200, content=payload + b"changed" if tampered else payload)
        if request.url.path.endswith("/artifacts/100/zip"):
            return httpx.Response(
                302,
                headers={
                    "location": "https://artifacts.example.blob.core.windows.net/observation?private-fixture"
                },
            )
        return httpx.Response(
            200,
            json={
                "artifacts": [
                    {
                        "id": 100,
                        "name": "fitician-server-observation-" + str(identifier),
                        "expired": False,
                        "size_in_bytes": len(payload),
                        "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
                    }
                ]
            },
        )

    async def run():
        nonlocal tampered
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            github = GitHubAutomation(client, "private-test-credential")
            assert (await github.observation_artifact(123, identifier))["observation"] == data
            tampered = True
            with pytest.raises(ValueError, match="github_artifact_invalid"):
                await github.observation_artifact(123, identifier)

    asyncio.run(run())


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


def test_pr_publication_is_exact_tested_candidate_and_reuses_an_existing_draft():
    validation_id = uuid4()
    proof = {
        "candidate_commit": "c" * 40,
        "base_commit": "a" * 40,
        "branch": "debug/ci-" + str(validation_id),
        "policy_commit": "d" * 40,
        "workflow_run_id": 123,
        "artifact_id": 456,
        "artifact_digest": "sha256:" + "e" * 64,
        "validation": {
            "passed": True,
            "exercised": 3,
            "profile": "backend",
            "tests": ["backend/tests/test_debug_runs.py"],
            "image": "sha256:" + "f" * 64,
        },
    }
    request_value = {
        "validation_id": str(validation_id),
        "proof": proof,
        "title": "fix(debug-agent): repair tested behavior",
        "profile": "backend",
        "tests": proof["validation"]["tests"],
        "snapshot": validation_request()["snapshot"],
    }
    created = []
    existing = []

    def handle(request):
        path = request.url.path
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "a" * 40}})
        if "/git/ref/heads/debug/ci-" in path:
            return httpx.Response(200, json={"object": {"sha": "c" * 40}})
        if "/compare/" in path:
            return httpx.Response(
                200,
                json={
                    "status": "ahead",
                    "merge_base_commit": {"sha": "a" * 40},
                    "files": [{"filename": "bug.py"}],
                },
            )
        if path.endswith("/pulls"):
            if request.method == "GET":
                return httpx.Response(200, json=existing)
            payload = json.loads(request.content)
            assert payload["draft"] is True and payload["base"] == "main"
            assert payload["head"] == proof["branch"]
            assert "c" * 40 in payload["body"] and "exercised: 3" in payload["body"]
            created.append(payload)
            existing.append(
                {
                    "number": 43,
                    "html_url": "https://github.com/mohammad4242/fitician/pull/43",
                    "state": "open",
                    "draft": True,
                    "head": {"sha": "c" * 40, "ref": proof["branch"]},
                    "base": {"ref": "main"},
                }
            )
            return httpx.Response(201, json=existing[0])
        raise AssertionError(path)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            github = GitHubAutomation(client, "private-test-credential")

            async def validation_run(run_id):
                return {
                    "id": run_id,
                    "head_sha": "d" * 40,
                    "event": "workflow_dispatch",
                    "path": ".github/workflows/debug-validation.yml",
                    "display_title": "Debug validation " + str(validation_id),
                    "status": "completed",
                    "conclusion": "success",
                    "head_repository": {"full_name": "mohammad4242/fitician"},
                }

            async def artifact(*args):
                return {
                    "artifact_id": 456,
                    "artifact_digest": proof["artifact_digest"],
                    "validation": proof["validation"],
                }

            github.validation_run = validation_run
            github.validation_artifact = artifact
            first = await github.publish_validated_pr(request_value, create=True)
            assert first["pr_number"] == 43
            assert await github.publish_validated_pr(request_value, create=False) == first

    asyncio.run(run())
    assert len(created) == 1
