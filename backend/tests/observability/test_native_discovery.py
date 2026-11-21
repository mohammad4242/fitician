"""Native SDK capture is independently discoverable; remote status is never local authority."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.observability.diagnostics_models import DiagnosticEvent, DiagnosticIssue
from app.observability.evidence import evidence_package


def remote_native(**overrides):
    return {
        "eventID": "d" * 32,
        "groupID": "12345",
        "platform": "native",
        "dateCreated": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        "tags": [
            {"key": "environment", "value": "test"},
            {"key": "release", "value": "fitician-mobile@" + "a" * 40},
            {"key": "level", "value": "fatal"},
        ],
        "contexts": {"os": {"name": "Android"}},
        "user": {"email": "private@example.invalid", "ip_address": "192.0.2.1"},
        "message": "medical private",
        "request": {"headers": {"Authorization": "secret"}},
        "entries": [
            {
                "type": "exception",
                "data": {
                    "values": [
                        {
                            "type": "SIGSEGV",
                            "value": "private health form",
                            "stacktrace": {
                                "frames": [
                                    {
                                        "filename": "app:///mobile/App.tsx",
                                        "function": "render",
                                        "lineNo": 42,
                                        "vars": {"password": "secret"},
                                        "context": [[42, "private"]],
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        ],
        **overrides,
    }


def test_sdk_native_page_import_is_durable_deduplicated_private_and_scoped(db, monkeypatch):
    from app.observability.evidence_models import DiagnosticDiscoveryCursor
    from app.observability.sentry_discovery import discover_native_page

    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "test")
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=[remote_native()])

    with Session(db.bind, join_transaction_mode="create_savepoint") as worker:
        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            assert discover_native_page(worker, client, "org", "mobile", "test")
            assert not discover_native_page(worker, client, "org", "mobile", "test")
            cursor = worker.scalar(select(DiagnosticDiscoveryCursor))
            assert cursor.last_success_at and cursor.watermark and cursor.imported_count == 1
            cursor.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
            worker.commit()
            assert discover_native_page(worker, client, "org", "mobile", "test")
        assert worker.scalar(select(func.count()).select_from(DiagnosticEvent)) == 1
        row = worker.scalar(select(DiagnosticEvent))
        issue = worker.get(DiagnosticIssue, row.issue_id)
        assert issue.count == 1 and issue.confidence == "unknown"
        assert row.timestamp < datetime.now(UTC) - timedelta(minutes=30)
        assert row.build == "a" * 40 and row.platform == "android"
        evidence = evidence_package(worker, row.issue_id, row.id)
        assert evidence["sync_state"] == "observed" and evidence["delivery"] == "observed"
        assert evidence["external_issue_id"] == "12345"
        assert evidence["snapshot"]["provenance"] == "sentry_native_capture"
        assert evidence["external_source"]["release_match"] is True
        encoded = json.dumps(evidence)
        for sensitive in ("private", "secret", "192.0.2.1", "Authorization", "password"):
            assert sensitive not in encoded
    assert all(r.url.host == "sentry.io" and r.url.params["full"] == "true" for r in requests)
    assert requests[0].url.params["per_page"] == "10"


@pytest.mark.parametrize(
    "change",
    [
        {"platform": "javascript"},
        {"tags": [{"key": "environment", "value": "other"}]},
        {
            "tags": [
                {"key": "environment", "value": "test"},
                {"key": "diagnostic_event_id", "value": "already-reported"},
            ]
        },
        {"eventID": "malformed"},
        {"dateCreated": "not-a-date"},
        {"dateCreated": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
        {"entries": [{"type": "exception", "data": {"values": [{"type": "HTTPError"}]}}]},
        {"tags": None},
        {"tags": [{"key": {}, "value": []}]},
    ],
)
def test_unrelated_or_expected_events_are_not_imported(db, change, monkeypatch):
    from app.observability.sentry_discovery import discover_native_page

    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "test")
    with Session(db.bind, join_transaction_mode="create_savepoint") as worker:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=[remote_native(**change)])
            )
        ) as client:
            discover_native_page(worker, client, "org", "mobile", "test")
        assert worker.scalar(select(func.count()).select_from(DiagnosticEvent)) == 0


def test_pagination_restarts_from_committed_cursor_and_outage_keeps_progress(db, monkeypatch):
    from app.observability.evidence_models import DiagnosticDiscoveryCursor
    from app.observability.sentry_discovery import discover_native_page

    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "test")
    url = "https://sentry.io/api/0/projects/org/mobile/events/?cursor=0:10:0"
    responses = [
        httpx.Response(
            200,
            json=[remote_native()],
            headers={
                "Link": f'<{url}>; rel="next"; results="true"; cursor="0:10:0"',
            },
        ),
        httpx.Response(429, headers={"Retry-After": "300"}),
        httpx.Response(200, json=[]),
    ]
    requests = []

    def handle(request):
        requests.append(request)
        return responses.pop(0)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        for index in range(3):
            # Each page/failure uses a new worker session, like a process restart.
            with Session(db.bind, join_transaction_mode="create_savepoint") as worker:
                if index:
                    state = worker.scalar(select(DiagnosticDiscoveryCursor))
                    state.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
                    worker.commit()
                assert discover_native_page(worker, client, "org", "mobile", "test")
                state = worker.scalar(select(DiagnosticDiscoveryCursor))
                assert state.cursor == (None if index == 2 else "0:10:0")
                assert (state.last_error_code == "rate_limited") is (index == 1)
                if index == 1:
                    assert state.next_attempt_at > datetime.now(UTC) + timedelta(seconds=290)
        assert requests[1].url.params["cursor"] == requests[2].url.params["cursor"] == "0:10:0"
        assert requests[0].url.params["end"] == requests[2].url.params["end"]


@pytest.mark.parametrize(
    "link",
    [
        '<http://127.0.0.1/secret?cursor=0:10:0>; rel="next"; results="true"',
        "<https://sentry.io/api/0/projects/org/other/events/?cursor=0:10:0>; "
        'rel="next"; results="true"',
    ],
)
def test_untrusted_pagination_cannot_advance_or_make_another_request(db, link, monkeypatch):
    from app.observability.evidence_models import DiagnosticDiscoveryCursor
    from app.observability.sentry_discovery import discover_native_page

    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "test")
    requests = []
    with Session(db.bind, join_transaction_mode="create_savepoint") as worker:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda r: (
                    requests.append(r)
                    or httpx.Response(200, json=[remote_native()], headers={"Link": link})
                )
            )
        ) as client:
            discover_native_page(worker, client, "org", "mobile", "test")
        state = worker.scalar(select(DiagnosticDiscoveryCursor))
        assert state.last_error_code == "invalid_pagination" and state.watermark is None
        assert len(requests) == 1
        assert worker.scalar(select(func.count()).select_from(DiagnosticEvent)) == 0


def test_tag_release_is_usable_but_conflicting_release_stays_unknown():
    from app.observability.sentry_sync import sanitize_remote_evidence

    remote = remote_native()
    assert sanitize_remote_evidence(remote, expected_commit="a" * 40)["release_commit"] == "a" * 40
    remote["release"] = {"version": "fitician-mobile@" + "b" * 40}
    assert sanitize_remote_evidence(remote, expected_commit="a" * 40)["release_commit"] is None


def test_native_cpp_function_name_survives_without_argument_values():
    from app.observability.sentry_sync import sanitize_remote_evidence

    remote = remote_native()
    frame = remote["entries"][0]["data"]["values"][0]["stacktrace"]["frames"][0]
    frame["function"] = "fitician::BodyVision::run(secret_argument=private_value)"
    result = sanitize_remote_evidence(remote, expected_commit="a" * 40)
    assert result["exceptions"][0]["frames"][0]["function"] == "fitician::BodyVision::run"
    assert "private_value" not in json.dumps(result)


def test_expired_worker_response_is_fenced_after_another_worker_claim(db, monkeypatch):
    from uuid import uuid4

    from app.observability.evidence_models import DiagnosticDiscoveryCursor
    from app.observability.sentry_discovery import discover_native_page

    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "test")
    with Session(db.bind, join_transaction_mode="create_savepoint") as worker:

        def handle(request):
            state = worker.scalar(select(DiagnosticDiscoveryCursor))
            state.lease_token = uuid4()
            worker.commit()
            return httpx.Response(200, json=[remote_native()])

        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            assert discover_native_page(worker, client, "org", "mobile", "test")
        state = worker.scalar(select(DiagnosticDiscoveryCursor))
        assert state.watermark is None and state.imported_count == 0
        assert worker.scalar(select(func.count()).select_from(DiagnosticEvent)) == 0


def test_cross_environment_discovery_cannot_create_a_cursor_or_call_sentry(db, monkeypatch):
    from app.observability.sentry_discovery import discover_native_page
    from app.observability.sentry_sync import SyncFailure

    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "test")
    requests = []
    with httpx.Client(transport=httpx.MockTransport(lambda r: requests.append(r))) as client:
        with pytest.raises(SyncFailure, match="scope_mismatch"):
            discover_native_page(db, client, "org", "mobile", "production-iran")
    assert not requests


def test_sync_health_is_admin_only_environment_and_project_scoped(client, db, monkeypatch):
    from uuid import uuid4

    from app.auth.models import User
    from app.observability.evidence_models import DiagnosticDiscoveryCursor

    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "test")
    monkeypatch.setenv("SENTRY_ORG", "org")
    monkeypatch.setenv("SENTRY_MOBILE_PROJECT", "mobile")
    email = f"discovery-admin-{uuid4()}@example.com"
    assert (
        client.post(
            "/api/v1/auth/register",
            headers={"Origin": "http://localhost:5173"},
            json={"email": email, "password": "long test password"},
        ).status_code
        == 201
    )
    user = db.scalar(select(User).where(User.email == email))
    user.is_admin = True
    for organization, project, environment in [
        ("org", "mobile", "test"),
        ("org", "mobile", "other"),
        ("foreign", "mobile", "test"),
        ("org", "unauthorized", "test"),
    ]:
        db.add(
            DiagnosticDiscoveryCursor(
                organization=organization, project_id=project, environment=environment
            )
        )
    db.commit()
    response = client.get("/api/v1/admin/diagnostics/sentry-health")
    assert response.status_code == 200
    scopes = response.json()["native_discovery"]
    assert len(scopes) == 1 and scopes[0]["project"] == "mobile"
    assert scopes[0]["environment"] == "test" and scopes[0]["state"] == "stale"


@pytest.mark.parametrize("platform", ["native", "javascript"])
def test_ingested_native_event_can_await_grouping_without_losing_or_duplicating_it(
    db, monkeypatch, platform
):
    from app.observability.evidence_models import DiagnosticExternalEvent
    from app.observability.sentry_discovery import discover_native_page
    from app.observability.sentry_sync import synchronize_one

    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "test")
    with Session(db.bind, join_transaction_mode="create_savepoint") as worker:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=[remote_native(groupID=None)])
            )
        ) as client:
            discover_native_page(worker, client, "org", "mobile", "test")
        event = worker.scalar(select(DiagnosticEvent))
        assert event is not None
        evidence = evidence_package(worker, event.issue_id, event.id)
        assert evidence["delivery"] == "observed" and evidence["external_issue_id"] is None
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=remote_native(platform=platform))
            )
        ) as client:
            assert synchronize_one(worker, client, "org", "mobile", "test")
        external = worker.scalar(select(DiagnosticExternalEvent))
        assert external.sync_state == ("observed" if platform == "native" else "retrying")
        assert worker.scalar(select(func.count()).select_from(DiagnosticEvent)) == 1
