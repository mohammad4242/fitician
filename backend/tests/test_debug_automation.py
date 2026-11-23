from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.debugging import automation
from app.debugging.models import DebugOperation
from tests.test_debug_server_evidence import setup_case as original_case


def setup_case(db, actor=None):
    from app.debugging.connectors import enroll_connector

    actor, occurrence, run, job = original_case(db, actor)
    broker, _ = enroll_connector(db, actor.id, "Germany CI", kind="automation")
    run.config_snapshot = {**run.config_snapshot, "automation_worker_id": str(broker.id)}
    return actor, occurrence, run, job


def broker_for(db, run):
    from uuid import UUID

    from app.debugging.models import DebugConnector

    return db.get(DebugConnector, UUID(run.config_snapshot["automation_worker_id"]))


def request():
    from app.debugging.ci_contract import _digest

    value = {
        "base_commit": "a" * 40,
        "tree_digest": "b" * 64,
        "files": [{"path": "bug.py", "content": "def add(a,b): return a+b\n"}],
    }
    return {
        "profile": "backend",
        "tests": ["backend/tests/test_debug_runs.py"],
        "snapshot": {**value, "snapshot_digest": _digest(value)},
    }


def test_validation_queue_is_durable_scoped_and_retry_safe(db):
    actor, occurrence, run, _ = setup_case(db)
    run.action = "prepare_fix"
    first = automation.queue_validation(db, run.id, "tool-1", request())
    assert first.state == "queued" and first.kind == "validate"
    from app.observability.environment import diagnostics_environment

    assert first.environment == diagnostics_environment()
    assert first.occurrence_id == occurrence.id
    assert automation.queue_validation(db, run.id, "tool-1", request()).id == first.id
    with pytest.raises(ValueError, match="automation_idempotency_conflict"):
        automation.queue_validation(
            db, run.id, "tool-1", {**request(), "profile": "migrations", "tests": []}
        )
    assert db.scalar(select(func.count()).select_from(DebugOperation)) == 1
    db.commit()
    db.expire_all()
    restored = automation.claim_operation(db, broker_for(db, run))
    assert restored.id == first.id and restored.lease_token
    assert restored.request["snapshot"]["tree_digest"] == "b" * 64
    actor.is_admin = False
    db.flush()
    with pytest.raises(ValueError, match="automation_not_authorized"):
        automation.authorize_operation(db, restored)


def test_read_only_runs_cannot_submit_a_patch_and_arbitrary_tools_are_rejected(db):
    _, _, run, _ = setup_case(db)
    with pytest.raises(ValueError, match="mutation_not_authorized"):
        automation.queue_validation(db, run.id, "bad", request())
    run.action = "prepare_fix"
    with pytest.raises(ValueError, match="invalid_validation_request"):
        automation.queue_validation(db, run.id, "shell", {**request(), "command": "ssh production"})
    run.cancel_requested = True
    with pytest.raises(ValueError, match="run_no_longer_authorized"):
        automation.queue_validation(db, run.id, "cancelled", request())


def test_restart_preserves_uncertain_dispatch_instead_of_repeating_it(db):
    _, _, run, _ = setup_case(db)
    run.action = "prepare_fix"
    operation = automation.queue_validation(db, run.id, "tool-1", request())
    row = automation.claim_operation(db, broker_for(db, run))
    lease = row.lease_token
    row.state = "dispatching"
    row.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    recovered = automation.claim_operation(db, broker_for(db, run))
    assert recovered.id == operation.id
    assert recovered.state == "uncertain"
    assert recovered.lease_token != lease
    assert recovered.error_code == "dispatch_confirmation_missing"
    assert db.scalar(select(func.count()).select_from(DebugOperation)) == 1


def test_automation_journal_cannot_be_read_across_issues_or_environments(client, db, monkeypatch):
    from tests.admin.test_ai_task_settings_api import _admin

    actor = _admin(client, db)
    _, occurrence, run, _ = setup_case(db, actor)
    run.action = "prepare_fix"
    operation = automation.queue_validation(db, run.id, "tool-1", request())
    db.flush()
    base = f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}/operations"
    response = client.get(base)
    assert response.status_code == 200
    assert response.json()["operations"][0]["id"] == str(operation.id)
    assert "content" not in str(response.json())
    assert client.get(f"/api/v1/admin/diagnostics/issues/{uuid4()}/operations").status_code == 404
    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "foreign")
    assert client.get(base).json()["operations"] == []


def test_connector_submission_requires_its_lease_and_cancellation_is_audited(client, db):
    from app.debugging.connectors import claim_call, enqueue_call, enroll_connector
    from app.debugging.models import DebugRunEvent
    from tests.admin.test_ai_task_settings_api import _admin

    actor = _admin(client, db)
    _, occurrence, run, _ = setup_case(db, actor)
    run.action = "prepare_fix"
    connector, token = enroll_connector(db, actor.id, "Germany")
    call = enqueue_call(db, run, connector, "turn", "fitician_codex_turn", {"messages": []})
    claim_call(db, connector)
    endpoint = f"/api/v1/debug-connectors/{connector.id}/calls/{call.id}/validations"
    payload = {**request(), "lease_token": str(call.lease_token), "key": "test-1"}
    assert client.post(endpoint, json=payload).status_code == 401
    headers = {"Authorization": "Bearer " + token}
    assert (
        client.post(
            endpoint, json={**payload, "lease_token": str(uuid4())}, headers=headers
        ).status_code
        == 409
    )
    response = client.post(endpoint, json=payload, headers=headers)
    assert response.status_code == 200
    assert client.post(endpoint, json=payload, headers=headers).json() == response.json()
    operation_id = response.json()["id"]
    cancel = (
        f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}/operations/{operation_id}/cancel"
    )
    assert client.post(cancel).status_code == 403
    assert client.post(cancel, headers={"Origin": "http://localhost:5173"}).json()[
        "cancel_requested"
    ]
    assert client.post(cancel, headers={"Origin": "http://localhost:5173"}).status_code == 200
    assert (
        db.scalar(
            select(func.count())
            .select_from(DebugRunEvent)
            .where(DebugRunEvent.kind == "automation_cancel_requested")
        )
        == 1
    )


def test_automation_worker_credential_cannot_be_used_as_a_model_connector(client, db):
    from app.debugging.connectors import enroll_connector
    from tests.admin.test_ai_task_settings_api import _admin

    actor = _admin(client, db)
    runtime, runtime_token = enroll_connector(db, actor.id, "Runtime")
    worker, worker_token = enroll_connector(db, actor.id, "Germany broker", kind="automation")
    runtime_headers = {"Authorization": "Bearer " + runtime_token}
    worker_headers = {"Authorization": "Bearer " + worker_token}
    assert (
        client.post(
            f"/api/v1/debug-automation/{worker.id}/poll", json={}, headers=runtime_headers
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"/api/v1/debug-connectors/{runtime.id}/poll", json={}, headers=worker_headers
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"/api/v1/debug-connectors/{worker.id}/poll", json={}, headers=worker_headers
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"/api/v1/debug-automation/{worker.id}/poll", json={}, headers=worker_headers
        ).status_code
        == 200
    )
    assert all(
        row["id"] != str(worker.id)
        for row in client.get("/api/v1/admin/diagnostics/connectors").json()
    )


def test_dispatch_intent_is_single_use_and_conflicting_receipts_are_rejected(db):
    actor, occurrence, run, _ = setup_case(db)
    run.action = "prepare_fix"
    operation = automation.queue_validation(db, run.id, "test-once", request())
    broker = broker_for(db, run)
    leased = automation.claim_operation(db, broker)
    lease = leased.lease_token
    snapshot = request()["snapshot"]
    preparation = {
        "base_commit": "a" * 40,
        "candidate_commit": "c" * 40,
        "policy_commit": "d" * 40,
        "branch": "debug/ci-" + str(operation.id),
        "policy_ref": "debug-policy/" + "d" * 40,
        "snapshot_digest": snapshot["snapshot_digest"],
        "tree_digest": snapshot["tree_digest"],
    }
    automation.record_progress(db, broker, operation.id, lease, "prepared", preparation)
    first = automation.record_progress(db, broker, operation.id, lease, "dispatch_intent", {})
    assert first["disposition"] == "dispatch_once"
    replay = automation.record_progress(db, broker, operation.id, lease, "dispatch_intent", {})
    assert replay["disposition"] == "reconcile_only"
    automation.record_progress(
        db, broker, operation.id, lease, "dispatched", {"workflow_run_id": 123}
    )
    validation = {
        "candidate_commit": "c" * 40,
        "policy_commit": "d" * 40,
        "profile": "backend",
        "tests": request()["tests"],
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
        automation.record_progress(
            db,
            broker,
            operation.id,
            lease,
            "completed",
            {**receipt, "validation": {**validation, "candidate_commit": "0" * 40}},
        )
    complete = automation.record_progress(db, broker, operation.id, lease, "completed", receipt)
    assert complete["operation"]["state"] == "succeeded"
    assert (
        automation.record_progress(db, broker, operation.id, lease, "completed", receipt)
        == complete
    )
    with pytest.raises(ValueError, match="automation_receipt_conflict"):
        automation.record_progress(
            db, broker, operation.id, lease, "completed", {**receipt, "artifact_id": 457}
        )
    assert operation.result["artifact_verified"] is True
    from app.observability.diagnostics_models import DiagnosticIssue

    assert db.get(DiagnosticIssue, occurrence.issue_id).status == "new"


def test_ci_connection_probe_is_idempotent_and_never_queues_a_paid_model_turn(client, db):
    from app.debugging.models import DebugMessage, DebugRun
    from tests.admin.test_ai_task_settings_api import _admin

    actor = _admin(client, db)
    _, occurrence, old_run, _ = setup_case(db, actor)
    old_run.state = "completed"
    broker = broker_for(db, old_run)
    broker.last_seen = datetime.now(UTC)
    broker.capabilities = {
        "github_authenticated": True,
        "workflow_installed": True,
        "policy_commit": "a" * 40,
    }
    db.flush()
    path = f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}/automation-probe"
    headers = {"Origin": "http://localhost:5173", "Idempotency-Key": "connection-probe-fixture"}
    payload = {"occurrence_id": str(occurrence.id)}
    first = client.post(path, headers=headers, json=payload)
    assert first.status_code == 200
    assert client.post(path, headers=headers, json=payload).json() == first.json()
    operation = db.get(DebugOperation, first.json()["id"])
    run = db.get(DebugRun, operation.run_id)
    assert run.state == "completed" and run.config_snapshot["mode"] == "ci_connection_probe"
    assert run.evidence["occurrence_id"] == str(occurrence.id)
    assert db.scalar(select(func.count()).select_from(DebugOperation)) == 1
    assert db.scalar(
        select(DebugMessage).where(
            DebugMessage.thread_id == run.thread_id, DebugMessage.role == "system"
        )
    )


def test_ci_tool_status_is_scoped_to_the_selected_occurrence_and_live_call_lease(client, db):
    from app.debugging.connectors import claim_call, enqueue_call, enroll_connector

    actor, occurrence, run, _ = setup_case(db)
    run.action = "prepare_fix"
    operation = automation.queue_validation(db, run.id, "test-status", request())
    connector, token = enroll_connector(db, actor.id, "Germany runtime")
    enqueue_call(db, run, connector, "status", "fitician_ci_status", {})
    leased = claim_call(db, connector)
    db.commit()
    path = f"/api/v1/debug-connectors/{connector.id}/calls/{leased['id']}/ci-status"
    headers = {"Authorization": "Bearer " + token}
    response = client.post(path, headers=headers, json={"lease_token": leased["lease_token"]})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["operations"]] == [str(operation.id)]
    assert response.json()["operations"][0]["occurrence_id"] == str(occurrence.id)
    assert "request" not in response.json()["operations"][0]
    assert client.post(path, headers=headers, json={"lease_token": str(uuid4())}).status_code == 409
    operation.occurrence_id = uuid4()
    db.commit()
    assert (
        client.post(path, headers=headers, json={"lease_token": leased["lease_token"]}).json()[
            "operations"
        ]
        == []
    )
    actor.is_admin = False
    db.commit()
    assert (
        client.post(path, headers=headers, json={"lease_token": leased["lease_token"]}).status_code
        == 401
    )
