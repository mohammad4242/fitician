from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.routing import APIRoute
from sqlalchemy import case, func, select, text
from sqlalchemy.sql.elements import ColumnElement
from starlette.concurrency import run_in_threadpool
from starlette.types import Message

from app.admin.dependencies import AdminUser, require_admin
from app.auth.dependencies import (
    AppSettings,
    CurrentAuthentication,
    DatabaseSession,
    get_current_user,
    require_authenticated_mutation,
)
from app.auth.models import User
from app.rate_limits.dependency import (
    DistributedRateLimitUnavailable,
    enforce_distributed_rate_limit,
    rate_limit_http_exception,
)
from app.rate_limits.service import DistributedRateLimitExceeded

from .diagnostics_models import (
    DiagnosticAlert,
    DiagnosticEvent,
    DiagnosticIssue,
    DiagnosticStatusHistory,
)
from .diagnostics_schemas import (
    AlertResponse,
    ClientBatch,
    DiagnosticHours,
    EventInput,
    EventResponse,
    GenerationMetricsResponse,
    InfrastructureResponse,
    IssueDetailResponse,
    IssueResponse,
    IssueStatusUpdate,
    OverviewResponse,
    StatusHistoryResponse,
)
from .diagnostics_service import (
    abandoned_attempts,
    change_status,
    cleanup_retention,
    quota_integrity,
    record_event,
)

router = APIRouter(
    prefix="/api/v1/admin/diagnostics",
    tags=["admin-diagnostics"],
    dependencies=[Depends(require_admin)],
)


class BoundedTelemetryRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def handle(request: Request) -> Response:
            total = 0

            async def receive() -> Message:
                nonlocal total
                message = await request.receive()
                total += len(message.get("body", b""))
                if total > 16_384:
                    raise HTTPException(413, detail={"code": "TELEMETRY_BATCH_TOO_LARGE"})
                return message

            return await original(Request(request.scope, receive=receive))

        return handle


client_router = APIRouter(
    prefix="/api/v1/diagnostics", tags=["diagnostics"], route_class=BoundedTelemetryRoute
)


@client_router.post("/client", status_code=202)
async def ingest_client_events(
    payload: ClientBatch,
    request: Request,
    db: DatabaseSession,
    user: Annotated[User, Depends(get_current_user)],
    settings: AppSettings,
    _authentication: CurrentAuthentication,
    _mutation: Annotated[None, Depends(require_authenticated_mutation)],
) -> dict[str, int]:
    if not settings.diagnostics_enabled:
        return {"accepted": 0}
    try:
        await enforce_distributed_rate_limit(
            request,
            db,
            settings,
            namespace="application",
            operation="diagnostics_client",
            limit=30,
            window_seconds=60,
            user_id=user.id,
        )
    except (DistributedRateLimitExceeded, DistributedRateLimitUnavailable) as error:
        raise rate_limit_http_exception(error) from None

    def persist_batch() -> None:
        db.execute(text("SET LOCAL statement_timeout = '2000'"))
        db.execute(text("SET LOCAL lock_timeout = '100ms'"))
        for event in payload.events:
            category = {
                "API_REQUEST_FAILED": "api_failure",
                "CLIENT_RUNTIME_ERROR": "application_bug",
                "CLIENT_UNHANDLED_REJECTION": "application_bug",
                "CLIENT_RENDER_ERROR": "client_runtime",
            }[event.error_code]
            severity = "error"
            if (
                event.error_code == "API_REQUEST_FAILED"
                and event.http_status is not None
                and event.http_status < 500
            ):
                category = (
                    "auth_failure"
                    if event.http_status in {401, 403}
                    else "quota_limit"
                    if event.http_status == 429
                    else "invalid_input"
                    if event.http_status in {400, 422}
                    else "business_rejection"
                )
                severity = "warning"
            record_event(
                db,
                EventInput(
                    **event.model_dump(),
                    category=category,
                    severity=severity,
                    outcome="failure",
                ),
                user_id=user.id,
                trusted=False,
            )
        cleanup_retention(db, limit=100)
        db.commit()

    await run_in_threadpool(persist_batch)
    return {"accepted": len(payload.events)}


def _filters(
    *,
    platform: str | None = None,
    component: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    status: str | None = None,
    error_code: str | None = None,
    user_id: UUID | None = None,
    request_id: str | None = None,
    version: str | None = None,
    q: str | None = None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    for column, value in (
        (DiagnosticIssue.component, component),
        (DiagnosticIssue.severity, severity),
        (DiagnosticIssue.category, category),
        (DiagnosticIssue.status, status),
        (DiagnosticIssue.error_code, error_code),
    ):
        if value is not None:
            conditions.append(column == value)
    if user_id is not None or request_id is not None or version is not None or platform is not None:
        event_conditions = []
        if platform is not None:
            event_conditions.append(DiagnosticEvent.platform == platform)
        if user_id is not None:
            event_conditions.append(DiagnosticEvent.user_id == user_id)
        if request_id is not None:
            event_conditions.append(DiagnosticEvent.request_id == request_id)
        if version is not None:
            event_conditions.append(DiagnosticEvent.version == version)
        conditions.append(
            DiagnosticIssue.id.in_(select(DiagnosticEvent.issue_id).where(*event_conditions))
        )
    if q is not None:
        conditions.append(DiagnosticIssue.error_code.ilike(f"%{q}%"))
    return conditions


@router.get("/overview", response_model=OverviewResponse)
def overview(
    db: DatabaseSession, hours: DiagnosticHours = DiagnosticHours.DAY
) -> dict[str, object]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    base = DiagnosticEvent.timestamp >= since
    terminal = DiagnosticEvent.outcome.not_in(("started", "stage"))

    def count(*conditions: ColumnElement[bool]) -> int:
        return (
            db.scalar(select(func.count()).select_from(DiagnosticEvent).where(base, *conditions))
            or 0
        )

    successes = count(
        terminal,
        DiagnosticEvent.platform == "backend",
        DiagnosticEvent.http_status.between(200, 399),
    )
    failures = count(
        terminal, DiagnosticEvent.platform == "backend", DiagnosticEvent.http_status >= 400
    )
    server_errors = count(
        terminal, DiagnosticEvent.platform == "backend", DiagnosticEvent.http_status >= 500
    )
    bucket = func.date_trunc("hour" if hours <= 24 else "day", DiagnosticEvent.timestamp)
    trends = db.execute(
        select(bucket, func.count()).where(base, terminal).group_by(bucket).order_by(bucket)
    ).all()
    platforms = db.execute(
        select(DiagnosticEvent.platform, func.count())
        .where(base, terminal)
        .group_by(DiagnosticEvent.platform)
    ).all()
    return {
        "hours": hours,
        "event_count": count(),
        "issue_count": db.scalar(
            select(func.count())
            .select_from(DiagnosticIssue)
            .where(DiagnosticIssue.last_seen >= since)
        )
        or 0,
        "failure_count": count(
            terminal, DiagnosticEvent.outcome.in_(("failure", "timeout", "cancelled"))
        ),
        "critical_count": count(terminal, DiagnosticEvent.severity == "critical"),
        "new_issue_count": db.scalar(
            select(func.count())
            .select_from(DiagnosticIssue)
            .where(DiagnosticIssue.first_seen >= since)
        )
        or 0,
        "affected_users": db.scalar(
            select(func.count(func.distinct(DiagnosticEvent.user_id))).where(
                base, DiagnosticEvent.issue_id.is_not(None)
            )
        )
        or 0,
        "error_rate": server_errors / (successes + failures) if successes + failures else None,
        "http_response_count": {"success": successes, "failure": failures},
        "infrastructure": {"status": "unknown", "last_seen": None, "outcome": None},
        "trend": [{"timestamp": stamp, "count": total} for stamp, total in trends],
        "platforms": [{"platform": platform, "count": total} for platform, total in platforms],
    }


@router.get("/issues", response_model=list[IssueResponse])
def list_issues(
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    platform: Annotated[str | None, Query(max_length=32)] = None,
    component: Annotated[str | None, Query(max_length=80)] = None,
    severity: Annotated[str | None, Query(max_length=16)] = None,
    category: Annotated[str | None, Query(max_length=40)] = None,
    status: Annotated[str | None, Query(max_length=20)] = None,
    error_code: Annotated[str | None, Query(max_length=64)] = None,
    user_id: UUID | None = None,
    request_id: Annotated[str | None, Query(max_length=128)] = None,
    version: Annotated[str | None, Query(max_length=64)] = None,
    q: Annotated[str | None, Query(max_length=64)] = None,
    sort: Annotated[str, Query(pattern="^(last_seen|first_seen|count|severity)$")] = "last_seen",
    hours: DiagnosticHours = DiagnosticHours.DAY,
) -> list[DiagnosticIssue]:
    ordering = (
        case(
            (DiagnosticIssue.severity == "critical", 4),
            (DiagnosticIssue.severity == "error", 3),
            (DiagnosticIssue.severity == "warning", 2),
            else_=1,
        ).desc()
        if sort == "severity"
        else getattr(DiagnosticIssue, sort).desc()
    )
    statement = (
        select(DiagnosticIssue)
        .where(
            DiagnosticIssue.last_seen >= datetime.now(UTC) - timedelta(hours=hours),
            *_filters(
                platform=platform,
                component=component,
                severity=severity,
                category=category,
                status=status,
                error_code=error_code,
                user_id=user_id,
                request_id=request_id,
                version=version,
                q=q,
            ),
        )
        .order_by(ordering, DiagnosticIssue.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement))


@router.get("/issues/{issue_id}", response_model=IssueDetailResponse)
def issue_detail(issue_id: UUID, db: DatabaseSession) -> dict[str, object]:
    issue = db.get(DiagnosticIssue, issue_id)
    if issue is None:
        raise HTTPException(404, detail={"code": "DIAGNOSTIC_ISSUE_NOT_FOUND"})
    events = list(
        db.scalars(
            select(DiagnosticEvent)
            .where(DiagnosticEvent.issue_id == issue_id)
            .order_by(DiagnosticEvent.timestamp.desc())
            .limit(50)
        )
    )
    history = list(
        db.scalars(
            select(DiagnosticStatusHistory)
            .where(DiagnosticStatusHistory.issue_id == issue_id)
            .order_by(DiagnosticStatusHistory.created_at.desc())
            .limit(50)
        )
    )
    return {
        "issue": issue,
        "events": events,
        "status_history": history,
        "affected_user_count": db.scalar(
            select(func.count(func.distinct(DiagnosticEvent.user_id))).where(
                DiagnosticEvent.issue_id == issue_id
            )
        )
        or 0,
        "affected_versions": list(
            db.scalars(
                select(DiagnosticEvent.version)
                .where(DiagnosticEvent.issue_id == issue_id, DiagnosticEvent.version.is_not(None))
                .distinct()
                .limit(50)
            )
        ),
    }


@router.patch(
    "/issues/{issue_id}",
    response_model=StatusHistoryResponse,
    dependencies=[Depends(require_authenticated_mutation)],
)
def update_issue(
    issue_id: UUID, payload: IssueStatusUpdate, db: DatabaseSession, actor: AdminUser
) -> DiagnosticStatusHistory:
    issue = db.scalar(
        select(DiagnosticIssue).where(DiagnosticIssue.id == issue_id).with_for_update()
    )
    if issue is None:
        raise HTTPException(404, detail={"code": "DIAGNOSTIC_ISSUE_NOT_FOUND"})
    history = change_status(
        db, issue, status=payload.status, actor_user_id=actor.id, note=payload.note
    )
    db.commit()
    return history


@router.get("/events", response_model=list[EventResponse])
def list_events(
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    user_id: UUID | None = None,
    resource_id: UUID | None = None,
    request_id: Annotated[str | None, Query(max_length=128)] = None,
    operation_id: Annotated[str | None, Query(max_length=128)] = None,
    issue_id: UUID | None = None,
    platform: Annotated[str | None, Query(max_length=32)] = None,
    hours: DiagnosticHours = DiagnosticHours.DAY,
) -> list[DiagnosticEvent]:
    stmt = select(DiagnosticEvent).where(
        DiagnosticEvent.timestamp >= datetime.now(UTC) - timedelta(hours=hours)
    )
    for column, value in (
        (DiagnosticEvent.user_id, user_id),
        (DiagnosticEvent.resource_id, resource_id),
        (DiagnosticEvent.request_id, request_id),
        (DiagnosticEvent.operation_id, operation_id),
        (DiagnosticEvent.issue_id, issue_id),
        (DiagnosticEvent.platform, platform),
    ):
        if value is not None:
            stmt = stmt.where(column == value)
    ordering = (
        DiagnosticEvent.timestamp.asc()
        if request_id or operation_id or resource_id
        else DiagnosticEvent.timestamp.desc()
    )
    return list(db.scalars(stmt.order_by(ordering, DiagnosticEvent.id).limit(limit).offset(offset)))


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DiagnosticAlert]:
    return list(
        db.scalars(
            select(DiagnosticAlert)
            .order_by(DiagnosticAlert.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.get("/generations", response_model=GenerationMetricsResponse)
def generation_metrics(
    db: DatabaseSession, hours: DiagnosticHours = DiagnosticHours.DAY
) -> dict[str, object]:
    from datetime import UTC, datetime, timedelta

    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = db.execute(
        select(DiagnosticEvent.operation, DiagnosticEvent.outcome, func.count())
        .where(
            DiagnosticEvent.operation.in_(("workout_generation", "nutrition_generation")),
            DiagnosticEvent.timestamp >= since,
            DiagnosticEvent.platform == "backend",
            DiagnosticEvent.outcome.in_(
                (
                    "success",
                    "failure",
                    "timeout",
                    "cancelled",
                    "reused",
                    "pending_review",
                    "blocked",
                )
            ),
        )
        .group_by(DiagnosticEvent.operation, DiagnosticEvent.outcome)
    ).all()
    totals: dict[str, dict[str, int]] = {}
    for operation, outcome, count in rows:
        outcomes = totals.setdefault(operation, {})
        outcomes[outcome] = count
    summaries = []
    for operation, outcomes in totals.items():
        terminal_count = sum(outcomes.values())
        success_count = outcomes.get("success", 0) + outcomes.get("reused", 0)
        summaries.append(
            {
                "operation": operation,
                "terminal_count": terminal_count,
                "success_count": success_count,
                "success_rate": success_count / terminal_count if terminal_count else None,
                "outcomes": outcomes,
                "average_duration_ms": db.scalar(
                    select(func.avg(DiagnosticEvent.duration_ms)).where(
                        DiagnosticEvent.operation == operation,
                        DiagnosticEvent.timestamp >= since,
                        DiagnosticEvent.platform == "backend",
                        DiagnosticEvent.outcome.not_in(("started", "stage")),
                    )
                ),
            }
        )
    return {
        "hours": hours,
        "operations": summaries,
        "failure_reasons": [
            {"operation": operation, "error_code": code, "count": total}
            for operation, code, total in db.execute(
                select(DiagnosticEvent.operation, DiagnosticEvent.error_code, func.count())
                .where(
                    DiagnosticEvent.timestamp >= since,
                    DiagnosticEvent.platform == "backend",
                    DiagnosticEvent.operation.in_(("workout_generation", "nutrition_generation")),
                    DiagnosticEvent.outcome.in_(("failure", "blocked", "timeout")),
                )
                .group_by(DiagnosticEvent.operation, DiagnosticEvent.error_code)
                .order_by(func.count().desc())
                .limit(20)
            ).all()
        ],
        "incomplete_attempts": len(abandoned_attempts(db, since=since)),
        "quota_integrity": quota_integrity(db, since=since),
        "engine_versions": [
            {
                "operation": operation,
                "version": version or "unknown",
                "outcome": outcome,
                "count": count,
            }
            for operation, version, outcome, count in db.execute(
                select(
                    DiagnosticEvent.operation,
                    DiagnosticEvent.version,
                    DiagnosticEvent.outcome,
                    func.count(),
                )
                .where(
                    DiagnosticEvent.timestamp >= since,
                    DiagnosticEvent.platform == "backend",
                    DiagnosticEvent.operation.in_(("workout_generation", "nutrition_generation")),
                    DiagnosticEvent.outcome.not_in(("started", "stage")),
                )
                .group_by(
                    DiagnosticEvent.operation, DiagnosticEvent.version, DiagnosticEvent.outcome
                )
                .order_by(func.count().desc())
                .limit(100)
            )
        ],
    }


@router.get("/infrastructure", response_model=InfrastructureResponse)
async def infrastructure(
    request: Request, db: DatabaseSession, settings: AppSettings, actor: AdminUser
) -> dict[str, object]:
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    from app.ai.connectivity import agent_connectivity
    from app.body_analysis.models import BodyAnalysis
    from app.notifications.models import NotificationEventDelivery
    from app.nutrition.models import NutritionFoodPhotoAnalysisJob

    now = datetime.now(UTC)
    signals = [
        {
            "component": "api",
            "status": "reachable",
            "observed_at": now,
            "evidence": "authenticated_admin_request",
            "business_operation_verified": False,
        }
    ]
    try:
        db.execute(text("SELECT 1"))
        signals.append(
            {
                "component": "database",
                "status": "reachable",
                "observed_at": now,
                "evidence": "select_1",
                "business_operation_verified": False,
            }
        )
    except SQLAlchemyError:
        db.rollback()
        signals.append(
            {
                "component": "database",
                "status": "unavailable",
                "observed_at": now,
                "evidence": "database_probe_failed",
                "business_operation_verified": False,
            }
        )
    redis = getattr(request.app.state, "redis", None)
    redis_status = "unknown"
    redis_evidence = "no_observation"
    if redis is not None:
        try:
            result = await redis.ping()
            redis_status = "reachable" if result.available else "unavailable"
            redis_evidence = (
                "bounded_ping"
                if result.available
                else f"ping_failed_{(result.error or 'unknown')[:64]}"
            )
        except Exception:
            redis_status = "unavailable"
    signals.append(
        {
            "component": "redis",
            "status": redis_status,
            "observed_at": now if redis else None,
            "evidence": redis_evidence,
            "business_operation_verified": False,
        }
    )
    try:
        agent = await agent_connectivity(request, actor, settings)  # probe uses no member data
        code = agent.get("error_code")
        agent_status = (
            "reachable"
            if code is None
            else "unknown"
            if code == "not_configured"
            else "unavailable"
        )
        evidence = "authenticated_connectivity_probe" if code is None else str(code)
    except Exception:
        agent_status, evidence = "unknown", "probe_unavailable"
    signals.append(
        {
            "component": "ai_agent",
            "status": agent_status,
            "observed_at": now,
            "evidence": evidence,
            "business_operation_verified": False,
        }
    )
    signals.append(
        {
            "component": "regional_connectivity",
            "status": agent_status,
            "observed_at": now,
            "evidence": "agent_route_probe_only",
            "business_operation_verified": False,
        }
    )
    try:
        media_available = settings.media_root.is_dir()
    except OSError:
        media_available = False
    signals.append(
        {
            "component": "media_storage",
            "status": "readable" if media_available else "unknown",
            "observed_at": now,
            "evidence": "directory_stat_only",
            "business_operation_verified": False,
        }
    )
    queues: dict[str, dict[str, int]] = {}
    for name, model in (
        ("body_analysis", BodyAnalysis),
        ("food_photo", NutritionFoodPhotoAnalysisJob),
        ("notifications", NotificationEventDelivery),
    ):
        queues[name] = {
            str(state.value if hasattr(state, "value") else state): total
            for state, total in db.execute(
                select(model.status, func.count()).group_by(model.status)
            ).all()
        }
    for name, model, lease_seconds in (
        ("body_analysis", BodyAnalysis, settings.body_analysis_worker_lease_seconds),
        ("food_photo", NutritionFoodPhotoAnalysisJob, settings.food_photo_worker_lease_seconds),
        ("notifications", NotificationEventDelivery, settings.notification_worker_lease_seconds),
    ):
        queues[name]["stale_leases"] = (
            db.scalar(
                select(func.count())
                .select_from(model)
                .where(
                    model.status == ("analyzing" if name == "body_analysis" else "processing"),
                    model.locked_at < now - timedelta(seconds=lease_seconds),
                )
            )
            or 0
        )
    signals.append(
        {
            "component": "workers",
            "status": "unknown",
            "observed_at": now,
            "evidence": "durable_queue_counts_only",
            "business_operation_verified": False,
        }
    )
    runtime = getattr(request.app.state, "diagnostics_runtime", None)
    if runtime is not None:
        for signal in signals:
            try:
                failed = signal["status"] == "unavailable"
                runtime.submit(
                    EventInput(
                        component=str(signal["component"]),
                        operation="infrastructure_probe",
                        stage="reachability",
                        platform="infrastructure",
                        category="infrastructure_failure" if failed else "unknown",
                        severity="error" if failed else "info",
                        outcome="failure"
                        if failed
                        else "stage"
                        if signal["status"] in {"unknown", "disabled"}
                        else "success",
                        error_code="SERVICE_UNAVAILABLE" if failed else "SERVICE_OBSERVED",
                    )
                )
            except Exception:
                pass
    if runtime is not None:
        queues["diagnostics"] = {"queued": runtime.queued_count, "dropped": runtime.dropped_count}
        signals.append(
            {
                "component": "diagnostics",
                "status": "active"
                if runtime.writer_running
                else "disabled"
                if not runtime.enabled
                else "unavailable",
                "observed_at": now,
                "evidence": "bounded_writer_thread",
                "business_operation_verified": False,
            }
        )
    return {"signals": signals, "queues": queues}
