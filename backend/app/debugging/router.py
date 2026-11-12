from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.admin.dependencies import AdminUser, require_admin
from app.auth.dependencies import AppSettings, DatabaseSession, require_authenticated_mutation
from app.observability.diagnostics_models import DiagnosticIssue
from app.observability.environment import diagnostics_environment

from .models import DebugMessage, DebugRun, DebugRunEvent, DebugThread
from .service import ACTIVE, cancel_run, submit_message

router = APIRouter(
    prefix="/api/v1/admin/diagnostics",
    tags=["admin-debugging"],
    dependencies=[Depends(require_admin)],
)


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=8000)
    occurrence_id: UUID | None = None
    action: Literal["analyze", "prepare_fix"] = "analyze"


def run_json(run: DebugRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
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
            .where(DebugRun.thread_id == thread.id)
            .order_by(DebugRun.created_at.desc())
            .limit(20)
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
            select(DebugConnector).where(DebugConnector.environment == diagnostics_environment())
        )
    ]


@router.post(
    "/connectors/{connector_id}/revoke", dependencies=[Depends(require_authenticated_mutation)]
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
