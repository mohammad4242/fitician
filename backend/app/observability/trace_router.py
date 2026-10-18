from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from app.auth.dependencies import AppSettings, DatabaseSession

from .diagnostics_schemas import DiagnosticHours
from .trace_queries import analytics, explore, trace_detail

router = APIRouter()


@router.get("/traces")
def traces(
    db: DatabaseSession,
    user_id: UUID | None = None,
    trace_id: Annotated[str | None, Query(pattern=r"^[a-f0-9]{32}$")] = None,
    request_id: Annotated[str | None, Query(max_length=128)] = None,
    operation_id: Annotated[str | None, Query(max_length=128)] = None,
    platform: Annotated[str | None, Query(max_length=32)] = None,
    component: Annotated[str | None, Query(max_length=80)] = None,
    operation: Annotated[str | None, Query(max_length=80)] = None,
    outcome: Annotated[str | None, Query(max_length=24)] = None,
    error_code: Annotated[str | None, Query(max_length=64)] = None,
    since: datetime | None = None,
    until: datetime | None = None,
    sort: Literal["newest", "slowest", "failed"] = "newest",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> dict[str, Any]:
    since = since or datetime.now(UTC) - timedelta(days=1)
    if since.tzinfo is None or (until and until.tzinfo is None):
        raise HTTPException(422, detail={"code": "TIMEZONE_REQUIRED"})
    if until and until < since:
        raise HTTPException(422, detail={"code": "INVALID_TIME_RANGE"})
    return explore(
        db,
        limit=limit,
        offset=offset,
        since=since,
        until=until,
        sort=sort,
        filters=dict(
            user_id=user_id,
            trace_id=trace_id,
            request_id=request_id,
            operation_id=operation_id,
            platform=platform,
            component=component,
            operation=operation,
            outcome=outcome,
            error_code=error_code,
        ),
    )


@router.get("/traces/{trace_id}")
def detail(db: DatabaseSession, trace_id: str) -> dict[str, Any]:
    import re

    if not re.fullmatch(r"[a-f0-9]{32}", trace_id):
        raise HTTPException(422, detail={"code": "INVALID_TRACE_ID"})
    return trace_detail(db, trace_id)


@router.get("/trace-analytics")
def aggregate(
    db: DatabaseSession,
    settings: AppSettings,
    request: Request,
    hours: DiagnosticHours = DiagnosticHours.DAY,
) -> dict[str, Any]:
    result = analytics(db, int(hours))
    runtime = getattr(request.app.state, "diagnostics_runtime", None)
    result["capture"] = dict(
        success_sample_rate=settings.diagnostics_success_sample_rate,
        process_dropped_count=getattr(runtime, "dropped_count", 0),
        queue_depth=getattr(runtime, "queued_count", 0),
        process_local=True,
    )
    return result
