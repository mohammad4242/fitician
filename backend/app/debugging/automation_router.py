"""Separate outbound automation identity; runtime/model credentials have no access here."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.auth.dependencies import DatabaseSession

from .automation import authorize_operation, claim_operation, operation_json
from .connector_schemas import (
    AutomationAuthorizationResponse,
    AutomationHeartbeatResponse,
    AutomationPollResponse,
    AutomationProgressResponse,
    OperationResponse,
)
from .connectors import authenticate_connector
from .models import DebugConnector, DebugOperation

router = APIRouter(prefix="/api/v1/debug-automation", tags=["debug-automation"])
security = HTTPBearer(auto_error=False)


def principal(
    worker_id: UUID,
    db: DatabaseSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> DebugConnector:
    try:
        if credentials is None:
            raise ValueError("automation_not_authorized")
        return authenticate_connector(db, worker_id, credentials.credentials, kind="automation")
    except ValueError:
        raise HTTPException(401, detail={"code": "automation_not_authorized"}) from None


Worker = Annotated[DebugConnector, Depends(principal)]


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_token: UUID
    intent: Literal["prepare", "dispatch", "cancel", "observe", "publish"]


class Receipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_token: UUID
    stage: Literal[
        "prepared",
        "dispatch_intent",
        "dispatched",
        "uncertain",
        "completed",
        "failed",
        "waiting",
        "cancel_intent",
        "publication_intent",
        "publication_completed",
    ]
    result: dict[str, Any]


class Heartbeat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runtime_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    github_authenticated: bool
    workflow_installed: bool
    policy_commit: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    error_code: str | None = Field(default=None, pattern=r"^[a-z_]{3,64}$")


@router.post("/{worker_id}/heartbeat", response_model=AutomationHeartbeatResponse)
def heartbeat(
    worker_id: UUID, worker: Worker, payload: Heartbeat, db: DatabaseSession
) -> dict[str, Any]:
    worker.last_seen = datetime.now(UTC)
    worker.capabilities = payload.model_dump()
    db.commit()
    return {"connected": True, "environment": worker.environment}


@router.post("/{worker_id}/poll", response_model=AutomationPollResponse)
def poll(worker_id: UUID, worker: Worker, db: DatabaseSession) -> dict[str, Any]:
    worker.last_seen = datetime.now(UTC)
    row = claim_operation(db, worker)
    value = (
        None
        if row is None
        else {
            **operation_json(row),
            "lease_token": str(row.lease_token),
            "request": row.request,
            "repository": worker.repository,
        }
    )
    db.commit()
    return {"job": value}


@router.get("/{worker_id}/operations/{operation_id}", response_model=OperationResponse)
def status(
    worker_id: UUID, operation_id: UUID, worker: Worker, db: DatabaseSession
) -> dict[str, Any]:
    row = db.scalar(
        select(DebugOperation).where(
            DebugOperation.id == operation_id,
            DebugOperation.worker_id == worker.id,
            DebugOperation.environment == worker.environment,
        )
    )
    if row is None:
        raise HTTPException(404, detail={"code": "operation_not_found"})
    return operation_json(row)


@router.post(
    "/{worker_id}/operations/{operation_id}/authorize",
    response_model=AutomationAuthorizationResponse,
)
def authorize(
    worker_id: UUID, operation_id: UUID, worker: Worker, payload: Intent, db: DatabaseSession
) -> dict[str, Any]:
    from .automation import leased_operation

    try:
        row = leased_operation(db, worker, operation_id, payload.lease_token)
        run = authorize_operation(db, row)
        cancelled = row.cancel_requested or run.cancel_requested
        allowed = (
            payload.intent == "prepare"
            and row.state == "preparing"
            and not cancelled
            or payload.intent == "dispatch"
            and row.state == "dispatching"
            and not cancelled
            or payload.intent == "cancel"
            and bool(row.result.get("workflow_run_id"))
            and cancelled
            or payload.intent == "observe"
            or payload.intent == "publish"
            and row.kind == "publish_pr"
            and row.state == "dispatching"
            and not cancelled
        )
        db.commit()
        return {"authorized": bool(allowed), "cancel_requested": cancelled, "state": row.state}
    except ValueError:
        db.rollback()
        raise HTTPException(409, detail={"code": "automation_lease_or_authority_lost"}) from None


@router.post(
    "/{worker_id}/operations/{operation_id}/progress", response_model=AutomationProgressResponse
)
def progress(
    worker_id: UUID, operation_id: UUID, worker: Worker, payload: Receipt, db: DatabaseSession
) -> dict[str, Any]:
    from .automation import record_progress

    try:
        result = record_progress(
            db, worker, operation_id, payload.lease_token, payload.stage, payload.result
        )
        db.commit()
        return result
    except ValueError as error:
        import re

        db.rollback()
        code = str(error)
        if not re.fullmatch(r"[a-z_]{3,64}", code):
            code = "invalid_automation_receipt"
        raise HTTPException(409, detail={"code": code}) from None
