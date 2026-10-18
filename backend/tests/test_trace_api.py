from uuid import uuid4

from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event


def test_trace_endpoints_require_admin(client):
    assert client.get("/api/v1/admin/diagnostics/traces").status_code == 401
    assert client.get("/api/v1/admin/diagnostics/trace-analytics").status_code == 401


def test_trace_summary_keeps_transport_and_business_outcomes_separate(db):
    from app.observability.trace_queries import trace_detail

    trace_id = uuid4().hex
    common = dict(
        trace_id=trace_id,
        request_id="nutrition-failed",
        operation_id=str(uuid4()),
        operation="nutrition_generation",
        component="nutrition_engine",
        platform="backend",
        category="engine_validation",
        severity="error",
        error_code="PLAN_FAILED",
    )
    record_event(
        db, EventInput(**common, stage="meal_construction", outcome="failure", http_status=201)
    )
    detail = trace_detail(db, trace_id)
    assert detail["trace"]["outcome"] == "failure"
    assert detail["trace"]["http_status"] == 201
    assert detail["summary"]["persistence"] == "unknown"
    assert detail["summary"]["confidence"] == "unknown"
    assert "The exact root cause has not yet been determined." in detail["summary"]["cause"]


def test_span_retries_deduplicate_and_incomplete_is_unknown(db):
    from datetime import UTC, datetime

    from app.observability.trace_queries import trace_detail

    trace_id, span_id, event_id = uuid4().hex, uuid4().hex[:16], uuid4()
    event = EventInput(
        event_id=event_id,
        trace_id=trace_id,
        span_id=span_id,
        record_type="span",
        started_at=datetime.now(UTC),
        stage="backend_request",
        component="api",
        operation="login",
        platform="backend",
        category="unknown",
        severity="info",
        error_code="SPAN_STARTED",
        outcome="started",
    )
    record_event(db, event)
    record_event(db, event)
    detail = trace_detail(db, trace_id)
    assert len(detail["spans"]) == 1
    assert detail["trace"]["incomplete"] is True
    assert detail["trace"]["outcome"] == "unknown"


def test_admin_explorer_filters_analytics_and_client_timeout(client, db):
    from sqlalchemy import select

    from app.auth.models import User

    email = f"trace-admin-{uuid4()}@example.com"
    headers = {"Origin": "http://localhost:5173"}
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=headers,
            json={"email": email, "password": "long test password"},
        ).status_code
        == 201
    )
    assert client.get("/api/v1/admin/diagnostics/traces").status_code == 403
    user = db.scalar(select(User).where(User.email == email))
    user.is_admin = True
    db.commit()
    trace_id = uuid4().hex
    span_id = uuid4().hex[:16]
    event = dict(
        event_id=str(uuid4()),
        trace_id=trace_id,
        span_id=span_id,
        request_id="client-timeout-only",
        operation_id=trace_id,
        platform="android",
        component="NativeTransport",
        operation="nutrition",
        stage="transport_failed",
        error_code="CLIENT_REQUEST_OBSERVED",
        duration_ms=1200,
    )
    for _ in range(2):
        assert (
            client.post(
                "/api/v1/diagnostics/client", headers=headers, json={"events": [event]}
            ).status_code
            == 202
        )
    detail = client.get(f"/api/v1/admin/diagnostics/traces/{trace_id}")
    assert detail.status_code == 200
    value = detail.json()
    assert value["trace"]["outcome"] == "unknown"
    assert value["summary"]["persistence"] == "unknown"
    assert len(value["spans"]) == 1 and value["spans"][0]["clock_domain"] == "client"
    found = client.get(
        "/api/v1/admin/diagnostics/traces", params={"trace_id": trace_id, "limit": 1}
    )
    assert found.status_code == 200 and len(found.json()["items"]) == 1
    report = client.get("/api/v1/admin/diagnostics/trace-analytics")
    assert report.status_code == 200 and report.json()["observed_requests"] >= 1
    assert report.json()["success_count"] == 0
    assert report.json()["capture"]["process_local"] is True
    assert "password" not in detail.text and email not in detail.text

    from app.observability.diagnostics_models import DiagnosticIssue

    for kind, observed in (
        ("timeout", "timeout"),
        ("aborted", "cancelled"),
        ("network", "failure"),
    ):
        typed_trace = uuid4().hex
        typed = {
            **event,
            "event_id": str(uuid4()),
            "trace_id": typed_trace,
            "span_id": uuid4().hex[:16],
            "component": "WebTransport",
            "platform": "web",
            "transport_kind": kind,
        }
        for _ in range(2):
            assert (
                client.post(
                    "/api/v1/diagnostics/client", headers=headers, json={"events": [typed]}
                ).status_code
                == 202
            )
        typed_detail = client.get(f"/api/v1/admin/diagnostics/traces/{typed_trace}").json()
        assert typed_detail["trace"]["outcome"] == "unknown"
        assert typed_detail["spans"][0]["outcome"] == observed
        assert typed_detail["spans"][0]["error_code"] == f"CLIENT_TRANSPORT_{kind.upper()}"
        assert bool(typed_detail["related_issue_ids"]) is (kind != "aborted")
    issues = list(db.scalars(select(DiagnosticIssue)))
    assert sum(issue.count for issue in issues) == 2


def test_retained_terminal_without_spans_is_incomplete(db):
    from app.observability.trace_queries import trace_detail

    trace_id = uuid4().hex
    record_event(
        db,
        EventInput(
            trace_id=trace_id,
            operation="request",
            component="api",
            stage="request",
            platform="backend",
            category="unknown",
            severity="info",
            error_code="HTTP_REQUEST_COMPLETED",
            outcome="success",
            expected_span_count=4,
        ),
    )
    assert trace_detail(db, trace_id)["trace"]["incomplete"] is True


def test_recorded_success_and_failure_examples(client, db, test_settings):
    import json
    import os
    from pathlib import Path

    from fastapi import Request
    from fastapi.encoders import jsonable_encoder
    from fastapi.testclient import TestClient

    from app.observability.diagnostics_runtime import DiagnosticsRuntime, stage
    from app.observability.trace_queries import analytics, trace_detail

    rows = []
    client.app.state.diagnostics_runtime = DiagnosticsRuntime(
        test_settings, injected_sink=lambda event, user: rows.append((event, user))
    )
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:5173", "X-Fitician-Platform": "web"},
        json={"email": f"evidence-{uuid4()}@example.com", "password": "long test password"},
    )
    assert response.status_code == 201
    success_id = response.headers["traceparent"].split("-")[1]

    @client.app.get("/api/v1/trace-evidence/failure")
    def failed_operation(request: Request):
        with stage("business_execution"):
            with stage("internal_calculation"):
                raise ZeroDivisionError("private test details must stay private")

    failed_response = TestClient(client.app, raise_server_exceptions=False).get(
        "/api/v1/trace-evidence/failure", headers={"X-Fitician-Platform": "android"}
    )
    assert failed_response.status_code == 500
    failed_id = next(event.trace_id for event, user in reversed(rows) if event.outcome == "failure")
    for event, user in rows:
        record_event(db, event, user_id=user)
    success = trace_detail(db, success_id)
    failed = trace_detail(db, failed_id)
    assert success["trace"]["outcome"] == "success"
    assert failed["trace"]["outcome"] == "failure"
    assert failed["trace"]["failure_stage"] == "internal_calculation"
    assert "private test details" not in json.dumps(jsonable_encoder(failed))
    target = os.environ.get("TRACE_EVIDENCE_DIR")
    if target:
        path = Path(target)
        path.mkdir(parents=True, exist_ok=True)
        (path / "recorded-traces.json").write_text(
            json.dumps(
                jsonable_encoder(
                    {
                        "environment": "isolated local test database; not production",
                        "analytics": analytics(db, 24),
                        "success": success,
                        "failure": failed,
                    }
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
