import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.debugging.models import DebugRunEvent
from app.debugging.service import append_event, submit_message
from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event
from tests.admin.test_ai_task_settings_api import _admin

ORIGIN = {"Origin": "http://localhost:5173", "Idempotency-Key": "verify-finding-1"}


def setup_case(client, db):
    actor = _admin(client, db)
    occurrence = record_event(
        db,
        EventInput(
            component="api",
            operation="findings_test",
            stage="execution",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
            build="a" * 40,
            sentry_event_id="e" * 32,
            exception_evidence={"values": [{"type": "ValueError", "frames": []}]},
        ),
    )
    run = submit_message(
        db, occurrence.issue_id, actor.id, "inspect", str(uuid4()), occurrence.id, "prepare_fix"
    )
    db.flush()
    return actor, occurrence, run


def test_proposals_require_scoped_evidence_and_never_self_confirm(client, db):
    from app.debugging.findings import proposal_payload

    _, occurrence, run = setup_case(client, db)
    payload = {
        "classification": "hypothesis",
        "text": "Possible missing validation token=private-fixture",
        "evidence_ids": [run.evidence["evidence_id"]],
    }
    safe = proposal_payload(db, run, payload)
    assert "private-fixture" not in safe["text"]
    assert safe["occurrence_id"] == str(occurrence.id)
    assert safe["evidence_version"] == run.evidence["evidence_version"]
    with pytest.raises(ValueError, match="finding_not_supported"):
        proposal_payload(db, run, {**payload, "classification": "confirmed"})
    with pytest.raises(ValueError, match="finding_evidence_not_found"):
        proposal_payload(db, run, {**payload, "evidence_ids": [str(uuid4())]})


def seed_finding(db, run):
    from app.debugging.findings import proposal_payload

    return append_event(
        db,
        run,
        "finding_proposed",
        proposal_payload(
            db,
            run,
            {
                "classification": "hypothesis",
                "text": "Boundary check is missing",
                "evidence_ids": [run.evidence["evidence_id"]],
            },
        ),
    )


def test_findings_survive_reload_and_are_occurrence_environment_scoped(client, db, monkeypatch):
    _, occurrence, run = setup_case(client, db)
    proposal = seed_finding(db, run)
    db.commit()
    base = f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}/findings"
    page = client.get(base, params={"occurrence_id": str(occurrence.id)})
    assert page.status_code == 200
    value = page.json()["findings"][0]
    assert value["id"] == str(proposal.id) and value["verification"] is None
    assert not value["stale"]
    assert client.get(base, params={"occurrence_id": str(uuid4())}).status_code == 404
    assert (
        client.post(
            f"/api/v1/admin/diagnostics/issues/{uuid4()}/findings/{proposal.id}/verify",
            json={
                "before_test_id": str(uuid4()),
                "after_test_id": str(uuid4()),
                "evidence_version": run.evidence["evidence_version"],
                "note": "Reviewed a scoped test",
            },
            headers=ORIGIN,
        ).status_code
        == 404
    )
    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "unrelated-environment")
    assert client.get(base).json()["findings"] == []


def test_verification_requires_admin_review_real_matching_tests_and_is_retry_safe(client, db):
    _, occurrence, run = setup_case(client, db)
    proposal = seed_finding(db, run)
    command = ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_bug.py"]

    def proof(passed, digest):
        return append_event(
            db,
            run,
            "tool_completed",
            {
                "tool": "fitician_run_tests",
                "provenance": "connector_tool",
                "output": json.dumps(
                    {
                        "passed": passed,
                        "exit_code": 0 if passed else 1,
                        "command": command,
                        "image": "sha256:" + "d" * 64,
                        "tree_digest": digest * 64,
                        "output": "Ran 1 test",
                    }
                ),
            },
        )

    before = proof(False, "b")
    after = proof(True, "c")
    run.state = "completed"
    db.commit()
    base = f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}"
    endpoint = f"{base}/findings/{proposal.id}/verify"
    payload = {
        "before_test_id": str(before.id),
        "after_test_id": str(after.id),
        "evidence_version": run.evidence["evidence_version"],
        "note": "Reviewed the same regression test before and after this focused patch.",
    }
    assert client.post(endpoint, json=payload).status_code == 403
    response = client.post(
        endpoint, json={**payload, "before_test_id": str(after.id)}, headers=ORIGIN
    )
    assert response.status_code == 409
    response = client.post(endpoint, json=payload, headers=ORIGIN)
    assert response.status_code == 200
    assert client.post(endpoint, json=payload, headers=ORIGIN).json() == response.json()
    assert (
        client.post(
            endpoint, json={**payload, "note": "Different review"}, headers=ORIGIN
        ).status_code
        == 409
    )
    value = client.get(base + "/findings").json()["findings"][0]
    assert value["verification"]["method"] == "reviewed_regression_comparison"
    assert value["classification"] == "hypothesis"
    assert (
        len(list(db.scalars(select(DebugRunEvent).where(DebugRunEvent.kind == "finding_verified"))))
        == 1
    )


def test_foreign_tool_evidence_and_stale_evidence_cannot_be_verified(client, db):
    from app.debugging.findings import proposal_payload
    from app.observability.evidence_models import DiagnosticExternalEvent

    actor, occurrence, run = setup_case(client, db)
    other = record_event(
        db,
        EventInput(
            component="api",
            operation="different_issue",
            stage="failed",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )
    other_run = submit_message(
        db, other.issue_id, actor.id, "inspect another issue", str(uuid4()), other.id
    )
    foreign = append_event(
        db,
        other_run,
        "tool_completed",
        {
            "tool": "fitician_read_file",
            "provenance": "connector_tool",
            "output": "Different issue source",
        },
    )
    with pytest.raises(ValueError, match="finding_evidence_not_found"):
        proposal_payload(
            db,
            run,
            {
                "classification": "observed_fact",
                "text": "untrusted",
                "evidence_ids": [str(foreign.id)],
            },
        )
    proposal = seed_finding(db, run)
    external = db.scalar(
        select(DiagnosticExternalEvent).where(
            DiagnosticExternalEvent.local_event_id == occurrence.id
        )
    )
    if external is None:
        external = DiagnosticExternalEvent(
            project_id="fitician-backend",
            external_event_id="e" * 32,
            local_event_id=occurrence.id,
            environment="development",
            sync_state="observed",
        )
        db.add(external)
    external.source_evidence = {"mapping_state": "observed"}
    # A new local occurrence must not inherit findings from a different selected occurrence.
    second = record_event(
        db,
        EventInput(
            component="api",
            operation="findings_test",
            stage="execution",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )
    db.commit()
    base = f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}/findings"
    selected = client.get(base, params={"occurrence_id": str(occurrence.id)}).json()["findings"]
    assert selected[0]["id"] == str(proposal.id) and selected[0]["stale"]
    run.state = "completed"
    db.commit()
    response = client.post(
        base + f"/{proposal.id}/verify",
        headers=ORIGIN,
        json={
            "before_test_id": str(uuid4()),
            "after_test_id": str(uuid4()),
            "evidence_version": run.evidence["evidence_version"],
            "note": "Attempt using stale evidence",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "finding_evidence_stale"
    assert client.get(base, params={"occurrence_id": str(second.id)}).json()["findings"] == []


def test_findings_require_administrator_authorization(client, db):
    assert client.get(f"/api/v1/admin/diagnostics/issues/{uuid4()}/findings").status_code == 401
    actor, occurrence, run = setup_case(client, db)
    proposal = seed_finding(db, run)
    actor.is_admin = False
    db.commit()
    base = f"/api/v1/admin/diagnostics/issues/{occurrence.issue_id}/findings"
    assert client.get(base).status_code == 403
    assert (
        client.post(
            base + f"/{proposal.id}/verify",
            headers=ORIGIN,
            json={
                "before_test_id": str(uuid4()),
                "after_test_id": str(uuid4()),
                "evidence_version": run.evidence["evidence_version"],
                "note": "No longer administrator",
            },
        ).status_code
        == 403
    )
