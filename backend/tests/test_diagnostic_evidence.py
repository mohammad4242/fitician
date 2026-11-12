from uuid import uuid4

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
