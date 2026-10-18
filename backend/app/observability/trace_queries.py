"""Read-only, bounded views over the existing diagnostic event store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from .diagnostics_models import DiagnosticEvent as E
from .diagnostics_schemas import EventResponse

FAILURES = ("failure", "blocked", "timeout", "cancelled")
SUCCESS = ("success", "reused")
UNKNOWN_CAUSE = "The exact root cause has not yet been determined."


def latest_requests(since: datetime, until: datetime | None = None) -> Subquery:
    # Prefer canonical backend terminal events; otherwise preserve an observed start.
    rank = case(
        (
            and_(
                E.record_type == "event",
                E.platform == "backend",
                E.outcome.not_in(("started", "stage")),
            ),
            0,
        ),
        (and_(E.record_type == "span", E.platform == "backend"), 1),
        else_=2,
    )
    return (
        select(E)
        .where(
            E.trace_id.is_not(None),
            E.timestamp >= since,
            E.timestamp <= (until or datetime.now(UTC)),
        )
        .distinct(E.trace_id)
        .order_by(E.trace_id, rank, E.timestamp.desc(), E.id)
        .subquery()
    )


def trace_summary(
    row: E,
    *,
    stage_count: int = 0,
    dropped_count: int = 0,
    outcome: str | None = None,
    worker_count: int = 0,
) -> dict[str, Any]:
    terminal = (
        row.record_type == "event"
        and row.platform == "backend"
        and row.outcome not in {"stage", "started"}
    )
    summary = dict(
        trace_id=row.trace_id,
        request_id=row.request_id,
        operation_id=row.operation_id,
        user_id=row.user_id,
        operation=row.operation,
        component=row.component,
        platform=row.origin_platform or row.platform,
        started_at=row.started_at or row.timestamp,
        ended_at=row.ended_at if terminal else None,
        duration_ms=row.duration_ms if terminal else None,
        stage_count=stage_count,
        outcome=row.outcome if terminal else "unknown",
        failure_stage=row.stage if terminal and row.outcome in FAILURES else None,
        http_status=row.http_status,
        incomplete=not terminal or dropped_count > 0,
        dropped_count=dropped_count,
    )
    if outcome is not None:
        summary["outcome"] = outcome
    if worker_count:
        summary["incomplete"] = outcome == "unknown" or dropped_count > 0
    return summary


def latest_worker_outcomes() -> Subquery:
    """One latest completed worker attempt per durable resource, aggregated per trace."""
    span_rank = (
        func.row_number()
        .over(
            partition_by=(E.trace_id, E.resource_id, E.retry_count, E.clock_domain, E.span_id),
            order_by=(E.ended_at.desc().nulls_last(), E.timestamp.desc(), E.id.desc()),
        )
        .label("span_rank")
    )
    recorded = (
        select(
            E.trace_id.label("trace_id"),
            E.resource_id.label("resource_id"),
            E.retry_count.label("retry_count"),
            E.outcome.label("outcome"),
            E.ended_at.label("ended_at"),
            E.timestamp.label("timestamp"),
            span_rank,
        )
        .where(
            E.trace_id.is_not(None),
            E.resource_id.is_not(None),
            E.record_type == "span",
            E.platform == "worker",
            E.stage == "worker_execution",
        )
        .subquery()
    )
    attempt_rank = (
        func.row_number()
        .over(
            partition_by=(recorded.c.trace_id, recorded.c.resource_id),
            order_by=(recorded.c.retry_count.desc(), recorded.c.timestamp.desc()),
        )
        .label("attempt_rank")
    )
    latest_attempts = (
        select(
            recorded.c.trace_id,
            recorded.c.resource_id,
            recorded.c.outcome,
            recorded.c.ended_at,
            attempt_rank,
        )
        .where(recorded.c.span_rank == 1)
        .subquery()
    )
    resources = (
        select(
            latest_attempts.c.trace_id,
            latest_attempts.c.resource_id,
            latest_attempts.c.outcome,
            latest_attempts.c.ended_at,
        )
        .where(latest_attempts.c.attempt_rank == 1)
        .subquery()
    )
    failure_count = func.count().filter(
        resources.c.ended_at.is_not(None), resources.c.outcome.in_(FAILURES)
    )
    success_count = func.count().filter(
        resources.c.ended_at.is_not(None), resources.c.outcome.in_(SUCCESS)
    )
    resource_count = func.count()
    return (
        select(
            resources.c.trace_id.label("trace_id"),
            resource_count.label("resource_count"),
            func.max(resources.c.ended_at).label("worker_ended_at"),
            case(
                (failure_count > 0, "failure"),
                (success_count == resource_count, "success"),
                else_="unknown",
            ).label("worker_outcome"),
        )
        .group_by(resources.c.trace_id)
        .subquery()
    )


def overall_outcome(row: Any, worker: Any) -> Any:
    terminal = and_(
        row.record_type == "event",
        row.platform == "backend",
        row.outcome.not_in(("started", "stage")),
    )
    return case(
        (worker.c.worker_outcome == "failure", "failure"),
        (worker.c.worker_outcome == "success", "success"),
        (worker.c.resource_count.is_not(None), "unknown"),
        (terminal, row.outcome),
        else_="unknown",
    )


def reduced_worker_roots(spans: list[E]) -> list[E]:
    by_resource: dict[Any, list[E]] = {}
    for span in spans:
        if (
            span.platform == "worker"
            and span.stage == "worker_execution"
            and span.resource_id is not None
        ):
            by_resource.setdefault(span.resource_id, []).append(span)
    latest = []
    for attempts in by_resource.values():
        latest.append(
            max(
                attempts,
                key=lambda span: (
                    span.retry_count,
                    span.timestamp,
                    span.ended_at is not None,
                ),
            )
        )
    return latest


def worker_outcome(roots: list[E]) -> str:
    if not roots:
        return "unknown"
    if any(root.ended_at is not None and root.outcome in FAILURES for root in roots):
        return "failure"
    if all(root.ended_at is not None and root.outcome in SUCCESS for root in roots):
        return "success"
    return "unknown"


def explore(
    db: Session,
    *,
    limit: int,
    offset: int,
    since: datetime,
    until: datetime | None,
    sort: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    from sqlalchemy.orm import aliased

    base = latest_requests(since, until)
    row = aliased(E, base)
    workers = latest_worker_outcomes()
    outcome = overall_outcome(row, workers)
    conditions = []
    for name, value in filters.items():
        if value is None:
            continue
        if name == "platform":
            conditions.append(func.coalesce(row.origin_platform, row.platform) == value)
        elif name == "outcome":
            conditions.append(outcome == value)
        else:
            # Correlated filters allow users/components known only at an internal stage.
            matches = (
                select(E.id).where(E.trace_id == row.trace_id, getattr(E, name) == value).exists()
            )
            conditions.append(matches)
    ordering = (
        (row.duration_ms.desc().nulls_last(), row.timestamp.desc())
        if sort == "slowest"
        else (case((outcome.in_(FAILURES), 0), else_=1), row.timestamp.desc())
        if sort == "failed"
        else (row.timestamp.desc(),)
    )
    rows = list(
        db.execute(
            select(
                row,
                outcome.label("overall_outcome"),
                func.coalesce(workers.c.worker_outcome, "unknown").label("worker_outcome"),
                func.coalesce(workers.c.resource_count, 0).label("worker_count"),
            )
            .outerjoin(workers, workers.c.trace_id == row.trace_id)
            .where(*conditions)
            .order_by(*ordering, row.trace_id)
            .limit(limit + 1)
            .offset(offset)
        )
    )
    ids = [result[0].trace_id for result in rows[:limit]]
    counts = (
        {
            trace: (count, dropped or 0)
            for trace, count, dropped in db.execute(
                select(E.trace_id, func.count(func.distinct(E.span_id)), func.max(E.dropped_count))
                .where(E.trace_id.in_(ids))
                .group_by(E.trace_id)
            )
        }
        if ids
        else {}
    )
    return dict(
        items=[
            trace_summary(
                result[0],
                stage_count=counts.get(result[0].trace_id, (0, 0))[0],
                dropped_count=counts.get(result[0].trace_id, (0, 0))[1],
                outcome=result.overall_outcome,
                worker_count=result.worker_count,
            )
            for result in rows[:limit]
        ],
        limit=limit,
        offset=offset,
        has_more=len(rows) > limit,
    )


def trace_detail(db: Session, trace_id: str) -> dict[str, Any]:
    # Bound pathological or forged traces; the UI must display truncation.
    rows = list(
        db.scalars(select(E).where(E.trace_id == trace_id).order_by(E.timestamp, E.id).limit(2049))
    )
    if not rows:
        raise HTTPException(404, detail={"code": "TRACE_NOT_FOUND"})
    truncated = len(rows) > 2048
    rows = rows[:2048]
    terminal = [
        r
        for r in rows
        if r.record_type == "event"
        and r.platform == "backend"
        and r.outcome not in {"started", "stage"}
    ]
    representative = (
        terminal[-1] if terminal else next((r for r in rows if r.platform == "backend"), rows[0])
    )
    spans: dict[tuple[str | None, str], E] = {}
    for row in rows:
        if row.record_type == "span" and row.span_id:
            key = (row.clock_domain, row.span_id)
            previous = spans.get(key)
            # A delayed replay of a start must never overwrite an observed completion.
            if previous is None or row.ended_at is not None or previous.ended_at is None:
                spans[key] = row
    ordered = sorted(
        spans.values(),
        key=lambda r: (r.clock_domain or "", r.offset_ms, r.started_at or r.timestamp),
    )
    worker_roots = reduced_worker_roots(ordered)
    final_worker_outcome = worker_outcome(worker_roots)
    failed_attempts = {
        (root.resource_id, root.retry_count)
        for root in worker_roots
        if root.ended_at is not None and root.outcome in FAILURES
    }
    failures = [
        r
        for r in ordered
        if r.outcome in FAILURES
        and (r.platform != "worker" or (r.resource_id, r.retry_count) in failed_attempts)
    ]
    dropped = max(r.dropped_count for r in rows)
    summary = trace_summary(representative, stage_count=len(ordered), dropped_count=dropped)
    backend_roots = [
        r
        for r in ordered
        if r.platform == "backend"
        and r.stage
        in {
            "backend_response_completed",
            "backend_response_interrupted",
            "backend_request",
            "backend_response_prepared",
        }
    ]
    root = backend_roots[-1] if backend_roots else None
    summary["business_outcome"] = (
        representative.outcome
        if terminal
        and representative.error_code
        not in {"HTTP_REQUEST_COMPLETED", "HTTP_CLIENT_ERROR", "HTTP_SERVER_ERROR"}
        else "unknown"
    )
    summary["worker_outcome"] = final_worker_outcome
    summary["transport_outcome"] = root.outcome if root and root.ended_at else "unknown"
    if root and root.ended_at:
        summary["duration_ms"] = root.duration_ms
        summary["ended_at"] = root.ended_at
        summary["http_status"] = root.http_status or summary["http_status"]
        if root.outcome in FAILURES:
            summary["outcome"] = root.outcome

    if worker_roots:
        summary["outcome"] = final_worker_outcome
        summary["incomplete"] = summary["incomplete"] or final_worker_outcome == "unknown"
        if final_worker_outcome in {"success", "unknown"}:
            summary["failure_stage"] = None

    expected = max((r.expected_span_count for r in rows if r.platform == "backend"), default=0)
    retained_backend = sum(r.platform == "backend" for r in ordered)
    missing_backend = expected > retained_backend or (bool(terminal) and not backend_roots)
    backend_open = any(r.platform == "backend" and r.ended_at is None for r in ordered)
    summary["incomplete"] = summary["incomplete"] or backend_open or missing_backend or truncated
    failed: E | None
    worker_failures = [r for r in failures if r.platform == "worker"]
    failure_evidence = worker_failures if final_worker_outcome == "failure" else failures
    has_worker_failure = bool(worker_roots) and final_worker_outcome == "failure"
    consider_span_failures = not worker_roots or has_worker_failure
    if (
        failure_evidence
        and consider_span_failures
        and summary["outcome"] not in (*SUCCESS, "pending_review")
    ):
        # Deepest observed failure is evidence; no causal inference from elapsed time.
        parents = {r.parent_span_id for r in failure_evidence}
        failed = next(
            (r for r in failure_evidence if r.span_id not in parents), failure_evidence[-1]
        )
        summary["failure_stage"] = (
            representative.stage
            if terminal
            and representative.outcome in FAILURES
            and representative.stage not in {"request", "backend_request"}
            and not has_worker_failure
            else failed.stage
        )
    else:
        failed = representative if representative.outcome in FAILURES and not worker_roots else None
    confirmed = bool(
        failed and failed.exception_type and failed.source_location and failed.platform == "backend"
    )
    cause = (
        f"Observed {failed.exception_type} at {failed.source_location}. "
        if confirmed and failed is not None
        else ""
    ) + UNKNOWN_CAUSE
    persistence = "unknown"
    if representative.resource_id and representative.outcome in (*SUCCESS, "pending_review"):
        from app.nutrition.models import NutritionPlanBundle
        from app.workouts.models import WorkoutPlan

        model = (
            NutritionPlanBundle
            if representative.operation == "nutrition_generation"
            else WorkoutPlan
            if representative.operation == "workout_generation"
            else None
        )
        if model is not None and db.scalar(
            select(model.id).where(
                model.id == representative.resource_id, model.user_id == representative.user_id
            )
        ):
            persistence = "confirmed"
    recommendation = (
        "شواهد مرحله و لاگ‌های سرویس را با trace_id بررسی کنید؛ نبود رویداد نتیجه را تأیید نمی‌کند."
    )
    if failed and failed.category == "database_failure":
        recommendation = (
            "وضعیت اتصال، قفل‌ها و خطای پایگاه داده را در همان بازه و با شناسه ردیابی بررسی کنید."
        )
    description = (
        f"عملیات {representative.operation} از {summary['platform']}؛ "
        f"{len(ordered)} مرحله مشاهده شد. "
    )
    description += f"نتیجه ثبت‌شده: {summary['outcome']}. "
    description += "علت دقیق هنوز مشخص نشده است. "
    description += (
        "ذخیره نتیجه تأیید شد." if persistence == "confirmed" else "ذخیره نتیجه تأیید نشده است."
    )
    return dict(
        trace=summary,
        spans=[
            EventResponse.model_validate(r).model_dump(mode="json", by_alias=True) for r in ordered
        ],
        summary=dict(
            operation=representative.operation,
            platform=summary["platform"],
            business_outcome=summary["business_outcome"],
            transport_outcome=summary["transport_outcome"],
            worker_outcome=summary["worker_outcome"],
            outcome=summary["outcome"],
            observed_stages=[r.stage for r in ordered],
            succeeded_stages=[r.stage for r in ordered if r.outcome == "success"],
            failure_stage=summary["failure_stage"],
            cause=cause,
            confidence="unknown",
            persistence=persistence,
            recommendation=recommendation,
            description_fa=description,
        ),
        related_issue_ids=sorted({str(r.issue_id) for r in rows if r.issue_id}),
        truncated=truncated,
    )


def analytics(db: Session, hours: int) -> dict[str, Any]:
    base = latest_requests(datetime.now(UTC) - timedelta(hours=hours))
    workers = latest_worker_outcomes()
    observed = base.outerjoin(workers, workers.c.trace_id == base.c.trace_id)
    outcome = overall_outcome(base.c, workers)
    failed = outcome.in_(FAILURES)
    successful = outcome.in_(SUCCESS)
    total, success, failure, incomplete = db.execute(
        select(
            func.count(),
            func.count().filter(successful),
            func.count().filter(failed),
            func.count().filter(outcome == "unknown"),
        ).select_from(observed)
    ).one()
    stage_rows = (
        select(E)
        .where(E.record_type == "span", E.timestamp >= datetime.now(UTC) - timedelta(hours=hours))
        .distinct(E.trace_id, E.clock_domain, E.span_id)
        .order_by(
            E.trace_id,
            E.clock_domain,
            E.span_id,
            E.ended_at.desc().nulls_last(),
            E.timestamp.desc(),
        )
        .subquery()
    )
    stages = [
        dict(stage=stage, count=count, failure_count=failures, p50_ms=p50, p95_ms=p95)
        for stage, count, failures, p50, p95 in db.execute(
            select(
                stage_rows.c.stage,
                func.count(),
                func.count().filter(stage_rows.c.outcome.in_(FAILURES)),
                func.percentile_cont(0.5).within_group(stage_rows.c.duration_ms),
                func.percentile_cont(0.95).within_group(stage_rows.c.duration_ms),
            )
            .group_by(stage_rows.c.stage)
            .order_by(func.count().desc())
            .limit(50)
        )
    ]
    operations = [
        dict(operation=operation, count=count, failure_count=failures, affected_users=users)
        for operation, count, failures, users in db.execute(
            select(
                base.c.operation,
                func.count(),
                func.count().filter(failed),
                func.count(func.distinct(base.c.user_id)).filter(failed),
            )
            .select_from(observed)
            .group_by(base.c.operation)
            .order_by(func.count().filter(failed).desc())
            .limit(30)
        )
    ]
    platform = func.coalesce(base.c.origin_platform, base.c.platform)
    platforms = [
        dict(platform=name, count=count, failure_count=failures)
        for name, count, failures in db.execute(
            select(platform, func.count(), func.count().filter(failed))
            .select_from(observed)
            .group_by(platform)
        )
    ]
    bucket = func.date_trunc("hour" if hours <= 24 else "day", base.c.timestamp)
    trend = [
        dict(timestamp=stamp, count=count, failure_count=failures)
        for stamp, count, failures in db.execute(
            select(bucket, func.count(), func.count().filter(failed))
            .select_from(observed)
            .group_by(bucket)
            .order_by(bucket)
        )
    ]
    return dict(
        observed_requests=total,
        success_count=success,
        failure_count=failure,
        incomplete_count=incomplete,
        success_rate=success / total if total else None,
        stages=stages,
        operations=operations,
        platforms=platforms,
        trend=trend,
        limitations=(
            "فقط مشاهدات نگهداری‌شده؛ نمونه‌برداری، حذف صف و پایان نگهداری بر مخرج اثر دارند. "
            "ساعت کلاینت با سرور قابل مقایسه مستقیم نیست."
        ),
    )
