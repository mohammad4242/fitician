from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.observability.diagnostics_models import DiagnosticIssue, DiagnosticStatusHistory
from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event


def native_event():
    return EventInput(
        component="mobile_native",
        operation="application_runtime",
        stage="native_crash",
        platform="android",
        category="application_bug",
        severity="critical",
        error_code="NATIVE_CRASH",
        exception_type="SIGSEGV",
        outcome="failure",
    )


def test_late_external_occurrence_preserves_source_time_and_does_not_reopen_resolved_issue(db):
    now = datetime.now(UTC)
    first = record_event(db, native_event(), occurred_at=now - timedelta(hours=2))
    issue = db.get(DiagnosticIssue, first.issue_id)
    issue.status = "resolved"
    db.add(
        DiagnosticStatusHistory(
            issue_id=issue.id,
            previous_status="new",
            new_status="resolved",
            created_at=now - timedelta(hours=1),
        )
    )
    db.flush()
    delayed = record_event(db, native_event(), occurred_at=now - timedelta(hours=3))
    assert delayed.timestamp == now - timedelta(hours=3)
    assert issue.count == 2 and issue.status == "resolved" and issue.regression_count == 0
    assert issue.first_seen == now - timedelta(hours=3)
    assert issue.last_seen == now - timedelta(hours=2)
    latest = native_event()
    record_event(db, latest, occurred_at=now - timedelta(minutes=30))
    assert issue.status == "new" and issue.regression_count == 1 and issue.count == 3
    # Retry of the exact external occurrence cannot increment the count.
    latest = latest.model_copy(update={"event_id": delayed.id})
    record_event(db, latest, occurred_at=now - timedelta(hours=3))
    assert issue.count == 3


def test_external_time_cannot_be_supplied_by_untrusted_client_or_without_timezone(db):
    for arguments in [
        {"trusted": False, "occurred_at": datetime.now(UTC)},
        {"occurred_at": datetime.now()},
        {"occurred_at": datetime.now(UTC) + timedelta(hours=1)},
    ]:
        with pytest.raises(ValueError, match="trusted_occurrence_time_required"):
            record_event(db, native_event(), **arguments)
    assert db.scalar(select(DiagnosticIssue)) is None


def test_historical_occurrence_without_resolution_time_keeps_resolution_unknown(db):
    now = datetime.now(UTC)
    row = record_event(db, native_event(), occurred_at=now - timedelta(hours=2))
    issue = db.get(DiagnosticIssue, row.issue_id)
    issue.status = "resolved"
    db.flush()
    record_event(db, native_event(), occurred_at=now - timedelta(minutes=30))
    assert issue.count == 2 and issue.status == "resolved" and issue.regression_count == 0
