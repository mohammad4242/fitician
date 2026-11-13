"""Authenticated laptop pull channel; token scope is one environment and repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.auth.dependencies import DatabaseSession

from .connector_schemas import (
    CallStatusResponse,
    CompletionResponse,
    HeartbeatResponse,
    OperationPage,
    OperationResponse,
    PollResponse,
    ProbePollResponse,
    ProbeStatusResponse,
    ProgressResponse,
    ServerEvidenceResponse,
)
from .connectors import _authorize_run, authenticate_connector, claim_call, finish_call, update_call
from .models import DebugConnector, DebugConnectorCall, DebugRun

router = APIRouter(prefix="/api/v1/debug-connectors", tags=["debug-connectors"])
security = HTTPBearer(auto_error=False)


def principal(
    connector_id: UUID,
    db: DatabaseSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> DebugConnector:
    try:
        if credentials is None:
            raise ValueError("connector_not_authorized")
        return authenticate_connector(db, connector_id, credentials.credentials)
    except ValueError:
        raise HTTPException(401, detail={"code": "connector_not_authorized"}) from None


Connector = Annotated[DebugConnector, Depends(principal)]


class Capabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cli_version: str | None = Field(default=None, max_length=40)
    models: list[str] = Field(default_factory=list, max_length=100)
    supports_codex: bool = False
    supports_tests: bool = False
    supports_github: bool = False
    supports_ci: bool = False
    runtime_revision: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    repository_head: str = Field(pattern=r"^[a-f0-9]{40}$")


class Completion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_token: UUID
    result: dict[str, Any]


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_token: UUID
    key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


class ValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_token: UUID
    key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    profile: str = Field(max_length=32)
    tests: list[str] = Field(max_length=16)
    snapshot: dict[str, Any]


class CIStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_token: UUID


@router.post("/{connector_id}/calls/{call_id}/ci-status", response_model=OperationPage)
def ci_status(
    connector_id: UUID,
    call_id: UUID,
    connector: Connector,
    payload: CIStatusRequest,
    db: DatabaseSession,
) -> dict[str, Any]:
    from .automation import operation_json
    from .models import DebugOperation

    call = db.get(DebugConnectorCall, call_id)
    if (
        call is None
        or call.connector_id != connector.id
        or call.lease_token != payload.lease_token
        or call.state != "running"
    ):
        raise HTTPException(409, detail={"code": "connector_lease_lost"})
    run = db.get(DebugRun, call.run_id)
    if run is None:
        raise HTTPException(404, detail={"code": "run_not_found"})
    try:
        _authorize_run(db, run)
    except ValueError:
        raise HTTPException(409, detail={"code": "run_no_longer_authorized"}) from None
    occurrence = UUID(run.evidence["occurrence_id"]) if run.evidence.get("occurrence_id") else None
    rows = db.scalars(
        select(DebugOperation)
        .join(DebugRun, DebugRun.id == DebugOperation.run_id)
        .where(
            DebugRun.thread_id == run.thread_id,
            DebugOperation.environment == connector.environment,
            DebugOperation.occurrence_id == occurrence,
        )
        .order_by(DebugOperation.created_at.desc(), DebugOperation.id.desc())
        .limit(20)
    )
    return {"operations": [operation_json(row) for row in rows]}


@router.post("/{connector_id}/calls/{call_id}/validations", response_model=OperationResponse)
def queue_validation(
    connector_id: UUID,
    call_id: UUID,
    connector: Connector,
    payload: ValidationRequest,
    db: DatabaseSession,
) -> dict[str, Any]:
    from .automation import operation_json
    from .automation import queue_validation as queue

    call = db.scalar(
        select(DebugConnectorCall)
        .where(
            DebugConnectorCall.id == call_id,
            DebugConnectorCall.connector_id == connector.id,
        )
        .with_for_update()
    )
    if call is None or call.lease_token != payload.lease_token or call.state != "running":
        raise HTTPException(409, detail={"code": "connector_lease_lost"})
    try:
        request = payload.model_dump(exclude={"lease_token", "key"})
        row = queue(db, call.run_id, f"ci:{call.id}:{payload.key}", request)
        db.commit()
        return operation_json(row)
    except ValueError as error:
        db.rollback()
        import re

        code = str(error)
        if not re.fullmatch(r"[a-z_]{3,64}", code):
            code = "invalid_validation_request"
        raise HTTPException(409, detail={"code": code}) from None


@router.post(
    "/{connector_id}/calls/{call_id}/server-evidence", response_model=ServerEvidenceResponse
)
def server_evidence(
    connector_id: UUID,
    call_id: UUID,
    connector: Connector,
    payload: EvidenceRequest,
    db: DatabaseSession,
) -> dict[str, str]:
    from .server_evidence import collect

    call = db.scalar(
        select(DebugConnectorCall)
        .where(
            DebugConnectorCall.id == call_id,
            DebugConnectorCall.connector_id == connector.id,
        )
        .with_for_update()
    )
    if call is None or call.lease_token != payload.lease_token or call.state != "running":
        raise HTTPException(409, detail={"code": "connector_lease_lost"})
    try:
        run = db.get(DebugRun, call.run_id)
        if run is None:
            raise ValueError("run_not_found")
        _authorize_run(db, run)
        result = collect(db, run.id, payload.key, process_role="api", call_id=call.id)
        db.commit()
        return result
    except ValueError as error:
        db.rollback()
        raise HTTPException(409, detail={"code": str(error)}) from None


@router.post("/{connector_id}/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    connector_id: UUID, connector: Connector, payload: Capabilities, db: DatabaseSession
) -> dict[str, object]:
    from .automation import availability

    connector.capabilities = payload.model_dump()
    connector.last_seen = datetime.now(UTC)
    db.commit()
    return {
        "connected": True,
        "environment": connector.environment,
        "repository": connector.repository,
        "ci_available": bool(payload.supports_ci and availability(db)["configured"]),
    }


@router.post("/{connector_id}/poll", response_model=PollResponse)
def poll(connector_id: UUID, connector: Connector, db: DatabaseSession) -> dict[str, Any]:
    connector.last_seen = datetime.now(UTC)
    try:
        job = claim_call(db, connector)
    except ValueError as error:
        db.rollback()
        raise HTTPException(409, detail={"code": str(error)}) from None
    db.commit()
    return {"job": job}


@router.get("/{connector_id}/calls/{call_id}/status", response_model=CallStatusResponse)
def status(
    connector_id: UUID, call_id: UUID, connector: Connector, db: DatabaseSession
) -> dict[str, Any]:
    call = db.get(DebugConnectorCall, call_id)
    if call is None or call.connector_id != connector.id:
        raise HTTPException(404, detail={"code": "call_not_found"})
    run = db.get(DebugRun, call.run_id)
    return {"cancel_requested": run is None or run.cancel_requested, "state": call.state}


@router.post("/{connector_id}/calls/{call_id}/complete", response_model=CompletionResponse)
def complete(
    connector_id: UUID,
    call_id: UUID,
    connector: Connector,
    payload: Completion,
    db: DatabaseSession,
) -> dict[str, bool]:
    try:
        finish_call(db, connector, call_id, payload.lease_token, payload.result)
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(409, detail={"code": str(error)}) from None
    return {"stored": True}


class Progress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_token: UUID
    sequence: int = Field(ge=0)
    kind: str = Field(default="tool_progress", max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/{connector_id}/calls/{call_id}/progress", response_model=ProgressResponse)
def progress(
    connector_id: UUID, call_id: UUID, connector: Connector, payload: Progress, db: DatabaseSession
) -> dict[str, Any]:
    if len(__import__("json").dumps(payload.payload).encode()) > 40000:
        raise HTTPException(413, detail={"code": "progress_too_large"})
    try:
        result = update_call(
            db,
            connector,
            call_id,
            payload.lease_token,
            payload.sequence,
            payload.kind,
            payload.payload,
        )
        db.commit()
        return result
    except ValueError as error:
        db.rollback()
        raise HTTPException(409, detail={"code": str(error)}) from None


@router.post("/{connector_id}/probes/poll", response_model=ProbePollResponse)
def poll_probe(connector_id: UUID, connector: Connector, db: DatabaseSession) -> dict[str, Any]:
    from .probes import claim_probe

    result = claim_probe(db, connector)
    db.commit()
    return {"job": result}


@router.post("/{connector_id}/probes/{probe_id}/status", response_model=ProbeStatusResponse)
def probe_status(
    connector_id: UUID,
    probe_id: UUID,
    connector: Connector,
    payload: Completion,
    db: DatabaseSession,
) -> dict[str, bool]:
    from .probes import authorize_probe

    try:
        authorize_probe(db, connector, probe_id, payload.lease_token)
    except ValueError:
        raise HTTPException(409, detail={"code": "probe_not_authorized"}) from None
    connector.last_seen = datetime.now(UTC)
    db.commit()
    return {"authorized": True}


@router.post("/{connector_id}/probes/{probe_id}/complete", response_model=CompletionResponse)
def complete_probe(
    connector_id: UUID,
    probe_id: UUID,
    connector: Connector,
    payload: Completion,
    db: DatabaseSession,
) -> dict[str, bool]:
    from .probes import finish_probe

    if len(__import__("json").dumps(payload.result).encode()) > 32000:
        raise HTTPException(413, detail={"code": "probe_result_too_large"})
    try:
        finish_probe(db, connector, probe_id, payload.lease_token, payload.result)
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(409, detail={"code": str(error)}) from None
    return {"stored": True}
