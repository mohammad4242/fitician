from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

from fastapi import Request, Response

from app.observability import diagnostics_runtime as runtime_module
from app.observability.diagnostics_runtime import (
    DiagnosticsRuntime,
    RequestDiagnosticsContext,
    bind_request_context,
    diagnostics_middleware,
    emit,
    route_operation,
    safe_source_location,
    set_stage,
)
from app.observability.diagnostics_schemas import EventInput


def _event() -> EventInput:
    return EventInput(
        component="api",
        operation="profile_read",
        stage="request",
        platform="backend",
        category="unknown",
        severity="info",
        error_code="HTTP_REQUEST_COMPLETED",
        outcome="success",
    )


def test_runtime_queue_is_bounded_and_nonblocking(test_settings):
    settings = test_settings.model_copy(update={"app_env": "local"})
    runtime = DiagnosticsRuntime(settings)

    for _ in range(256):
        assert runtime.submit(_event())

    assert runtime.queued_count == 256
    assert runtime.submit(_event()) is False


def test_runtime_does_not_start_a_thread_in_test_environment(test_settings):
    runtime = DiagnosticsRuntime(test_settings)

    runtime.start()

    assert runtime._thread is None


def test_injected_sink_accepts_events_without_a_writer_thread(test_settings):
    received: list[EventInput] = []
    runtime = DiagnosticsRuntime(
        test_settings,
        injected_sink=lambda event, _user_id: received.append(event),
    )

    runtime.start()
    accepted = runtime.submit(_event())

    assert accepted is True
    assert runtime._thread is None
    assert received == [_event()]


def test_stage_and_terminal_outcome_are_noop_outside_a_request():
    assert set_stage("provider_call") is False
    assert (
        emit(
            category="provider_failure",
            severity="error",
            error_code="WORKOUT_GENERATION_FAILED",
            outcome="failure",
        )
        is False
    )


def test_terminal_workflow_result_replaces_http_success_event(test_settings):
    received: list[EventInput] = []
    user_id = uuid4()
    runtime = DiagnosticsRuntime(
        test_settings,
        injected_sink=lambda event, _user_id: received.append(event),
    )
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/workouts/generate",
        "raw_path": b"/api/v1/workouts/generate",
        "query_string": b"secret=query-is-not-recorded",
        "headers": [],
        "scheme": "https",
        "server": ("example.test", 443),
        "client": ("127.0.0.1", 1234),
        "state": {"request_id": "request-safe-1", "diagnostics_user_id": user_id},
        "route": SimpleNamespace(path="/api/v1/workouts/generate"),
    }
    request = Request(scope)

    async def call_next(_request: Request) -> Response:
        set_stage("provider_call", component="workout_provider")
        emit(
            category="provider_failure",
            severity="error",
            error_code="WORKOUT_GENERATION_FAILED",
            outcome="failure",
            operation="workout_generation",
        )
        return Response(status_code=200)

    response = asyncio.run(diagnostics_middleware(request, call_next, runtime))

    assert response.status_code == 200
    received = [
        row
        for row in received
        if row.record_type == "event" and row.outcome not in {"stage", "started"}
    ]
    assert len(received) == 1
    assert received[0].operation == "workout_generation"
    assert received[0].stage == "provider_call"
    assert received[0].outcome == "failure"
    assert received[0].request_id == "request-safe-1"
    assert received[0].user_id == user_id if hasattr(received[0], "user_id") else True


def test_route_operations_use_templates_without_concrete_identifiers():
    assert route_operation("/api/v1/workouts/{plan_id}/versions/{version_id}", "GET") == (
        "get_api_v1_workouts_id_versions_id"
    )
    assert route_operation("/api/v1/nutrition/plans", "POST") == "nutrition_generation"


def test_source_location_is_repository_basename_only(monkeypatch):
    monkeypatch.setattr(
        runtime_module.traceback,
        "extract_tb",
        lambda _traceback: [
            SimpleNamespace(filename="/srv/fitician/backend/app/workouts/router.py", lineno=42)
        ],
    )
    error = RuntimeError("private message must not appear")

    assert safe_source_location(error) is None
    try:
        raise error
    except RuntimeError:
        assert safe_source_location(error) == "router.py:42"


def test_injected_context_can_be_bound_and_reset(test_settings):
    received: list[EventInput] = []
    runtime = DiagnosticsRuntime(
        test_settings,
        injected_sink=lambda event, _user_id: received.append(event),
    )
    context = RequestDiagnosticsContext(
        submit=runtime.submit,
        request_id="request-123",
        operation_id=str(uuid4()),
        operation="nutrition_generation",
    )

    with bind_request_context(context):
        assert set_stage("engine_validation", component="nutrition_engine")
        assert emit(
            category="engine_validation",
            severity="warning",
            error_code="GENERATION_REVIEW_REQUIRED",
            outcome="pending_review",
        )
        assert context.stage_name == "engine_validation"
        assert context.outcome == "pending_review"

    assert (
        emit(
            category="unknown",
            severity="info",
            error_code="HTTP_REQUEST_COMPLETED",
            outcome="success",
        )
        is False
    )
    received = [row for row in received if row.record_type == "event"]
    assert len(received) == 1 and received[0].outcome == "stage"


def test_actual_workout_route_is_classified():
    assert route_operation("/api/v1/workout-plans/generate", "POST") == "workout_generation"


def test_stage_records_a_bounded_correlated_timeline(test_settings):
    received = []
    context = RequestDiagnosticsContext(
        submit=lambda event, user: received.append(event) or True,
        request_id="request-1",
        operation_id=str(uuid4()),
        operation="workout_generation",
    )
    with bind_request_context(context):
        set_stage("candidate_selection", component="workout_engine")
        set_stage("constraint_validation")
    received = [row for row in received if row.record_type == "event"]
    assert [row.stage for row in received] == ["candidate_selection", "constraint_validation"]
    assert all(row.outcome == "stage" and row.request_id == "request-1" for row in received)


def test_unhandled_api_exception_is_recorded_without_exception_message(client, test_settings):
    from fastapi.testclient import TestClient

    received = []
    client.app.state.diagnostics_runtime = DiagnosticsRuntime(
        test_settings, injected_sink=lambda event, user: received.append(event)
    )

    @client.app.get("/api/v1/diagnostic-failure-probe")
    def broken_operation():
        raise ValueError("private-input-must-never-be-recorded")

    response = TestClient(client.app, raise_server_exceptions=False).get(
        "/api/v1/diagnostic-failure-probe", headers={"X-Correlation-ID": "safe-error-correlation"}
    )
    assert response.status_code == 500
    received = [row for row in received if row.record_type == "event" and row.outcome == "failure"]
    assert len(received) == 1
    assert received[0].exception_type == "ValueError"
    assert received[0].error_code == "UNHANDLED_EXCEPTION"
    assert "private-input" not in received[0].model_dump_json()
    assert received[0].request_id == "safe-error-correlation"


def test_lowercase_provider_codes_keep_their_precise_failure_classification():
    from app.observability.diagnostics_runtime import category_for_error, safe_error_code

    assert safe_error_code("agent_network_unavailable") == "agent_network_unavailable"
    assert category_for_error("agent_network_unavailable", 503) == "infrastructure_failure"
    assert category_for_error("provider_timeout", 502) == "interrupted"
    assert category_for_error("COACH_REVIEW_QUOTA_EXCEEDED", 429) == "quota_limit"


def test_maintenance_failure_does_not_roll_back_the_recorded_event(test_settings, monkeypatch):
    from contextlib import contextmanager

    from app.observability import diagnostics_jobs

    commits = []

    class Database:
        def commit(self):
            commits.append("commit")

    @contextmanager
    def session():
        yield Database()

    monkeypatch.setattr(runtime_module, "record_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(diagnostics_jobs, "reconcile_job_failures", lambda *args: 0)
    monkeypatch.setattr(runtime_module, "detect_abandoned_attempts", lambda *args: 0)

    def failed_cleanup(*args, **kwargs):
        raise RuntimeError("maintenance unavailable")

    monkeypatch.setattr(runtime_module, "cleanup_retention", failed_cleanup)
    runtime = DiagnosticsRuntime(
        test_settings.model_copy(update={"app_env": "local"}), session_factory=session
    )
    runtime.submit(_event())
    runtime._stop.set()
    runtime._run()
    assert commits == ["commit"]
