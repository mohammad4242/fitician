from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.observability.diagnostics_models import DiagnosticIssue
from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event
from app.observability.evidence import exception_evidence
from app.observability.evidence_models import DiagnosticEvidenceSnapshot


def test_original_chain_has_relative_coordinates_and_no_content():
    try:
        try:
            raise ValueError("private health form")
        except ValueError as cause:
            raise RuntimeError("Bearer secret") from cause
    except RuntimeError as error:
        evidence = exception_evidence(error)
    assert [item["type"] for item in evidence["values"]] == ["ValueError", "RuntimeError"]
    assert "private" not in str(evidence)
    assert "Bearer" not in str(evidence)
    assert all("lineno" in frame for item in evidence["values"] for frame in item["frames"])


def test_evidence_is_immutable_and_retry_does_not_increment_occurrence(db):
    event_id = uuid4()
    event = EventInput(
        event_id=event_id,
        component="api",
        operation="test",
        stage="execution",
        platform="backend",
        category="application_bug",
        severity="error",
        error_code="UNHANDLED_EXCEPTION",
        outcome="failure",
        exception_evidence={"values": [{"type": "RuntimeError", "frames": []}]},
        sentry_event_id="a" * 32,
    )
    first = record_event(db, event)
    record_event(db, event)
    snapshot = db.scalar(select(DiagnosticEvidenceSnapshot))
    assert snapshot.event_id == first.id
    assert snapshot.issue_id == first.issue_id
    assert snapshot.payload["exception"]["values"][0]["type"] == "RuntimeError"
    assert snapshot.sentry_event_id == "a" * 32
    assert db.scalar(select(func.count()).select_from(DiagnosticEvidenceSnapshot)) == 1
    assert db.get(DiagnosticIssue, first.issue_id).count == 1


def test_retention_keeps_evidence_and_occurrence_together(db):
    from datetime import UTC, datetime, timedelta

    from app.observability.diagnostics_service import cleanup_retention

    event = EventInput(
        component="api",
        operation="test",
        stage="execution",
        platform="backend",
        category="application_bug",
        severity="error",
        error_code="UNHANDLED_EXCEPTION",
        outcome="failure",
        exception_evidence={"values": []},
    )
    row = record_event(db, event)
    row.timestamp = datetime.now(UTC) - timedelta(days=40)
    db.flush()
    cleanup_retention(db)
    assert db.get(type(row), row.id) is not None


@pytest.mark.parametrize("anchor", ["run", "operation"])
def test_retention_keeps_chat_selected_occurrence_without_stack_and_expires_unreferenced(
    db, anchor
):
    from datetime import UTC, datetime, timedelta

    from app.debugging.models import (
        DebugConnector,
        DebugMessage,
        DebugOperation,
        DebugRun,
        DebugThread,
    )
    from app.observability.diagnostics_models import DiagnosticEvent
    from app.observability.diagnostics_service import cleanup_retention

    events = [
        record_event(
            db,
            EventInput(
                component="worker",
                operation="test",
                stage="run",
                platform="backend",
                category="application_bug",
                severity="error",
                error_code="UNHANDLED_EXCEPTION",
                outcome="failure",
            ),
        )
        for _ in range(2)
    ]
    for event in events:
        event.timestamp = datetime.now(UTC) - timedelta(days=40)
    thread = DebugThread(issue_id=events[0].issue_id, environment="test")
    db.add(thread)
    db.flush()
    # Legacy/null and malformed evidence must not turn NOT IN(NULL) into a global pin.
    for index, evidence in enumerate(
        (
            {"occurrence_id": str(events[0].id)} if anchor == "run" else {},
            {},
            {"occurrence_id": "not-a-uuid"},
        )
    ):
        message = DebugMessage(thread_id=thread.id, role="assistant", content="synthetic")
        db.add(message)
        db.flush()
        run = DebugRun(
            thread_id=thread.id,
            message_id=message.id,
            state="completed",
            evidence=evidence,
            config_snapshot={},
        )
        db.add(run)
        db.flush()
        if anchor == "operation" and index == 0:
            worker = DebugConnector(
                name="synthetic",
                environment="test",
                repository="mohammad4242/fitician",
                token_hash=uuid4().hex * 2,
                capabilities={},
            )
            db.add(worker)
            db.flush()
            db.add(
                DebugOperation(
                    run_id=run.id,
                    occurrence_id=events[0].id,
                    worker_id=worker.id,
                    environment="test",
                    kind="observe",
                    state="failed",
                    submission_key="synthetic",
                    request_hash="a" * 64,
                    request={},
                    result={},
                )
            )
    db.flush()
    selected_id, unreferenced_id = (event.id for event in events)
    result = cleanup_retention(db)
    assert result["events"] == 1
    assert db.get(DiagnosticEvent, selected_id) is not None
    assert db.get(DiagnosticEvent, unreferenced_id) is None
