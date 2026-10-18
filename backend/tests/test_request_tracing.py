from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi import Request, Response

from app.observability.diagnostics_runtime import (
    DiagnosticsRuntime,
    RequestDiagnosticsContext,
    bind_request_context,
    diagnostics_middleware,
    emit,
    stage,
)


def test_nested_spans_have_timing_and_failure_without_private_message():
    rows = []
    context = RequestDiagnosticsContext(
        submit=lambda event, user: rows.append(event) or True,
        request_id="trace-request",
        operation_id=str(uuid4()),
        operation="nutrition_generation",
    )
    with bind_request_context(context):
        with stage("meal_construction", component="nutrition_engine"):
            with pytest.raises(ValueError), stage("candidate_construction"):
                raise ValueError("private-medical-input")
    spans = [r for r in rows if getattr(r, "record_type", None) == "span"]
    completed = [r for r in spans if r.outcome != "started"]
    assert len(completed) == 2
    child = next(r for r in completed if r.stage == "candidate_construction")
    parent = next(r for r in completed if r.stage == "meal_construction")
    assert child.parent_span_id == parent.span_id
    assert child.outcome == "failure"
    assert child.duration_ms >= 0 and child.ended_at >= child.started_at
    assert child.trace_id == parent.trace_id
    assert "private-medical-input" not in child.model_dump_json()


def test_request_preserves_w3c_context_and_business_failure(test_settings):
    rows = []
    runtime = DiagnosticsRuntime(
        test_settings, injected_sink=lambda event, user: rows.append(event)
    )
    trace_id = "1234567890abcdef1234567890abcdef"
    parent = "1234567890abcdef"
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/nutrition/plans",
            "query_string": b"secret=never",
            "headers": [(b"traceparent", f"00-{trace_id}-{parent}-01".encode())],
            "state": {"request_id": "business-failed"},
        }
    )

    async def execute(_request):
        with stage("meal_construction"):
            emit(
                category="engine_validation",
                severity="error",
                error_code="PLAN_FAILED",
                outcome="failure",
            )
        return Response(status_code=201)

    response = asyncio.run(diagnostics_middleware(request, execute, runtime))
    assert response.headers["traceparent"].split("-")[1] == trace_id
    terminal = [r for r in rows if r.record_type == "event" and r.outcome == "failure"]
    assert len(terminal) == 1 and terminal[0].http_status == 201
    assert terminal[0].trace_id == trace_id
    roots = [r for r in rows if r.record_type == "span" and r.parent_span_id == parent]
    assert roots


def test_trace_ids_reject_zero_and_invalid_context():
    from app.observability.tracing import parse_traceparent

    assert parse_traceparent("00-" + "0" * 32 + "-1234567890abcdef-01") is None
    assert parse_traceparent("secret") is None
    assert parse_traceparent("00-1234567890abcdef1234567890abcdef-1234567890abcdef-01") is not None


def test_database_failure_has_correlated_sanitized_span():
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    from app.observability.dependency_tracing import install_database_tracing

    install_database_tracing()
    rows = []
    context = RequestDiagnosticsContext(
        submit=lambda event, user: rows.append(event) or True,
        request_id="db-error",
        operation_id="db-operation",
        operation="profile",
    )
    engine = create_engine("sqlite://")
    with bind_request_context(context), engine.connect() as connection:
        with pytest.raises(SQLAlchemyError):
            connection.execute(text("select private_medical_column from missing_private_table"))
    failed = [row for row in rows if row.outcome == "failure"]
    assert failed and failed[0].trace_id == context.trace_id
    assert failed[0].component == "database" and failed[0].category == "database_failure"
    assert "private_medical" not in failed[0].model_dump_json()
    engine.dispose()


def test_sampling_retains_failed_trace_and_bounded_drop_evidence(test_settings):
    rows = []
    runtime = DiagnosticsRuntime(
        test_settings.model_copy(update={"diagnostics_success_sample_rate": 0}),
        injected_sink=lambda event, user: rows.append(event),
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/nutrition/plans",
            "query_string": b"",
            "headers": [],
            "state": {"request_id": "sampled-failure"},
        }
    )

    async def execute(_request):
        for _ in range(100):
            with stage("candidate"):
                pass
        emit(
            category="engine_validation",
            severity="error",
            error_code="PLAN_FAILED",
            outcome="failure",
        )
        return Response(status_code=201)

    asyncio.run(diagnostics_middleware(request, execute, runtime))
    assert any(row.outcome == "failure" and row.record_type == "event" for row in rows)
    assert any(row.dropped_count > 0 for row in rows)
    assert len([row for row in rows if row.record_type == "span"]) <= 194


def test_worker_resumes_durable_context_and_retry_count(test_settings):
    from types import SimpleNamespace

    from app.observability.job_tracing import job_trace

    rows = []
    runtime = DiagnosticsRuntime(
        test_settings, injected_sink=lambda event, user: rows.append(event)
    )
    job = SimpleNamespace(
        trace_id=uuid4().hex,
        trace_parent_span_id=uuid4().hex[:16],
        trace_operation_id="operation-worker",
        correlation_id="request-worker",
        status="failed",
        attempt_count=2,
    )
    with job_trace(job, component="body_analysis", runtime=runtime):
        with stage("agent_service_call", component="agent_service"):
            pass
    failed = [row for row in rows if row.outcome == "failure"]
    assert failed[0].trace_id == job.trace_id
    assert failed[0].parent_span_id == job.trace_parent_span_id
    assert failed[0].retry_count == 2 and failed[0].platform == "worker"


def test_completion_waits_for_last_body_and_records_interruption(test_settings):
    from app.observability.tracing import DiagnosticsCompletionMiddleware

    rows = []
    runtime = DiagnosticsRuntime(
        test_settings, injected_sink=lambda event, user: rows.append(event)
    )
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/stream",
        "query_string": b"",
        "headers": [],
        "state": {},
    }

    async def app(scope, receive, send):
        async def call_next(request):
            return Response(status_code=200)

        await diagnostics_middleware(Request(scope), call_next, runtime)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"part", "more_body": True})
        raise ConnectionError("private body stream failed")

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        pass

    with pytest.raises(ConnectionError):
        asyncio.run(DiagnosticsCompletionMiddleware(app)(scope, receive, send))
    roots = [
        row
        for row in rows
        if row.span_id == scope["state"]["diagnostics_root_span"].span_id
        and row.record_type == "span"
    ]
    assert roots[-1].outcome == "failure"
    assert roots[-1].stage == "backend_response_interrupted"
    assert "private body" not in roots[-1].model_dump_json()


def test_actual_registration_has_observed_common_stages(client, test_settings):
    rows = []
    client.app.state.diagnostics_runtime = DiagnosticsRuntime(
        test_settings, injected_sink=lambda event, user: rows.append(event)
    )
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:5173", "X-Fitician-Platform": "web"},
        json={"email": f"trace-{uuid4()}@example.com", "password": "long test password"},
    )
    assert response.status_code == 201
    spans = [row for row in rows if row.record_type == "span" and row.ended_at]
    names = {row.stage for row in spans}
    assert {
        "validation_and_dependencies",
        "business_logic",
        "register_user",
        "response_preparation",
        "backend_response_completed",
    } <= names
    assert all(row.outcome == "success" for row in spans)
    assert len({row.trace_id for row in rows}) == 1
    assert all(row.origin_platform == "web" for row in spans)
    assert all(row.duration_ms is not None for row in spans)


def test_invalid_request_records_failed_validation_and_never_business_execution(
    client, test_settings
):
    rows = []
    client.app.state.diagnostics_runtime = DiagnosticsRuntime(
        test_settings, injected_sink=lambda event, user: rows.append(event)
    )
    response = client.post(
        "/api/v1/auth/register", headers={"Origin": "http://localhost:5173"}, json={}
    )
    assert response.status_code == 422
    terminal = next(row for row in rows if row.record_type == "event" and row.outcome == "failure")
    assert terminal.stage == "validation_and_dependencies"
    assert not any(row.stage == "business_logic" for row in rows)


def test_promoted_trace_reports_buffer_delivery_loss(test_settings):
    rows = []

    class RejectSpans(DiagnosticsRuntime):
        def submit(self, event, user_id=None):
            if event.record_type == "span":
                return False
            rows.append(event)
            return True

    runtime = RejectSpans(
        test_settings.model_copy(update={"app_env": "local", "diagnostics_success_sample_rate": 0})
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/nutrition/plans",
            "query_string": b"",
            "headers": [],
            "state": {},
        }
    )

    async def execute(request):
        with stage("failed_construction"):
            pass
        emit(
            category="engine_validation",
            severity="error",
            error_code="PLAN_FAILED",
            outcome="failure",
        )
        return Response(status_code=201)

    asyncio.run(diagnostics_middleware(request, execute, runtime))
    assert next(row for row in rows if row.outcome == "failure").dropped_count >= 3


def test_late_persisted_business_failure_updates_observed_stage_without_extending_duration():
    from app.observability.diagnostics_runtime import set_stage

    rows = []
    context = RequestDiagnosticsContext(
        submit=lambda event, user: rows.append(event) or True,
        request_id="late-domain-failure",
        operation_id="nutrition-operation",
        operation="nutrition_generation",
    )
    with bind_request_context(context):
        set_stage("meal_construction", component="nutrition_engine")
        set_stage("transaction_commit")
        original = next(row for row in rows if row.stage == "meal_construction" and row.ended_at)
        set_stage("response_serialization")
        emit(
            category="engine_validation",
            severity="error",
            error_code="NUTRITION_PLAN_FAILED",
            outcome="failure",
            stage_name="meal_construction",
        )
    corrected = [row for row in rows if row.stage == "meal_construction" and row.ended_at][-1]
    assert corrected.outcome == "failure"
    assert corrected.ended_at == original.ended_at and corrected.duration_ms == original.duration_ms
    assert corrected.span_id == original.span_id


def test_dependency_saturation_reserves_explicit_workflow_stages():
    from app.observability.diagnostics_runtime import set_stage
    from app.observability.tracing import start_span

    rows = []
    context = RequestDiagnosticsContext(
        submit=lambda event, user: rows.append(event) or True,
        request_id="bounded-dependencies",
        operation_id="bounded-operation",
        operation="nutrition_generation",
    )
    with bind_request_context(context):
        for _ in range(110):
            span = start_span("database_execute", "database")
            if span:
                span.finish()
        set_stage("transaction_commit")
        set_stage("response_serialization")
        context.active_stage.finish()
    assert context.dependency_span_count == 32
    assert context.trace_dropped == 78
    assert any(row.stage == "response_serialization" and row.outcome == "success" for row in rows)
