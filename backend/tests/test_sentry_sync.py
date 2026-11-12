import httpx
import pytest

from app.observability.sentry_sync import SyncFailure, fetch_event


def test_fetch_is_narrow_and_does_not_follow_untrusted_redirect():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "http://private.invalid/secret"})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SyncFailure) as failure:
            fetch_event(client, "org", "backend", "a" * 32)
    assert failure.value.code == "upstream_rejected"
    assert len(requests) == 1
    assert requests[0].url.path == "/api/0/projects/org/backend/events/" + "a" * 32 + "/"


def test_rate_limit_is_reported_without_treating_id_as_delivery():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(429))) as client:
        with pytest.raises(SyncFailure) as failure:
            fetch_event(client, "org", "backend", "a" * 32)
    assert failure.value.code == "rate_limited"


def test_polling_links_external_group_without_creating_local_occurrences(db, monkeypatch):
    from sqlalchemy import select

    from app.observability.diagnostics_models import DiagnosticIssue
    from app.observability.diagnostics_schemas import EventInput
    from app.observability.diagnostics_service import record_event
    from app.observability.evidence_models import (
        DiagnosticExternalEvent,
        DiagnosticExternalIssueLink,
    )
    from app.observability.sentry_sync import synchronize_one

    monkeypatch.setenv("SENTRY_PROJECT", "backend")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")
    row = record_event(
        db,
        EventInput(
            component="api",
            operation="test",
            stage="execution",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
            exception_evidence={"values": []},
            sentry_event_id="a" * 32,
        ),
    )
    db.flush()
    remote = {
        "eventID": "a" * 32,
        "groupID": "123",
        "tags": [
            {"key": "environment", "value": "test"},
            {"key": "diagnostic_event_id", "value": str(row.id)},
        ],
    }
    # synchronize_one commits its durable lease; use an independent worker-owned session.
    from sqlalchemy.orm import Session

    event_id, issue_id = row.id, row.issue_id
    with Session(db.bind, join_transaction_mode="create_savepoint") as worker:
        with httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=remote))
        ) as client:
            assert synchronize_one(worker, client, "org", "backend", "test")
            assert not synchronize_one(worker, client, "org", "backend", "test")
        external = worker.scalar(
            select(DiagnosticExternalEvent).where(
                DiagnosticExternalEvent.local_event_id == event_id
            )
        )
        assert external.sync_state == "observed"
        assert worker.scalar(select(DiagnosticExternalIssueLink)).external_issue_id == "123"
        assert worker.get(DiagnosticIssue, issue_id).count == 1
