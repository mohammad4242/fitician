from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event
from app.observability.trace_queries import analytics, explore, trace_detail


def _record(
    db,
    *,
    trace_id: str,
    stage: str,
    platform: str,
    outcome: str,
    record_type: str = "event",
    at: datetime | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    resource_id=None,
    retry_count: int = 0,
    error_code: str = "HTTP_REQUEST_COMPLETED",
    http_status: int | None = None,
    ended: bool = True,
    clock_domain: str | None = None,
    source_location: str | None = None,
) -> None:
    started_at = at or datetime.now(UTC)
    record_event(
        db,
        EventInput(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            record_type=record_type,
            started_at=started_at if record_type == "span" else None,
            ended_at=started_at + timedelta(milliseconds=20)
            if record_type == "span" and ended
            else None,
            offset_ms=0,
            clock_domain=clock_domain,
            request_id=f"request-{trace_id[:8]}",
            operation_id=f"operation-{trace_id[:8]}",
            component="body_analysis" if platform == "worker" else "api",
            operation="body_analysis",
            stage=stage,
            platform=platform,
            category="application_bug" if outcome == "failure" else "unknown",
            severity="error" if outcome == "failure" else "info",
            error_code=error_code,
            source_location=source_location,
            resource_id=resource_id,
            outcome=outcome,
            duration_ms=20 if record_type == "span" and ended else None,
            retry_count=retry_count,
            http_status=http_status,
        ),
    )


def _backend_accepted(db, trace_id: str, at: datetime) -> None:
    _record(
        db,
        trace_id=trace_id,
        stage="request_completed",
        platform="backend",
        outcome="success",
        at=at,
        error_code="HTTP_REQUEST_COMPLETED",
        http_status=202,
    )
    _record(
        db,
        trace_id=trace_id,
        stage="backend_response_completed",
        platform="backend",
        outcome="success",
        record_type="span",
        at=at,
        span_id=uuid4().hex[:16],
        http_status=202,
        clock_domain="backend",
    )


def _worker_root(
    db,
    *,
    trace_id: str,
    resource_id,
    attempt: int,
    outcome: str,
    at: datetime,
    ended=True,
):
    root_id = uuid4().hex[:16]
    _record(
        db,
        trace_id=trace_id,
        stage="worker_execution",
        platform="worker",
        outcome=outcome,
        record_type="span",
        at=at,
        span_id=root_id,
        resource_id=resource_id,
        retry_count=attempt,
        error_code="SPAN_FAILED" if outcome == "failure" else "SPAN_COMPLETED",
        ended=ended,
        clock_domain="worker:body_analysis",
    )
    return root_id


def _analytics(db):
    return analytics(db, 24)


def test_worker_failure_overrides_accepted_http_success_but_preserves_transport(db):
    trace_id, resource_id = uuid4().hex, uuid4()
    now = datetime.now(UTC)
    _backend_accepted(db, trace_id, now)
    root_id = _worker_root(
        db, trace_id=trace_id, resource_id=resource_id, attempt=1, outcome="failure", at=now
    )
    _record(
        db,
        trace_id=trace_id,
        stage="provider_call",
        platform="worker",
        outcome="failure",
        record_type="span",
        at=now + timedelta(milliseconds=1),
        span_id=uuid4().hex[:16],
        parent_span_id=root_id,
        resource_id=resource_id,
        retry_count=1,
        error_code="SPAN_FAILED",
        source_location="provider.py:42",
        clock_domain="worker:body_analysis",
    )

    detail = trace_detail(db, trace_id)
    assert detail["trace"]["outcome"] == "failure"
    assert detail["summary"]["worker_outcome"] == "failure"
    assert detail["summary"]["transport_outcome"] == "success"
    assert detail["summary"]["business_outcome"] == "unknown"
    assert detail["summary"]["failure_stage"] == "provider_call"
    report = _analytics(db)
    assert report["observed_requests"] == 1
    assert report["failure_count"] == 1
    assert report["success_count"] == 0
    assert report["incomplete_count"] == 0


def test_latest_successful_retry_replaces_earlier_worker_failure(db):
    trace_id, resource_id = uuid4().hex, uuid4()
    now = datetime.now(UTC)
    _backend_accepted(db, trace_id, now)
    _worker_root(
        db, trace_id=trace_id, resource_id=resource_id, attempt=1, outcome="failure", at=now
    )
    _worker_root(
        db,
        trace_id=trace_id,
        resource_id=resource_id,
        attempt=2,
        outcome="success",
        at=now + timedelta(seconds=1),
    )

    detail = trace_detail(db, trace_id)
    assert detail["trace"]["outcome"] == "success"
    assert detail["summary"]["worker_outcome"] == "success"
    assert detail["summary"]["transport_outcome"] == "success"
    assert detail["summary"]["failure_stage"] is None
    report = _analytics(db)
    assert report["observed_requests"] == 1
    assert report["success_count"] == 1
    assert report["failure_count"] == 0


def test_scheduled_retry_keeps_latest_worker_and_overall_outcomes_unknown(db):
    trace_id, resource_id = uuid4().hex, uuid4()
    now = datetime.now(UTC)
    _backend_accepted(db, trace_id, now)
    _worker_root(
        db, trace_id=trace_id, resource_id=resource_id, attempt=1, outcome="failure", at=now
    )
    _worker_root(
        db,
        trace_id=trace_id,
        resource_id=resource_id,
        attempt=2,
        outcome="started",
        at=now + timedelta(seconds=1),
        ended=False,
    )

    detail = trace_detail(db, trace_id)
    assert detail["trace"]["outcome"] == "unknown"
    assert detail["trace"]["incomplete"] is True
    assert detail["summary"]["worker_outcome"] == "unknown"
    assert detail["summary"]["transport_outcome"] == "success"
    assert detail["summary"]["failure_stage"] is None
    report = _analytics(db)
    assert report["observed_requests"] == 1
    assert report["success_count"] == 0
    assert report["failure_count"] == 0
    assert report["incomplete_count"] == 1


def test_unknown_filter_matches_span_representative_whose_displayed_outcome_is_unknown(db):
    trace_id = uuid4().hex
    now = datetime.now(UTC)
    _record(
        db,
        trace_id=trace_id,
        stage="backend_request",
        platform="backend",
        outcome="started",
        record_type="span",
        at=now,
        span_id=uuid4().hex[:16],
        ended=False,
        clock_domain="backend",
    )
    _record(
        db,
        trace_id=trace_id,
        stage="database_execute",
        platform="backend",
        outcome="success",
        record_type="span",
        at=now + timedelta(milliseconds=5),
        span_id=uuid4().hex[:16],
        clock_domain="backend",
    )

    page = explore(
        db,
        limit=20,
        offset=0,
        since=now - timedelta(minutes=1),
        until=now + timedelta(minutes=1),
        sort="newest",
        filters={"outcome": "unknown"},
    )
    assert [item["trace_id"] for item in page["items"]] == [trace_id]
    assert page["items"][0]["outcome"] == "unknown"
