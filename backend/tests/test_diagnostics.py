from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.auth.models import User
from app.observability.diagnostics_models import (
    DiagnosticAlert,
    DiagnosticEvent,
    DiagnosticIssue,
    DiagnosticStatusHistory,
)
from app.observability.diagnostics_schemas import ClientBatch, EventInput
from app.observability.diagnostics_service import cleanup_retention, record_event, safe_record


def _event(
    *,
    severity: str = "error",
    category: str = "api_failure",
    outcome: str = "failure",
    event_id=None,
) -> EventInput:
    return EventInput(
        event_id=event_id,
        component="frontend",
        operation="load_profile",
        stage="request",
        platform="web",
        category=category,
        severity=severity,
        error_code="API_REQUEST_FAILED",
        outcome=outcome,
    )


def test_grouping_increments_counters_without_user_in_fingerprint(db):
    users = [
        User(email=f"diagnostics-{uuid4()}@example.com", password_hash="test-hash"),
        User(email=f"diagnostics-{uuid4()}@example.com", password_hash="test-hash"),
    ]
    db.add_all(users)
    db.flush()
    first = record_event(db, _event(), user_id=users[0].id)
    second = record_event(db, _event(), user_id=users[1].id)
    db.flush()

    issues = list(db.scalars(select(DiagnosticIssue)))
    assert len(issues) == 1
    assert issues[0].count == 2
    assert issues[0].regression_count == 0
    assert first.issue_id == second.issue_id
    assert db.scalar(select(DiagnosticEvent).where(DiagnosticEvent.id == first.id)) is not None


def test_resolved_issue_reopens_as_a_regression(db):
    record_event(db, _event())
    issue = db.scalar(select(DiagnosticIssue))
    assert issue is not None
    issue.status = "resolved"
    db.flush()

    record_event(db, _event())
    db.refresh(issue)

    assert issue.status == "new"
    assert issue.count == 2
    assert issue.regression_count == 1


def test_stage_and_expected_events_do_not_create_issues(db):
    record_event(db, _event(outcome="started"))
    record_event(db, _event(outcome="success", severity="info"))
    record_event(db, _event(category="quota_limit"))
    record_event(db, _event(category="invalid_input"))
    record_event(db, _event(category="safety_restriction"))
    record_event(db, _event(category="business_rejection"))
    record_event(db, _event(category="auth_failure"))

    assert db.scalar(select(DiagnosticIssue)) is None


def test_duplicate_event_id_does_not_increment_issue_count(db):
    event_id = uuid4()
    first = record_event(db, _event(event_id=event_id))
    duplicate = record_event(db, _event(event_id=event_id))
    db.flush()

    issue = db.get(DiagnosticIssue, first.issue_id)
    assert issue is not None
    assert issue.count == 1
    assert duplicate.id == first.id
    assert db.scalar(select(DiagnosticEvent).where(DiagnosticEvent.id == event_id)) is not None


def test_client_payload_forbids_server_owned_and_free_text_fields():
    data = {
        "event_id": str(uuid4()),
        "platform": "web",
        "component": "ReactRoot",
        "operation": "render",
        "stage": "caught",
        "error_code": "CLIENT_RENDER_ERROR",
    }
    assert len(ClientBatch(events=[data]).events) == 1
    for forbidden in ("user_id", "category", "severity", "confidence", "message", "details"):
        with pytest.raises(ValidationError):
            ClientBatch(events=[{**data, forbidden: "must not be accepted"}])


def test_alert_threshold_and_one_hour_cooldown(db):
    for _ in range(5):
        record_event(db, _event())
    db.flush()
    assert len(list(db.scalars(select(DiagnosticAlert)))) == 1
    for _ in range(5):
        record_event(db, _event())
    db.flush()
    assert len(list(db.scalars(select(DiagnosticAlert)))) == 1


def test_retention_caps_a_run_at_one_thousand(db):
    old = datetime.now(UTC) - timedelta(days=31)
    for _ in range(1001):
        db.add(
            DiagnosticEvent(
                component="worker",
                operation="job",
                stage="run",
                platform="backend",
                category="job_failure",
                severity="error",
                error_code="JOB_FAILED",
                outcome="failure",
                timestamp=old,
            )
        )
    db.flush()

    removed = cleanup_retention(db)

    assert removed["events"] == 1000
    assert db.scalar(select(DiagnosticEvent).where(DiagnosticEvent.timestamp == old)) is not None


def test_safe_record_swallows_database_failure(test_settings, monkeypatch):
    from app.observability import diagnostics_service

    def fail(_settings):
        raise RuntimeError("database connection secret must not leak")

    monkeypatch.setattr(diagnostics_service, "isolated_session", fail)
    safe_record(test_settings, _event())


@pytest.mark.parametrize(
    "path", ["overview", "issues", "events", "alerts", "generations", "infrastructure"]
)
def test_diagnostic_reads_require_admin(client, db, path):
    assert client.get(f"/api/v1/admin/diagnostics/{path}").status_code == 401
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:5173"},
        json={"email": f"member-{uuid4()}@example.com", "password": "long test password"},
    )
    assert response.status_code == 201
    assert client.get(f"/api/v1/admin/diagnostics/{path}").status_code == 403


def test_authenticated_ingestion_is_private_deduplicated_and_admin_status_is_csrf_protected(
    client, db
):
    headers = {"Origin": "http://localhost:5173"}
    email = f"telemetry-{uuid4()}@example.com"
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=headers,
            json={"email": email, "password": "long test password"},
        ).status_code
        == 201
    )
    event = {
        "event_id": str(uuid4()),
        "platform": "web",
        "component": "WebTransport",
        "operation": "request",
        "stage": "failed",
        "error_code": "API_REQUEST_FAILED",
        "request_id": "diagnostic-api-correlation",
        "http_status": 503,
    }
    assert (
        client.post(
            "/api/v1/diagnostics/client",
            headers=headers,
            json={"events": [{**event, "message": "secret"}]},
        ).status_code
        == 422
    )
    for _ in range(2):
        assert (
            client.post(
                "/api/v1/diagnostics/client", headers=headers, json={"events": [event]}
            ).status_code
            == 202
        )
    issue = db.scalar(select(DiagnosticIssue))
    assert issue is not None and issue.count == 1 and issue.confidence == "unknown"
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    user.is_admin = True
    db.commit()
    response = client.get(f"/api/v1/admin/diagnostics/issues/{issue.id}")
    assert response.status_code == 200
    assert response.json()["events"][0]["event_id"] == event["event_id"]
    assert response.json()["affected_user_count"] == 1
    assert (
        client.patch(
            f"/api/v1/admin/diagnostics/issues/{issue.id}", json={"status": "resolved"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/admin/diagnostics/issues/{issue.id}",
            headers=headers,
            json={"status": "resolved", "note": "Verified operation"},
        ).status_code
        == 200
    )
    assert db.scalar(select(DiagnosticStatusHistory)).actor_user_id == user.id
    assert client.get("/api/v1/admin/diagnostics/events?request_id=other&limit=10").json() == []
    assert (
        len(
            client.get(
                "/api/v1/admin/diagnostics/events?request_id=diagnostic-api-correlation&limit=10"
            ).json()
        )
        == 1
    )


def test_overview_uses_real_terminal_denominators_and_all_time_buckets(client, db):
    from app.auth.dependencies import get_current_user

    admin = User(email=f"admin-{uuid4()}@example.com", password_hash="hash", is_admin=True)
    db.add(admin)
    db.flush()
    client.app.dependency_overrides[get_current_user] = lambda: admin
    record_event(db, _event().model_copy(update={"http_status": 503, "platform": "backend"}))
    record_event(
        db,
        _event(outcome="success", severity="info").model_copy(
            update={"http_status": 200, "platform": "backend"}
        ),
    )
    record_event(db, _event(outcome="stage", severity="info"))
    result = client.get("/api/v1/admin/diagnostics/overview?hours=24").json()
    assert result["event_count"] == 3
    assert result["failure_count"] == 1
    assert result["http_response_count"] == {"success": 1, "failure": 1}
    assert result["error_rate"] == 0.5
    assert sum(row["count"] for row in result["trend"]) == 2


def test_abandoned_attempt_is_unknown_and_does_not_change_business_data(db):
    from datetime import UTC, datetime, timedelta

    from app.entitlements.models import EntitlementUsageEvent
    from app.observability.diagnostics_service import detect_abandoned_attempts

    event = _event(outcome="started", severity="info").model_copy(
        update={"operation_id": str(uuid4()), "operation": "nutrition_generation"}
    )
    row = record_event(db, event)
    row.timestamp = datetime.now(UTC) - timedelta(minutes=31)
    db.flush()
    assert detect_abandoned_attempts(db) == 1
    assert detect_abandoned_attempts(db) == 0
    incident = db.scalar(
        select(DiagnosticEvent).where(DiagnosticEvent.error_code == "WORKFLOW_OUTCOME_UNCONFIRMED")
    )
    assert incident is not None and incident.severity == "warning"
    assert db.scalar(select(EntitlementUsageEvent)) is None


def test_expected_client_rejections_do_not_raise_admin_alerts(client, db):
    from app.auth.dependencies import get_current_user

    member = User(email=f"client-{uuid4()}@example.com", password_hash="hash")
    db.add(member)
    db.flush()
    client.app.dependency_overrides[get_current_user] = lambda: member
    # Exercise service semantics directly; auth guards are covered by API tests.
    for status in (400, 401, 403, 409, 422, 429):
        record_event(
            db,
            _event(category="business_rejection", severity="warning").model_copy(
                update={"http_status": status}
            ),
        )
    assert db.scalar(select(DiagnosticIssue)) is None
    assert db.scalar(select(DiagnosticAlert)) is None


def test_telemetry_rejects_oversized_body_before_json_validation(client):
    assert (
        client.post(
            "/api/v1/diagnostics/client",
            content=b"x" * 17000,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )


def test_confirmed_cause_requires_trusted_deterministic_exception_and_location(db):
    evidence = _event().model_copy(
        update={"exception_type": "ZeroDivisionError", "source_location": "engine.py:42"}
    )
    known = record_event(db, evidence)
    assert db.get(DiagnosticIssue, known.issue_id).confidence == "confirmed"
    unknown = record_event(
        db, evidence.model_copy(update={"source_location": "engine.py:43"}), trusted=False
    )
    assert db.get(DiagnosticIssue, unknown.issue_id).confidence == "unknown"


@pytest.mark.parametrize("hours", [1, 24, 168, 720])
def test_every_dashboard_time_filter_accepts_query_strings(client, db, hours):
    from app.auth.dependencies import get_current_user

    admin = User(email=f"window-{uuid4()}@example.com", password_hash="hash", is_admin=True)
    db.add(admin)
    db.flush()
    client.app.dependency_overrides[get_current_user] = lambda: admin
    for endpoint in ("overview", "issues", "events", "generations"):
        response = client.get(f"/api/v1/admin/diagnostics/{endpoint}?hours={hours}")
        assert response.status_code == 200
    assert client.get("/api/v1/admin/diagnostics/overview?hours=2").status_code == 422


def test_durable_dead_letter_reconciliation_is_private_and_idempotent(db):
    from app.observability.diagnostics_jobs import reconcile_job_failures
    from tests.notifications.test_notification_delivery import _pending_delivery

    delivery, _token = _pending_delivery(db)
    delivery.status = "dead_letter"
    delivery.last_error = "PROVIDER_ERROR"
    delivery.attempt_count = 3
    db.commit()
    assert reconcile_job_failures(db) == 1
    assert reconcile_job_failures(db) == 0
    event = db.scalar(select(DiagnosticEvent).where(DiagnosticEvent.resource_id == delivery.id))
    assert event is not None and event.user_id is not None and event.retry_count == 3
    assert event.error_code == "PROVIDER_ERROR"
    assert "delivery-token" not in event.__dict__.values()
    assert db.scalar(select(DiagnosticIssue)).count == 1


def test_infrastructure_reports_observed_database_and_unknown_unconfigured_services(client, db):
    from app.auth.dependencies import get_current_user

    admin = User(email=f"infra-{uuid4()}@example.com", password_hash="hash", is_admin=True)
    db.add(admin)
    db.flush()
    client.app.dependency_overrides[get_current_user] = lambda: admin
    client.app.state.agent_http_client = None
    client.app.state.redis = None
    response = client.get("/api/v1/admin/diagnostics/infrastructure")
    assert response.status_code == 200
    signals = {item["component"]: item for item in response.json()["signals"]}
    assert signals["database"]["status"] == "reachable"
    assert signals["redis"]["status"] == "unknown"
    assert signals["workers"]["status"] == "unknown"
    assert all(item["business_operation_verified"] is False for item in signals.values())
    assert response.json()["queues"]["body_analysis"]["stale_leases"] == 0


def test_safe_client_exception_location_is_persisted_without_confirming_cause(client, db):
    origin = {"Origin": "http://localhost:5173"}
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=origin,
            json={"email": f"client-stack-{uuid4()}@example.com", "password": "long test password"},
        ).status_code
        == 201
    )
    event = {
        "event_id": str(uuid4()),
        "platform": "web",
        "component": "ReactRoot",
        "operation": "render",
        "stage": "caught",
        "error_code": "CLIENT_RENDER_ERROR",
        "exception_type": "TypeError",
        "source_location": "WorkoutPage-AbCd1234.js:1:321",
    }
    assert (
        client.post(
            "/api/v1/diagnostics/client", headers=origin, json={"events": [event]}
        ).status_code
        == 202
    )
    row = db.scalar(select(DiagnosticEvent).where(DiagnosticEvent.id == event["event_id"]))
    assert row.exception_type == "TypeError" and row.source_location == event["source_location"]
    assert db.get(DiagnosticIssue, row.issue_id).confidence == "unknown"
    for field, value in (
        ("exception_type", "PrivateMedicalValue"),
        ("source_location", "/private/form.tsx:2:3"),
        ("source_location", "https://example.com/assets/index-AbCd1234.js:1:2"),
    ):
        assert (
            client.post(
                "/api/v1/diagnostics/client",
                headers=origin,
                json={"events": [{**event, "event_id": str(uuid4()), field: value}]},
            ).status_code
            == 422
        )
