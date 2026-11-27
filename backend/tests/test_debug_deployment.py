from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from tests.test_debug_automation import broker_for, setup_case
from tests.test_debug_host_operations import packet
from tests.test_debug_release_contract import manifest


def prepared_case(db):
    from app.debugging.models import DebugOperation

    actor, occurrence, run, _ = setup_case(db)
    run.action, run.state = "prepare_fix", "completed"
    common = dict(
        run_id=run.id,
        worker_id=broker_for(db, run).id,
        occurrence_id=occurrence.id,
        environment=broker_for(db, run).environment,
        state="succeeded",
        request_hash="a" * 64,
    )
    publication = DebugOperation(
        **common,
        kind="publish_pr",
        submission_key="publication",
        request={"purpose": "repair_publication"},
        result={
            "pr_number": 43,
            "pr_url": "https://github.com/mohammad4242/fitician/pull/43",
            "candidate_commit": "b" * 40,
        },
    )
    observation = DebugOperation(
        **common,
        kind="observe",
        submission_key="observation",
        request={"purpose": "server_observation", "target_environment": "production-germany"},
        result={"observation": packet(), "artifact_verified": True},
    )
    db.add_all([publication, observation])
    db.flush()
    return actor, occurrence, run, publication, observation


def preview():
    return {
        "manifest": manifest(),
        "manifest_sha256": "f" * 64,
        "artifact_id": 120,
        "artifact_digest": "sha256:" + "e" * 64,
        "policy_commit": "a" * 40,
        "pr_number": 43,
    }


def test_deployment_binds_diagnostics_workers_and_rejects_missing_or_extra_readback(db):
    from app.debugging.deployment import queue_deployment, validate_readback

    actor, occurrence, _, publication, observation = prepared_case(db)
    workers = ["debug-worker", "diagnostics-sync-worker"]
    observation.request = {**observation.request, "target_environment": "production-iran"}
    packet_value = {**observation.result["observation"], "target_environment": "production-iran"}
    packet_value["services"] = [{"service": name} for name in workers]
    observation.result = {**observation.result, "observation": packet_value}
    row = queue_deployment(
        db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-workers", 123
    )
    assert row.request["diagnostics_services"] == workers
    row.result = {
        "grant": {
            "commit": "a" * 40,
            "ci_run_id": 123,
            "manifest_sha256": "f" * 64,
            "authorized_at": int(datetime.now(UTC).timestamp()),
        },
        "preview": preview(),
    }
    names = [
        "backend",
        "backend-2",
        "body-analysis-worker",
        "food-photo-worker",
        "notification-worker",
        "scheduler",
        *workers,
        "frontend",
    ]
    proof = {
        "schema_version": 1,
        "operation_id": str(row.id),
        "target_environment": "production-iran",
        "commit": "a" * 40,
        "ci_run_id": 123,
        "manifest_sha256": "f" * 64,
        "captured_at": datetime.now(UTC).isoformat(),
        "images": {key: manifest()["images"][key] for key in ("backend", "frontend")},
        "services": {
            name: {
                "container_id": "b" * 64,
                "image_role": "frontend" if name == "frontend" else "backend",
                "healthy": True,
            }
            for name in names
        },
        "provenance": "fixed_running_image_guard",
        "business_outcome_verified": False,
    }
    value = {"artifact_id": 100, "artifact_digest": "sha256:" + "d" * 64, "readback": proof}
    assert validate_readback(row, value) == value
    for name in workers:
        incomplete = {key: item for key, item in proof["services"].items() if key != name}
        with pytest.raises(ValueError, match="deployment_readback_invalid"):
            validate_readback(row, {**value, "readback": {**proof, "services": incomplete}})
    extra = {**proof["services"], "diagnostics-alert-worker": proof["services"][workers[0]]}
    with pytest.raises(ValueError, match="deployment_readback_invalid"):
        validate_readback(row, {**value, "readback": {**proof, "services": extra}})


def test_deployment_preview_is_not_authority_and_grant_binds_artifact_actor_and_target(db):
    from app.debugging.automation import claim_operation
    from app.debugging.deployment import authorize_deployment, queue_deployment, record_deployment

    actor, occurrence, run, publication, observation = prepared_case(db)
    row = queue_deployment(
        db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-1", 123
    )
    assert row.kind == "deploy" and row.target_environment == "production-germany"
    assert row.occurrence_id == occurrence.id and not row.result.get("grant")
    worker = broker_for(db, run)
    claimed = claim_operation(db, worker)
    record_deployment(db, worker, row.id, claimed.lease_token, "deployment_prepared", preview())
    assert row.state == "awaiting_authorization" and not row.result.get("grant")
    digest = row.result["preview_sha256"]
    with pytest.raises(ValueError, match="deployment_preview_changed"):
        authorize_deployment(db, occurrence.issue_id, row.id, actor.id, "approval-1", "0" * 64)
    authorize_deployment(db, occurrence.issue_id, row.id, actor.id, "approval-1", digest)
    assert row.state == "queued"
    grant = row.result["grant"]
    assert grant["actor_id"] == str(actor.id) and grant["manifest_sha256"] == "f" * 64
    assert grant["target_environment"] == "production-germany" and grant["commit"] == "a" * 40
    assert grant["baseline_sha256"] == observation.result["observation"]["baseline_sha256"]
    assert grant["allow_schema_migrations"] is False
    assert (
        authorize_deployment(db, occurrence.issue_id, row.id, actor.id, "approval-1", digest).id
        == row.id
    )


def test_deployment_rejects_unrelated_evidence_and_overlapping_target(db):
    from app.debugging.deployment import queue_deployment

    actor, occurrence, _, publication, observation = prepared_case(db)
    observation.occurrence_id = uuid4()
    with pytest.raises(ValueError, match="matching_host_observation_required"):
        queue_deployment(
            db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-1", 123
        )
    observation.occurrence_id = occurrence.id
    first = queue_deployment(
        db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-1", 123
    )
    assert (
        queue_deployment(
            db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-1", 123
        ).id
        == first.id
    )
    with pytest.raises(ValueError, match="deployment_target_busy"):
        queue_deployment(
            db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-2", 123
        )


def test_deployment_grant_expiry_blocks_dispatch_and_cannot_be_extended_by_worker(db):
    from app.debugging.automation import claim_operation
    from app.debugging.deployment import authorize_deployment, queue_deployment, record_deployment

    actor, occurrence, run, publication, observation = prepared_case(db)
    worker = broker_for(db, run)
    row = queue_deployment(
        db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-1", 123
    )
    lease = claim_operation(db, worker).lease_token
    record_deployment(db, worker, row.id, lease, "deployment_prepared", preview())
    authorize_deployment(
        db, occurrence.issue_id, row.id, actor.id, "approval-1", row.result["preview_sha256"]
    )
    lease = claim_operation(db, worker).lease_token
    grant = {
        **row.result["grant"],
        "expires_at": int((datetime.now(UTC) - timedelta(seconds=1)).timestamp()),
    }
    row.result = {**row.result, "grant": grant}
    with pytest.raises(ValueError, match="deployment_authorization_expired"):
        record_deployment(db, worker, row.id, lease, "dispatch_intent", {})
    with pytest.raises(ValueError):
        record_deployment(
            db, worker, row.id, lease, "deployment_prepared", {**preview(), "grant": grant}
        )


def test_deployment_preview_and_authorization_require_explicit_admin_csrf_and_issue_scope(
    client, db
):
    from app.debugging.automation import claim_operation
    from app.debugging.deployment import record_deployment
    from tests.admin.test_ai_task_settings_api import _admin

    admin = _admin(client, db)
    actor, occurrence, run, publication, observation = prepared_case(db)
    base = f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}/deployments"
    value = {
        "publication_id": str(publication.id),
        "observation_id": str(observation.id),
        "ci_run_id": 123,
    }
    assert client.post(base, json=value).status_code == 403
    headers = {"Origin": "http://localhost:5173", "Idempotency-Key": "preview-test-1"}
    response = client.post(base, json=value, headers=headers)
    assert response.status_code == 200
    assert client.post(base, json=value, headers=headers).json()["id"] == response.json()["id"]
    from uuid import UUID

    from app.debugging.models import DebugOperation

    row = db.get(DebugOperation, UUID(response.json()["id"]))
    worker = broker_for(db, run)
    lease = claim_operation(db, worker).lease_token
    record_deployment(db, worker, row.id, lease, "deployment_prepared", preview())
    db.commit()
    target = base + f"/{row.id}/authorize"
    payload = {"preview_sha256": row.result["preview_sha256"]}
    assert client.post(target, json=payload).status_code == 403
    cross = f"/api/v1/admin/diagnostics/issues/{uuid4()}/deployments/{row.id}/authorize"
    assert client.post(cross, json=payload, headers=headers).status_code == 404
    assert (
        client.post(
            target, json={**payload, "command": "ssh production"}, headers=headers
        ).status_code
        == 422
    )
    approved = client.post(target, json=payload, headers=headers)
    assert approved.status_code == 200 and approved.json()["result"]["grant"]["actor_id"] == str(
        admin.id
    )
    assert actor.id != admin.id


def test_green_deployment_waits_for_exact_running_image_evidence_and_never_resolves_issue(db):
    from app.debugging.automation import claim_operation
    from app.debugging.deployment import authorize_deployment, queue_deployment, record_deployment
    from app.observability.diagnostics_models import DiagnosticIssue

    actor, occurrence, run, publication, observation = prepared_case(db)
    worker = broker_for(db, run)
    row = queue_deployment(
        db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-1", 123
    )
    lease = claim_operation(db, worker).lease_token
    record_deployment(db, worker, row.id, lease, "deployment_prepared", preview())
    authorize_deployment(
        db, occurrence.issue_id, row.id, actor.id, "approval-1", row.result["preview_sha256"]
    )
    lease = claim_operation(db, worker).lease_token
    record_deployment(db, worker, row.id, lease, "dispatch_intent", {})
    record_deployment(db, worker, row.id, lease, "dispatched", {"workflow_run_id": 456})
    record_deployment(
        db,
        worker,
        row.id,
        lease,
        "deployment_completed",
        {"workflow_run_id": 456, "workflow_conclusion": "success"},
    )
    assert row.state == "verifying" and row.result["deployed"] is False
    proof = {
        "schema_version": 1,
        "operation_id": str(row.id),
        "target_environment": "production-germany",
        "commit": "a" * 40,
        "ci_run_id": 123,
        "manifest_sha256": "f" * 64,
        "captured_at": datetime.now(UTC).isoformat(),
        "images": {"agent": manifest()["images"]["agent"]},
        "services": {
            "agent-service": {"container_id": "b" * 64, "image_role": "agent", "healthy": True}
        },
        "provenance": "fixed_running_image_guard",
        "business_outcome_verified": False,
    }
    value = {"artifact_id": 100, "artifact_digest": "sha256:" + "d" * 64, "readback": proof}
    with pytest.raises(ValueError, match="deployment_readback_invalid"):
        record_deployment(
            db,
            worker,
            row.id,
            lease,
            "deployment_verified",
            {**value, "readback": {**proof, "commit": "b" * 40}},
        )
    record_deployment(db, worker, row.id, lease, "deployment_verified", value)
    assert row.state == "succeeded" and row.result["deployed"] is True
    assert row.result["verified_resolved"] is False
    assert db.get(DiagnosticIssue, occurrence.issue_id).status != "resolved"


def test_transient_error_after_dispatch_retains_target_lock_until_remote_reconciliation(db):
    from app.debugging.automation import claim_operation
    from app.debugging.deployment import authorize_deployment, queue_deployment, record_deployment

    actor, occurrence, run, publication, observation = prepared_case(db)
    worker = broker_for(db, run)
    row = queue_deployment(
        db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-1", 123
    )
    lease = claim_operation(db, worker).lease_token
    record_deployment(db, worker, row.id, lease, "deployment_prepared", preview())
    authorize_deployment(
        db, occurrence.issue_id, row.id, actor.id, "approval-1", row.result["preview_sha256"]
    )
    lease = claim_operation(db, worker).lease_token
    record_deployment(db, worker, row.id, lease, "dispatch_intent", {})
    record_deployment(db, worker, row.id, lease, "dispatched", {"workflow_run_id": 456})
    record_deployment(db, worker, row.id, lease, "failed", {"code": "github_unreachable"})
    assert row.state == "running" and row.error_code == "github_unreachable"
    with pytest.raises(ValueError, match="deployment_target_busy"):
        queue_deployment(
            db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-2", 123
        )


def test_awaiting_deployment_can_be_cancelled_with_actor_audit_and_cannot_then_be_authorized(
    client, db
):
    from sqlalchemy import select

    from app.debugging.automation import claim_operation
    from app.debugging.deployment import queue_deployment, record_deployment
    from app.debugging.models import DebugRunEvent
    from tests.admin.test_ai_task_settings_api import _admin

    administrator = _admin(client, db)
    actor, occurrence, run, publication, observation = prepared_case(db)
    row = queue_deployment(
        db, occurrence.issue_id, publication.id, observation.id, actor.id, "deploy-1", 123
    )
    worker = broker_for(db, run)
    lease = claim_operation(db, worker).lease_token
    record_deployment(db, worker, row.id, lease, "deployment_prepared", preview())
    db.commit()
    base = f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}"
    response = client.post(
        base + f"/operations/{row.id}/cancel", headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200 and response.json()["state"] == "cancelled"
    event = db.scalar(
        select(DebugRunEvent).where(
            DebugRunEvent.run_id == run.id, DebugRunEvent.kind == "automation_cancel_requested"
        )
    )
    assert event.payload["actor_id"] == str(administrator.id)
