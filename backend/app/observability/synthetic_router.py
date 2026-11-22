"""Explicit, default-off operator capture through the existing diagnostics workspace."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, text

from app.admin.dependencies import AdminUser
from app.auth.dependencies import AppSettings, DatabaseSession, require_authenticated_mutation

from .diagnostics_models import DiagnosticEvent
from .environment import diagnostics_environment
from .evidence_models import DiagnosticEvidenceSnapshot
from .synthetic_probe import record_synthetic_failure

router = APIRouter()


class ProbePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class CaptureResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID
    issue_id: UUID
    sentry_event_id: str | None
    build: str
    environment: str
    delivery: Literal["unconfirmed", "not_configured", "unknown"]


def enabled(settings: AppSettings) -> bool:
    return settings.diagnostics_synthetic_probe_enabled and bool(
        re.fullmatch(r"[a-f0-9]{40}", settings.app_build_sha)
    )


@router.get("/synthetic-probe", response_model=ProbePolicy)
def policy(settings: AppSettings) -> dict[str, bool]:
    return {"enabled": enabled(settings)}


@router.post(
    "/synthetic-probe",
    response_model=CaptureResult,
    status_code=201,
    dependencies=[Depends(require_authenticated_mutation)],
)
def capture(
    request: Request,
    settings: AppSettings,
    actor: AdminUser,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str, Header(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")
    ],
) -> dict[str, Any]:
    if not enabled(settings):
        raise HTTPException(404, detail={"code": "synthetic_probe_disabled_or_release_unknown"})
    environment = diagnostics_environment()
    # One cross-process transaction lease bounds dispatch and concurrent duplicate requests.
    lock = int.from_bytes(
        hashlib.sha256(("synthetic-probe:" + environment).encode()).digest()[:8], signed=True
    )
    if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:identity)"), {"identity": lock}):
        raise HTTPException(409, detail={"code": "synthetic_probe_busy"})
    identifier = uuid5(NAMESPACE_URL, f"fitician-probe:{environment}:{actor.id}:{idempotency_key}")
    previous = db.get(DiagnosticEvent, identifier)
    if previous:
        if previous.build != settings.app_build_sha:
            raise HTTPException(409, detail={"code": "synthetic_probe_release_changed"})
        snapshot = db.scalar(
            select(DiagnosticEvidenceSnapshot)
            .where(DiagnosticEvidenceSnapshot.event_id == identifier)
            .limit(1)
        )
        external_id = snapshot.sentry_event_id if snapshot else None
        return {
            "event_id": str(previous.id),
            "issue_id": str(previous.issue_id),
            "sentry_event_id": external_id,
            "build": previous.build,
            "environment": environment,
            "delivery": "unconfirmed" if external_id else "unknown",
        }
    recent = (
        db.scalar(
            select(func.count())
            .select_from(DiagnosticEvent)
            .where(
                DiagnosticEvent.error_code == "DIAGNOSTIC_SYNTHETIC_FAILURE",
                DiagnosticEvent.timestamp >= datetime.now(UTC) - timedelta(hours=1),
            )
        )
        or 0
    )
    if recent >= 6:
        raise HTTPException(429, detail={"code": "synthetic_probe_rate_limited"})
    result = record_synthetic_failure(
        db,
        settings.app_build_sha,
        event_id=identifier,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    # This is local persistence, never a claim of external ingestion or SMS delivery.
    return result
