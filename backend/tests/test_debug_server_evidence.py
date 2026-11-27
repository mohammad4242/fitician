import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.auth.models import User
from app.body_analysis.models import BodyAnalysis
from app.body_photos.models import BodyPhotoSession
from app.debugging import server_evidence
from app.debugging.connectors import claim_call, enqueue_call, enroll_connector
from app.debugging.models import DebugRunEvent
from app.debugging.service import claim_run, submit_message
from app.observability.diagnostics_models import DiagnosticEvent, DiagnosticIssue
from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event
from tests.admin.test_ai_task_settings_api import _admin


def setup_case(db, actor=None):
    actor = actor or User(
        id=uuid4(), email=f"{uuid4()}@example.invalid", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    session = BodyPhotoSession(user_id=actor.id, purpose="initial_plan")
    db.add(session)
    db.flush()
    job = BodyAnalysis(
        session_id=session.id,
        revision=1,
        provider="openrouter",
        model_id="fixture/model",
        prompt_version="test",
        schema_version="1",
        status="failed",
        attempt_count=2,
        raw_result={"medical_form": "private-health-fixture"},
        error_message="private-prompt-fixture",
    )
    db.add(job)
    db.flush()
    occurrence = record_event(
        db,
        EventInput(
            component="body_analysis_worker",
            operation="body_analysis",
            stage="provider",
            platform="worker",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
            resource_id=job.id,
            trace_id="c" * 32,
            operation_id=str(uuid4()),
            build="a" * 40,
        ),
    )
    run = submit_message(
        db,
        occurrence.issue_id,
        actor.id,
        "inspect selected occurrence",
        str(uuid4()),
        occurrence.id,
    )
    run = claim_run(db)
    return actor, occurrence, run, job


def test_collection_is_scoped_private_passive_and_idempotent(db, monkeypatch):
    actor, occurrence, run, job = setup_case(db)
    monkeypatch.setenv("APP_BUILD_SHA", "b" * 40)
    monkeypatch.setenv("SENTRY_API_TOKEN", "private-credential-fixture")
    related = record_event(
        db,
        EventInput(
            component="body_analysis_worker",
            operation="body_analysis",
            stage="accepted",
            platform="worker",
            outcome="started",
            category="provider_failure",
            severity="info",
            error_code="WORKFLOW_STARTED",
            resource_id=job.id,
            trace_id=occurrence.trace_id,
        ),
    )
    foreign = record_event(
        db,
        EventInput(
            component="api",
            operation="foreign_issue",
            stage="failed",
            platform="backend",
            outcome="failure",
            severity="error",
            category="application_bug",
            error_code="UNHANDLED_EXCEPTION",
            trace_id=occurrence.trace_id,
        ),
    )
    infra = record_event(
        db,
        EventInput(
            component="redis",
            operation="infrastructure_probe",
            stage="reachability",
            platform="infrastructure",
            category="infrastructure_failure",
            severity="error",
            outcome="failure",
            error_code="SERVICE_UNAVAILABLE",
        ),
    )
    infra.timestamp = datetime.now(UTC) - timedelta(minutes=20)
    db.flush()
    counts = (
        db.scalar(select(func.count()).select_from(DiagnosticEvent)),
        db.scalar(select(func.sum(DiagnosticIssue.count))),
    )
    first = server_evidence.collect(db, run.id, "api-tool-1", process_role="debug_worker")
    packet = json.loads(first["output"])
    assert packet["occurrence_id"] == str(occurrence.id)
    assert packet["release"]["reported_commit"] == "b" * 40
    assert packet["release"]["image_digest"] is None
    assert packet["jobs"][0]["id"] == str(job.id)
    assert packet["jobs"][0]["attempt_count"] == 2
    identifiers = {row["id"] for row in packet["observations"]}
    assert str(related.id) in identifiers and str(foreign.id) not in identifiers
    assert packet["infrastructure"][0]["stale"] is True
    assert packet["infrastructure"][0]["current_status"] == "not_verified"
    assert packet["business_outcome_verified"] is False
    for forbidden in [
        "private-health-fixture",
        "private-prompt-fixture",
        "private-credential-fixture",
        str(actor.id),
    ]:
        assert forbidden not in first["output"]
    assert counts == (
        db.scalar(select(func.count()).select_from(DiagnosticEvent)),
        db.scalar(select(func.sum(DiagnosticIssue.count))),
    )
    monkeypatch.setenv("APP_BUILD_SHA", "d" * 40)
    assert server_evidence.collect(db, run.id, "api-tool-1", process_role="debug_worker") == first
    assert (
        db.scalar(
            select(func.count())
            .select_from(DebugRunEvent)
            .where(DebugRunEvent.payload["server_evidence_key"].as_string() == "api-tool-1")
        )
        == 1
    )


def test_collection_stops_after_cancellation_or_environment_change(db, monkeypatch):
    _, _, run, _ = setup_case(db)
    run.cancel_requested = True
    with pytest.raises(ValueError, match="run_no_longer_authorized"):
        server_evidence.collect(db, run.id, "cancelled", process_role="debug_worker")
    run.cancel_requested = False
    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "another-environment")
    with pytest.raises(ValueError, match="run_no_longer_authorized"):
        server_evidence.collect(db, run.id, "foreign-environment", process_role="debug_worker")


def test_server_observations_are_citable_but_cannot_verify_a_cause(db):
    from app.debugging.findings import _test_proof, proposal_payload

    _, _, run, _ = setup_case(db)
    snapshot = server_evidence.collect(db, run.id, "facts", process_role="debug_worker")
    finding = proposal_payload(
        db,
        run,
        {
            "classification": "observed_fact",
            "text": "دو تلاش ثبت شده است.",
            "evidence_ids": [snapshot["evidence_id"]],
        },
    )
    assert finding["evidence_ids"] == [snapshot["evidence_id"]]
    from uuid import UUID

    with pytest.raises(ValueError, match="regression_evidence_required"):
        _test_proof(db, run, UUID(snapshot["evidence_id"]), True)


def test_old_worker_lease_cannot_collect_evidence(db):
    _, _, run, _ = setup_case(db)
    with pytest.raises(ValueError, match="run_lease_lost"):
        server_evidence.collect(
            db, run.id, "stale", process_role="debug_worker", required_lease=uuid4()
        )


def test_connector_evidence_endpoint_enforces_lease_admin_and_issue_scope(client, db):
    actor = _admin(client, db)
    _, occurrence, run, _ = setup_case(db, actor)
    connector, token = enroll_connector(db, actor.id, "Germany")
    call = enqueue_call(db, run, connector, "codex-turn", "fitician_codex_turn", {"messages": []})
    claim_call(db, connector)
    endpoint = f"/api/v1/debug-connectors/{connector.id}/calls/{call.id}/server-evidence"
    payload = {"lease_token": str(call.lease_token), "key": "tool-1"}
    assert client.post(endpoint, json=payload).status_code == 401
    bearer = {"Authorization": "Bearer " + token}
    assert (
        client.post(
            endpoint, json={**payload, "lease_token": str(uuid4())}, headers=bearer
        ).status_code
        == 409
    )
    response = client.post(endpoint, json=payload, headers=bearer)
    assert response.status_code == 200
    assert client.post(endpoint, json=payload, headers=bearer).json() == response.json()
    base = f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}/runs/{run.id}/server-evidence"
    run.state = "completed"
    db.flush()
    assert client.get(base).status_code == 200
    assert (
        client.get(
            f"/api/v1/admin/diagnostics/issues/{uuid4()}/runs/{run.id}/server-evidence"
        ).status_code
        == 404
    )
    actor.is_admin = False
    db.flush()
    assert client.get(base).status_code == 403
