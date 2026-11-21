from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from tests.test_debug_automation import broker_for
from tests.test_debug_deployment import prepared_case


def deployed_case(db):
    from app.debugging.models import DebugOperation

    actor, occurrence, run, publication, observation = prepared_case(db)
    publication.request = {
        **publication.request,
        "profile": "backend",
        "tests": ["backend/tests/test_debug_runs.py"],
    }
    image = "sha256:" + "c" * 64
    packet = deepcopy(observation.result["observation"])
    packet["services"] = [{"service": "agent-service", "image_id": image}]
    packet["captured_at"] = datetime.now(UTC).isoformat()
    observation.result = {"artifact_verified": True, "observation": packet}
    deployment = DebugOperation(
        run_id=run.id,
        worker_id=broker_for(db, run).id,
        occurrence_id=occurrence.id,
        environment=publication.environment,
        target_environment="production-germany",
        kind="deploy",
        state="succeeded",
        submission_key="deployed",
        request_hash="a" * 64,
        request={"publication_id": str(publication.id)},
        result={
            "deployed": True,
            "verified_resolved": False,
            "artifact_id": 101,
            "artifact_digest": "sha256:" + "d" * 64,
            "grant": {"commit": "a" * 40, "manifest_sha256": "f" * 64},
            "readback": {
                "commit": "a" * 40,
                "manifest_sha256": "f" * 64,
                "target_environment": "production-germany",
                "services": {"agent-service": {"image_role": "agent"}},
                "images": {"agent": {"image_id": image}},
            },
        },
    )
    db.add(deployment)
    db.flush()
    return actor, occurrence, run, deployment, observation


def test_replay_binds_deployed_commit_selected_occurrence_tests_and_fresh_target(db):
    from app.debugging.replay import queue_replay

    actor, occurrence, run, deployment, observation = deployed_case(db)
    row = queue_replay(db, occurrence.issue_id, deployment.id, observation.id, actor.id, "replay-1")
    assert row.kind == "replay" and row.occurrence_id == occurrence.id
    assert row.run_id == run.id and row.request["release_commit"] == "a" * 40
    assert row.request["tests"] == ["backend/tests/test_debug_runs.py"]
    assert row.request["deployment_artifact_digest"] == deployment.result["artifact_digest"]
    assert not row.result.get("verified_resolved")
    assert (
        queue_replay(
            db, occurrence.issue_id, deployment.id, observation.id, actor.id, "replay-1"
        ).id
        == row.id
    )
    with pytest.raises(ValueError, match="replay_already_active"):
        queue_replay(db, occurrence.issue_id, deployment.id, observation.id, actor.id, "replay-2")
    db.commit()
    db.expire_all()
    from app.debugging.automation import claim_operation

    assert claim_operation(db, broker_for(db, run)).id == row.id


def test_replay_rejects_cross_issue_changed_images_and_non_admin(db):
    from app.debugging.replay import queue_replay

    actor, occurrence, _, deployment, observation = deployed_case(db)
    with pytest.raises(ValueError, match="operation_not_found"):
        queue_replay(db, uuid4(), deployment.id, observation.id, actor.id, "replay-1")
    packet = observation.result["observation"]
    packet["services"][0]["image_id"] = "sha256:" + "b" * 64
    observation.result = {"artifact_verified": True, "observation": packet}
    with pytest.raises(ValueError, match="replay_target_changed"):
        queue_replay(db, occurrence.issue_id, deployment.id, observation.id, actor.id, "replay-1")
    actor.is_admin = False
    with pytest.raises(ValueError, match="deployment_not_authorized"):
        queue_replay(db, occurrence.issue_id, deployment.id, observation.id, actor.id, "replay-1")


def test_replay_requires_verified_deployment_not_green_workflow_or_pr(db):
    from app.debugging.replay import queue_replay

    actor, occurrence, _, deployment, observation = deployed_case(db)
    deployment.result = {**deployment.result, "deployed": False}
    with pytest.raises(ValueError, match="verified_deployment_required"):
        queue_replay(db, occurrence.issue_id, deployment.id, observation.id, actor.id, "replay-1")


def test_replay_preparation_cannot_change_tested_commit_or_grant_deployment(db):
    from app.debugging.automation import claim_operation, record_progress
    from app.debugging.replay import queue_replay

    actor, occurrence, run, deployment, observation = deployed_case(db)
    row = queue_replay(db, occurrence.issue_id, deployment.id, observation.id, actor.id, "replay-1")
    worker = broker_for(db, run)
    lease = claim_operation(db, worker).lease_token
    with pytest.raises(ValueError, match="automation_snapshot_mismatch"):
        record_progress(
            db,
            worker,
            row.id,
            lease,
            "prepared",
            {
                "candidate_commit": "b" * 40,
                "policy_commit": "c" * 40,
            },
        )
    record_progress(
        db,
        worker,
        row.id,
        lease,
        "prepared",
        {
            "candidate_commit": "a" * 40,
            "policy_commit": "c" * 40,
        },
    )
    assert row.result["candidate_commit"] == "a" * 40 and "grant" not in row.result
    assert (
        record_progress(db, worker, row.id, lease, "dispatch_intent", {})["disposition"]
        == "dispatch_once"
    )
    assert (
        record_progress(db, worker, row.id, lease, "dispatch_intent", {})["disposition"]
        == "reconcile_only"
    )


def test_replay_verified_artifact_is_regression_evidence_and_never_resolves_issue(db):
    from app.debugging.automation import claim_operation, record_progress
    from app.debugging.replay import queue_replay
    from app.observability.diagnostics_models import DiagnosticIssue

    actor, occurrence, run, deployment, observation = deployed_case(db)
    row = queue_replay(db, occurrence.issue_id, deployment.id, observation.id, actor.id, "replay-1")
    worker = broker_for(db, run)
    lease = claim_operation(db, worker).lease_token
    record_progress(
        db,
        worker,
        row.id,
        lease,
        "prepared",
        {
            "candidate_commit": "a" * 40,
            "policy_commit": "c" * 40,
        },
    )
    record_progress(db, worker, row.id, lease, "dispatch_intent", {})
    record_progress(db, worker, row.id, lease, "dispatched", {"workflow_run_id": 123})
    validation = {
        "candidate_commit": "a" * 40,
        "policy_commit": "c" * 40,
        "profile": row.request["profile"],
        "tests": row.request["tests"],
        "image": "sha256:" + "e" * 64,
        "passed": True,
        "exit_code": 0,
        "exercised": 1,
        "skipped": 0,
        "failures": 0,
        "failed_tests": [],
        "failed_stage": None,
        "diagnostics": [],
    }
    receipt = {
        "workflow_run_id": 123,
        "workflow_conclusion": "success",
        "artifact_id": 456,
        "artifact_digest": "sha256:" + "f" * 64,
        "validation": validation,
    }
    with pytest.raises(ValueError, match="automation_snapshot_mismatch"):
        record_progress(
            db,
            worker,
            row.id,
            lease,
            "completed",
            {
                **receipt,
                "validation": {**validation, "candidate_commit": "b" * 40},
            },
        )
    record_progress(db, worker, row.id, lease, "completed", receipt)
    assert row.state == "succeeded" and row.result["artifact_verified"] is True
    assert row.result["controlled_replay_passed"] is True
    assert row.result["production_business_outcome_verified"] is False
    assert row.result["verified_resolved"] is False
    assert db.get(DiagnosticIssue, occurrence.issue_id).status != "resolved"


def test_replay_endpoint_requires_admin_csrf_and_rejects_untrusted_options(client, db):
    from tests.admin.test_ai_task_settings_api import _admin

    _admin(client, db)
    _, occurrence, _, deployment, observation = deployed_case(db)
    db.commit()
    url = (
        f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}/deployments/{deployment.id}/replay"
    )
    body = {"observation_id": str(observation.id)}
    headers = {"Origin": "http://localhost:5173", "Idempotency-Key": "replay-1"}
    assert client.post(url, json=body, headers={"Idempotency-Key": "replay-1"}).status_code == 403
    assert (
        client.post(url, json={**body, "command": "ssh production"}, headers=headers).status_code
        == 422
    )
    result = client.post(url, json=body, headers=headers)
    assert result.status_code == 200, result.json()
    assert result.json()["kind"] == "replay"
    assert result.json()["occurrence_id"] == str(occurrence.id)


def test_replay_requester_revocation_and_foreign_environment_block_claim(db, monkeypatch):
    from app.auth.models import User
    from app.debugging.automation import authorize_operation
    from app.debugging.replay import queue_replay

    actor, occurrence, _, deployment, observation = deployed_case(db)
    reviewer = User(email="replay-reviewer@example.invalid", password_hash="fixture", is_admin=True)
    db.add(reviewer)
    db.flush()
    row = queue_replay(
        db, occurrence.issue_id, deployment.id, observation.id, reviewer.id, "replay-1"
    )
    reviewer.is_admin = False
    assert actor.is_admin
    with pytest.raises(ValueError, match="automation_not_authorized"):
        authorize_operation(db, row)
    reviewer.is_admin = True
    monkeypatch.setattr("app.debugging.automation.diagnostics_environment", lambda: "foreign")
    with pytest.raises(ValueError, match="automation_not_authorized"):
        authorize_operation(db, row)


def test_github_replay_uses_only_protected_main_dispatch_without_creating_git_objects():
    import asyncio
    import json

    import httpx

    from app.debugging.github_automation import GitHubAutomation

    writes = []

    def handle(request):
        path = request.url.path
        if request.method == "POST":
            writes.append(path)
            assert path.endswith("/actions/workflows/debug-validation.yml/dispatches")
            body = json.loads(request.content)
            assert body["ref"] == "main"
            assert body["inputs"]["candidate_sha"] == "a" * 40
            return httpx.Response(200, json={"workflow_run_id": 123})
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "c" * 40}})
        if path.endswith("/actions/workflows/debug-validation.yml"):
            return httpx.Response(
                200, json={"state": "active", "path": ".github/workflows/debug-validation.yml"}
            )
        if "/contents/" in path:
            assert request.url.params["ref"] == "c" * 40
            return httpx.Response(200, json={"type": "file"})
        if "/compare/" in path:
            return httpx.Response(
                200, json={"status": "ahead", "merge_base_commit": {"sha": "a" * 40}}
            )
        raise AssertionError(path)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            github = GitHubAutomation(client, "private-fixture")
            proof = await github.prepare_replay("a" * 40)
            assert proof == {"candidate_commit": "a" * 40, "policy_commit": "c" * 40}
            assert not writes
            assert (
                await github.dispatch_replay(
                    uuid4(), "c" * 40, "a" * 40, "backend", ["backend/tests/test_debug_runs.py"]
                )
                == 123
            )
            with pytest.raises(ValueError, match="github_invalid_identity"):
                await github.dispatch_replay(
                    uuid4(), "d" * 40, "a" * 40, "backend", ["backend/tests/test_debug_runs.py"]
                )
            assert len(writes) == 1

    asyncio.run(run())


def test_replay_restart_reconciles_uncertain_dispatch_without_preparing_a_branch():
    import asyncio

    from app.debugging.automation_client import advance

    job = {
        "id": str(uuid4()),
        "kind": "replay",
        "state": "uncertain",
        "lease_token": str(uuid4()),
        "result": {"policy_commit": "a" * 40},
    }
    calls = []

    class Github:
        async def find_validation(self, identifier, policy):
            assert policy == "a" * 40
            return {"id": 123}

        async def dispatch_replay(self, *args):
            raise AssertionError("Uncertain replay must never be dispatched again")

    async def rpc(path, payload):
        calls.append(payload["stage"])
        assert payload["result"] == {"workflow_run_id": 123}
        return {"operation": {**job, "state": "running"}, "disposition": "recorded"}

    assert asyncio.run(advance(job, Github(), rpc))["state"] == "running"
    assert calls == ["dispatched"]


def test_migration_downgrade_refuses_to_remove_persisted_replay_audit(db):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy.exc import DBAPIError

    from app.debugging.replay import queue_replay

    actor, occurrence, _, deployment, observation = deployed_case(db)
    row = queue_replay(db, occurrence.issue_id, deployment.id, observation.id, actor.id, "replay-1")
    path = Path(__file__).parents[1] / "alembic/versions/20261121_187_controlled_replay.py"
    spec = importlib.util.spec_from_file_location("controlled_replay_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(DBAPIError, match="Retain replay audit"):
        with db.begin_nested(), Operations.context(MigrationContext.configure(db.connection())):
            module.downgrade()
    db.refresh(row)
    assert row.kind == "replay" and row.occurrence_id == occurrence.id
