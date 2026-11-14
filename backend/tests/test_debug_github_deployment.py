import asyncio
import hashlib
import io
import json
import zipfile
from uuid import uuid4

import httpx
import pytest

from app.debugging.github_automation import REPOSITORY, GitHubAutomation
from tests.test_debug_release_contract import manifest


def test_release_preview_requires_merged_selected_repair_exact_main_ci_and_private_manifest():
    from app.debugging.github_deployment import GitHubDeployment

    raw = (json.dumps(manifest(), indent=2) + "\n").encode()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as f:
        f.writestr("manifest.json", raw)
    data = archive.getvalue()
    merged = True

    def handle(r):
        if r.url.host.endswith(".blob.core.windows.net"):
            assert "Authorization" not in r.headers
            return httpx.Response(200, content=data)
        path = r.url.path
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "a" * 40}})
        if path.endswith("/pulls/43"):
            return httpx.Response(
                200,
                json={
                    "merged": merged,
                    "merge_commit_sha": "a" * 40,
                    "base": {"ref": "main", "repo": {"full_name": REPOSITORY}},
                    "head": {"sha": "b" * 40, "repo": {"full_name": REPOSITORY}},
                },
            )
        if path.endswith("/actions/runs/123"):
            return httpx.Response(
                200,
                json={
                    "path": ".github/workflows/ci.yml",
                    "name": "Fitician CI",
                    "head_sha": "a" * 40,
                    "head_branch": "main",
                    "head_repository": {"full_name": REPOSITORY},
                    "event": "push",
                    "status": "completed",
                    "conclusion": "success",
                    "run_attempt": 1,
                },
            )
        if path.endswith("/artifacts/100/zip"):
            return httpx.Response(
                302,
                headers={
                    "Location": "https://artifacts.example.blob.core.windows.net/release?private-fixture"
                },
            )
        if path.endswith("/artifacts"):
            return httpx.Response(
                200,
                json={
                    "artifacts": [
                        {
                            "id": 100,
                            "expired": False,
                            "name": "fitician-release-manifest-" + "a" * 40,
                            "size_in_bytes": len(data),
                            "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
                        }
                    ]
                },
            )
        raise AssertionError(path)

    async def run():
        nonlocal merged
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            github = GitHubDeployment(GitHubAutomation(client, "private-test-credential"))
            proof = await github.preview(
                {"ci_run_id": 123, "pr_number": 43, "candidate_commit": "b" * 40}
            )
            assert proof["manifest_sha256"] == hashlib.sha256(raw).hexdigest()
            assert proof["manifest"] == manifest()
            merged = False
            with pytest.raises(ValueError, match="github_release_not_ready"):
                await github.preview(
                    {"ci_run_id": 123, "pr_number": 43, "candidate_commit": "b" * 40}
                )

    asyncio.run(run())


def test_deploy_dispatch_keeps_owner_gate_and_sends_only_artifact_bound_fixed_inputs():
    import time

    from app.debugging.github_deployment import GitHubDeployment

    operation_id = uuid4()
    grant = {
        "commit": "a" * 40,
        "ci_run_id": 123,
        "manifest_sha256": "b" * 64,
        "target_environment": "production-iran",
        "deploy_kind": "full",
        "baseline_sha256": "c" * 64,
        "expires_at": int(time.time()) + 1000,
        "allow_schema_migrations": False,
    }
    calls = []

    def handle(r):
        if r.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "a" * 40}})
        if r.method == "POST":
            calls.append(json.loads(r.content))
            assert r.url.path.endswith("/deploy-regional.yml/dispatches")
            return httpx.Response(200, json={"workflow_run_id": 456})
        raise AssertionError(r.url.path)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            adapter = GitHubDeployment(GitHubAutomation(client, "private-test-credential"))
            assert await adapter.dispatch(operation_id, grant) == 456
            with pytest.raises(ValueError, match="deployment_authorization_expired"):
                await adapter.dispatch(operation_id, {**grant, "expires_at": 1})

    asyncio.run(run())
    assert len(calls) == 1
    inputs = calls[0]["inputs"]
    assert calls[0]["ref"] == "main" and inputs["operation_id"] == str(operation_id)
    assert inputs["expected_manifest_sha256"] == grant["manifest_sha256"]
    assert inputs["expected_baseline_sha256"] == grant["baseline_sha256"]
    assert inputs["allow_schema_migrations"] == "false" and inputs["owner_approved"] == "true"


@pytest.mark.parametrize("status,content", [(500, b"gateway failure"), (200, b"invalid response")])
def test_ambiguous_mutation_response_is_uncertain_and_never_automatically_retried(status, content):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(status, content=content)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(ValueError, match="github_mutation_uncertain"):
                await GitHubAutomation(client, "private-test-credential").dispatch_validation(
                    uuid4(), "a" * 40, "b" * 40, "migrations", []
                )

    asyncio.run(run())
    assert len(calls) == 1
