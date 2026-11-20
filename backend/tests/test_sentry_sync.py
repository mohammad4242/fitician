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


def test_remote_evidence_keeps_source_coordinates_without_remote_user_content():
    from app.observability.sentry_sync import sanitize_remote_evidence

    result = sanitize_remote_evidence(
        {
            "release": {"version": "fitician-web@" + "b" * 40},
            "user": {"email": "private@example.invalid"},
            "entries": [
                {
                    "type": "exception",
                    "data": {
                        "values": [
                            {
                                "type": "TypeError",
                                "value": "medical secret",
                                "stacktrace": {
                                    "frames": [
                                        {
                                            "filename": "app:///src/Profile.tsx",
                                            "function": "render",
                                            "lineNo": 42,
                                            "colNo": 3,
                                            "vars": {"token": "secret"},
                                            "context": [[42, "secret"]],
                                        }
                                    ]
                                },
                            }
                        ]
                    },
                }
            ],
        },
        expected_commit="b" * 40,
    )
    assert result["release_commit"] == "b" * 40
    assert result["exceptions"][0]["frames"][0] == {
        "filename": "src/Profile.tsx",
        "function": "render",
        "lineno": 42,
        "colno": 3,
    }
    assert "secret" not in str(result)
    assert "private@example.invalid" not in str(result)
    assert (
        sanitize_remote_evidence(
            {"release": {"version": "fitician-web@" + "c" * 40}}, expected_commit="b" * 40
        )["release_match"]
        is False
    )


@pytest.mark.parametrize("expired", [True, False])
def test_last_attempt_interrupted_by_restart_is_recovered_only_after_lease_expiry(db, expired):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from sqlalchemy.orm import Session

    from app.observability.evidence_models import DiagnosticExternalEvent
    from app.observability.sentry_sync import synchronize_one

    lease = uuid4()
    row = DiagnosticExternalEvent(
        project_id="backend",
        external_event_id="b" * 32,
        environment="test",
        sync_state="syncing",
        attempts=12,
        lease_token=lease,
        next_attempt_at=datetime.now(UTC) + timedelta(minutes=-1 if expired else 5),
    )
    db.add(row)
    db.flush()
    requests = []
    with Session(db.bind, join_transaction_mode="create_savepoint") as worker:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda request: requests.append(request) or httpx.Response(500)
            )
        ) as client:
            # A different project/environment must never recover this lease.
            assert not synchronize_one(worker, client, "org", "other", "test")
            assert not synchronize_one(worker, client, "org", "backend", "other")
            assert synchronize_one(worker, client, "org", "backend", "test") is expired
            recovered = worker.get(DiagnosticExternalEvent, row.id)
            assert recovered.attempts == 12
            assert recovered.sync_state == ("exhausted" if expired else "syncing")
            assert recovered.lease_token == (None if expired else lease)
            assert recovered.last_error_code == ("sync_lease_expired" if expired else None)
            assert not synchronize_one(worker, client, "org", "backend", "test")
        assert requests == []  # Recovery must not create a thirteenth external request.
