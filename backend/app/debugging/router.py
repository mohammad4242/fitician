from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.admin.dependencies import AdminUser, require_admin
from app.auth.dependencies import AppSettings, DatabaseSession, require_authenticated_mutation
from app.observability.diagnostics_models import DiagnosticIssue
from app.observability.environment import diagnostics_environment

from .connector_schemas import (
    AutomationAvailability,
    OperationPage,
    OperationResponse,
    StoredServerEvidenceResponse,
)
from .deployment_router import router as deployment_router
from .findings_router import router as findings_router
from .models import DebugMessage, DebugOperation, DebugRun, DebugRunEvent, DebugThread
from .service import ACTIVE, cancel_run, submit_message

router = APIRouter(
    prefix="/api/v1/admin/diagnostics",
    tags=["admin-debugging"],
    dependencies=[Depends(require_admin)],
)

router.include_router(findings_router)
router.include_router(deployment_router)


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=8000)
    occurrence_id: UUID | None = None
    action: Literal["analyze", "prepare_fix"] = "analyze"


def run_json(run: DebugRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "message_id": str(run.message_id),
        "state": run.state,
        "error_code": run.error_code,
        "config": run.config_snapshot,
        "evidence_id": run.evidence.get("evidence_id"),
        "occurrence_id": run.evidence.get("occurrence_id"),
        "action": run.action,
        "cancel_requested": run.cancel_requested,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }


def translate_error(error: ValueError) -> HTTPException:
    code = str(error)
    return HTTPException(404 if code.endswith("not_found") else 409, detail={"code": code})


class AutomationProbeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    occurrence_id: UUID


@router.post(
    "/issues/{issue_id}/automation-probe",
    response_model=OperationResponse,
    dependencies=[Depends(require_authenticated_mutation)],
)
def automation_probe(
    issue_id: UUID,
    payload: AutomationProbeInput,
    actor: AdminUser,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str, Header(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")
    ],
) -> dict[str, Any]:
    from .automation import operation_json, queue_connection_probe

    try:
        row = queue_connection_probe(db, issue_id, payload.occurrence_id, actor.id, idempotency_key)
        db.commit()
        return operation_json(row)
    except ValueError as error:
        db.rollback()
        raise translate_error(error) from None


@router.get("/automation-status", response_model=AutomationAvailability)
def automation_status(db: DatabaseSession) -> dict[str, Any]:
    from .automation import availability

    return availability(db)


@router.get("/issues/{issue_id}/operations", response_model=OperationPage)
def operations(issue_id: UUID, db: DatabaseSession) -> dict[str, Any]:
    from .automation import operation_json

    if db.get(DiagnosticIssue, issue_id) is None:
        raise HTTPException(404, detail={"code": "issue_not_found"})
    rows = db.scalars(
        select(DebugOperation)
        .join(DebugRun)
        .join(DebugThread)
        .where(
            DebugThread.issue_id == issue_id,
            DebugThread.environment == diagnostics_environment(),
            DebugOperation.environment == diagnostics_environment(),
        )
        .order_by(DebugOperation.created_at.desc(), DebugOperation.id.desc())
        .limit(50)
    )
    return {"operations": [operation_json(row) for row in rows]}


@router.post(
    "/issues/{issue_id}/operations/{operation_id}/cancel",
    response_model=OperationResponse,
    dependencies=[Depends(require_authenticated_mutation)],
)
def cancel_operation(
    issue_id: UUID, operation_id: UUID, actor: AdminUser, db: DatabaseSession
) -> dict[str, Any]:
    from .automation import ACTIVE as OPERATION_ACTIVE
    from .automation import operation_json
    from .service import append_event

    row = db.scalar(
        select(DebugOperation)
        .join(DebugRun)
        .join(DebugThread)
        .where(
            DebugOperation.id == operation_id,
            DebugThread.issue_id == issue_id,
            DebugThread.environment == diagnostics_environment(),
            DebugOperation.environment == diagnostics_environment(),
        )
        .with_for_update(of=DebugOperation)
    )
    if row is None:
        raise HTTPException(404, detail={"code": "operation_not_found"})
    if not row.cancel_requested and row.state in (*OPERATION_ACTIVE, "awaiting_authorization"):
        row.cancel_requested = True
        if row.state == "awaiting_authorization":
            row.state = "cancelled"
        run = db.scalar(select(DebugRun).where(DebugRun.id == row.run_id).with_for_update())
        assert run is not None
        append_event(
            db,
            run,
            "automation_cancel_requested",
            {"operation_id": str(row.id), "actor_id": str(actor.id)},
        )
        db.commit()
    return operation_json(row)


@router.get(
    "/issues/{issue_id}/runs/{run_id}/server-evidence", response_model=StoredServerEvidenceResponse
)
def recorded_server_evidence(issue_id: UUID, run_id: UUID, db: DatabaseSession) -> dict[str, Any]:
    from .server_evidence import PROVENANCE, TOOL

    run = db.scalar(
        select(DebugRun)
        .join(DebugThread)
        .where(
            DebugRun.id == run_id,
            DebugThread.issue_id == issue_id,
            DebugThread.environment == diagnostics_environment(),
        )
    )
    if run is None:
        raise HTTPException(404, detail={"code": "run_not_found"})
    event = db.scalar(
        select(DebugRunEvent)
        .where(
            DebugRunEvent.run_id == run.id,
            DebugRunEvent.kind == "tool_completed",
            DebugRunEvent.payload["tool"].as_string() == TOOL,
            DebugRunEvent.payload["provenance"].as_string() == PROVENANCE,
        )
        .order_by(DebugRunEvent.sequence.desc())
        .limit(1)
    )
    return (
        {"state": "recorded", "evidence_id": str(event.id), "output": event.payload["output"]}
        if event
        else {"state": "not_collected"}
    )


@router.get("/issues/{issue_id}/conversation")
def conversation(
    issue_id: UUID,
    db: DatabaseSession,
    before: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, Any]:

    if db.get(DiagnosticIssue, issue_id) is None:
        raise HTTPException(404, detail={"code": "issue_not_found"})
    thread = db.scalar(
        select(DebugThread).where(
            DebugThread.issue_id == issue_id,
            DebugThread.environment == diagnostics_environment(),
        )
    )
    if thread is None:
        return {"thread_id": None, "messages": [], "runs": [], "next_cursor": None}
    statement = select(DebugMessage).where(DebugMessage.thread_id == thread.id)
    if before:
        anchor = db.get(DebugMessage, before)
        if anchor is None or anchor.thread_id != thread.id:
            raise HTTPException(404, detail={"code": "message_not_found"})
        from sqlalchemy import tuple_

        statement = statement.where(
            tuple_(DebugMessage.created_at, DebugMessage.id) < (anchor.created_at, anchor.id)
        )
    messages = list(
        db.scalars(
            statement.order_by(DebugMessage.created_at.desc(), DebugMessage.id.desc()).limit(
                limit + 1
            )
        )
    )
    more = len(messages) > limit
    messages = messages[:limit]
    runs = list(
        db.scalars(
            select(DebugRun)
            .where(
                DebugRun.thread_id == thread.id,
                (DebugRun.message_id.in_([message.id for message in messages]))
                | DebugRun.state.in_(ACTIVE),
            )
            .order_by(DebugRun.created_at.desc(), DebugRun.id.desc())
        )
    )
    return {
        "thread_id": str(thread.id),
        "messages": [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
            for message in reversed(messages)
        ],
        "runs": [run_json(run) for run in runs],
        "next_cursor": str(messages[-1].id) if more else None,
    }


@router.post("/issues/{issue_id}/messages", dependencies=[Depends(require_authenticated_mutation)])
def post_message(
    issue_id: UUID,
    payload: MessageInput,
    actor: AdminUser,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str, Header(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    ],
) -> dict[str, Any]:
    try:
        run = submit_message(
            db,
            issue_id,
            actor.id,
            payload.content,
            idempotency_key,
            payload.occurrence_id,
            payload.action,
        )
        db.commit()
        return run_json(run)
    except ValueError as error:
        db.rollback()
        raise translate_error(error) from None


@router.get("/issues/{issue_id}/runs/{run_id}/events")
def run_events(
    issue_id: UUID, run_id: UUID, db: DatabaseSession, after: Annotated[int, Query(ge=0)] = 0
) -> dict[str, Any]:

    run = db.scalar(
        select(DebugRun)
        .join(DebugThread)
        .where(
            DebugRun.id == run_id,
            DebugThread.issue_id == issue_id,
            DebugThread.environment == diagnostics_environment(),
        )
    )
    if run is None:
        raise HTTPException(404, detail={"code": "run_not_found"})
    events = list(
        db.scalars(
            select(DebugRunEvent)
            .where(DebugRunEvent.run_id == run_id, DebugRunEvent.sequence > after)
            .order_by(DebugRunEvent.sequence)
            .limit(100)
        )
    )
    return {
        "run": run_json(run),
        "events": [
            {
                "id": str(item.id),
                "sequence": item.sequence,
                "kind": item.kind,
                "payload": item.payload,
                "created_at": item.created_at.isoformat(),
            }
            for item in events
        ],
        "next_cursor": events[-1].sequence if events else after,
    }


@router.post(
    "/issues/{issue_id}/runs/{run_id}/cancel",
    dependencies=[Depends(require_authenticated_mutation)],
)
def cancel(issue_id: UUID, run_id: UUID, actor: AdminUser, db: DatabaseSession) -> dict[str, Any]:
    try:
        run = cancel_run(db, issue_id, run_id)
        db.commit()
        return run_json(run)
    except ValueError as error:
        db.rollback()
        raise translate_error(error) from None


@router.get("/issues/{issue_id}/runs/{run_id}/stream")
def stream_events(
    issue_id: UUID,
    run_id: UUID,
    request: Request,
    settings: AppSettings,
    after: Annotated[int, Query(ge=0)] = 0,
    last_event_id: Annotated[str | None, Header(max_length=20)] = None,
) -> StreamingResponse:
    import asyncio
    import json
    import time

    from sqlalchemy.orm import Session
    from starlette.concurrency import run_in_threadpool

    from app.auth.dependencies import get_current_authentication
    from app.database.session import get_engine

    cursor = max(after, int(last_event_id) if last_event_id and last_event_id.isdigit() else 0)

    def read_page(position: int) -> dict[str, Any]:
        with Session(get_engine(settings)) as db:
            principal = get_current_authentication(request, db, settings, None)
            if not principal.user.is_admin:
                raise HTTPException(403, detail={"code": "ADMIN_ROLE_REQUIRED"})
            return run_events(issue_id, run_id, db, position)

    # Validate scope and current session before returning HTTP 200.
    read_page(cursor)

    async def generate() -> AsyncIterator[str]:
        position = cursor
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not await request.is_disconnected():
            try:
                page = await run_in_threadpool(read_page, position)
            except HTTPException:
                return
            for event in page["events"]:
                position = event["sequence"]
                yield f"id: {position}\ndata: {json.dumps(event)}\n\n"
            if page["run"]["state"] not in ACTIVE:
                return
            yield ": keepalive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


class ConnectorEnrollment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)


@router.post("/automation-workers", dependencies=[Depends(require_authenticated_mutation)])
def enroll_automation(
    payload: ConnectorEnrollment, actor: AdminUser, db: DatabaseSession
) -> dict[str, Any]:
    from .connectors import enroll_connector

    try:
        worker, token = enroll_connector(db, actor.id, payload.name, kind="automation")
        db.commit()
        return {
            "id": str(worker.id),
            "token": token,
            "environment": worker.environment,
            "repository_name": worker.repository,
            "name": worker.name,
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail={"code": "automation_worker_already_enrolled"}) from None
    except ValueError as error:
        db.rollback()
        raise translate_error(error) from None


@router.get("/automation-workers")
def list_automation(db: DatabaseSession) -> list[dict[str, Any]]:
    from datetime import UTC, datetime, timedelta

    from .models import DebugConnector

    rows = db.scalars(
        select(DebugConnector)
        .where(
            DebugConnector.kind == "automation",
            DebugConnector.environment == diagnostics_environment(),
        )
        .order_by(DebugConnector.created_at.desc())
    )
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "environment": row.environment,
            "repository_name": row.repository,
            "revoked": row.revoked,
            "connected": bool(
                not row.revoked
                and row.last_seen
                and row.last_seen > datetime.now(UTC) - timedelta(seconds=30)
            ),
            "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            "capabilities": row.capabilities,
        }
        for row in rows
    ]


@router.post("/connectors", dependencies=[Depends(require_authenticated_mutation)])
def enroll_laptop(
    payload: ConnectorEnrollment, actor: AdminUser, db: DatabaseSession
) -> dict[str, Any]:
    from .connectors import enroll_connector

    connector, token = enroll_connector(db, actor.id, payload.name)
    db.commit()
    return {
        "id": str(connector.id),
        "token": token,
        "environment": connector.environment,
        "repository": connector.repository,
    }


@router.get("/connectors")
def list_laptops(db: DatabaseSession) -> list[dict[str, Any]]:
    from .models import DebugConnector

    return [
        {
            "id": str(row.id),
            "name": row.name,
            "environment": row.environment,
            "repository": row.repository,
            "revoked": row.revoked,
            "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            "capabilities": row.capabilities,
        }
        for row in db.scalars(
            select(DebugConnector).where(
                DebugConnector.environment == diagnostics_environment(),
                DebugConnector.kind == "runtime",
            )
        )
    ]


@router.post(
    "/connectors/{connector_id}/revoke", dependencies=[Depends(require_authenticated_mutation)]
)
@router.post(
    "/automation-workers/{connector_id}/revoke",
    dependencies=[Depends(require_authenticated_mutation)],
)
def revoke_laptop(connector_id: UUID, actor: AdminUser, db: DatabaseSession) -> dict[str, bool]:
    from .models import DebugConnector

    row = db.get(DebugConnector, connector_id)
    if row is None or row.environment != diagnostics_environment():
        raise HTTPException(404, detail={"code": "connector_not_found"})
    row.revoked = True
    from .connectors import audit_connector

    audit_connector(db, actor.id, row.id, "revoked")
    db.commit()
    return {"revoked": True}
