"""Durable, admin-requested, read-only runtime verification without a fabricated issue."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User

from .appserver import SUPPORTED_VERSIONS
from .models import DebugConnector, DebugConnectorProbe
from .privacy import sanitize_payload


def queue_probe(
    db: Session, connector: DebugConnector, actor_id: UUID, model: str
) -> DebugConnectorProbe:
    actor = db.get(User, actor_id)
    if (
        actor is None
        or not actor.is_admin
        or connector.kind != "runtime"
        or connector.revoked
        or model not in connector.capabilities.get("models", [])
    ):
        raise ValueError("probe_not_authorized")
    now = datetime.now(UTC)
    for stale in db.scalars(
        select(DebugConnectorProbe).where(
            DebugConnectorProbe.connector_id == connector.id,
            DebugConnectorProbe.state.in_(["queued", "running"]),
        )
    ):
        if stale.created_at and stale.created_at < now - timedelta(seconds=150):
            stale.state = "failed"
        else:
            raise ValueError("runtime_probe_already_active")
    row = DebugConnectorProbe(
        connector_id=connector.id,
        actor_id=actor_id,
        model=model,
        release_commit=connector.capabilities["repository_head"],
    )
    db.add(row)
    db.flush()
    return row


def claim_probe(db: Session, connector: DebugConnector) -> dict[str, Any] | None:
    row = db.scalar(
        select(DebugConnectorProbe)
        .where(
            DebugConnectorProbe.connector_id == connector.id, DebugConnectorProbe.state == "queued"
        )
        .order_by(DebugConnectorProbe.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if row is None:
        return None
    actor = db.get(User, row.actor_id) if row.actor_id else None
    if actor is None or not actor.is_admin:
        row.state = "failed"
        return None
    row.state = "running"
    row.lease_token = uuid4()
    row.lease_until = datetime.now(UTC) + timedelta(seconds=90)
    return {
        "id": str(row.id),
        "model": row.model,
        "release_commit": row.release_commit,
        "lease_token": str(row.lease_token),
    }


def authorize_probe(
    db: Session, connector: DebugConnector, probe_id: UUID, lease: UUID
) -> DebugConnectorProbe:
    row = db.scalar(
        select(DebugConnectorProbe)
        .where(DebugConnectorProbe.id == probe_id, DebugConnectorProbe.connector_id == connector.id)
        .with_for_update()
    )
    actor = db.get(User, row.actor_id) if row and row.actor_id else None
    if (
        row is None
        or row.lease_token != lease
        or row.state != "running"
        or actor is None
        or not actor.is_admin
        or connector.revoked
        or row.lease_until is None
        or row.lease_until < datetime.now(UTC)
    ):
        raise ValueError("probe_not_authorized")
    return row


def finish_probe(
    db: Session, connector: DebugConnector, probe_id: UUID, lease: UUID, result: dict[str, Any]
) -> None:
    row = authorize_probe(db, connector, probe_id, lease)
    if result.get("model") != row.model:
        raise ValueError("probe_model_mismatch")
    row.result = json.loads(json.dumps(sanitize_payload(result)))
    row.state = "completed"
    row.lease_until = None


async def run_profile_probe(
    db: Session, connector: DebugConnector, actor_id: UUID, model: str
) -> bool:
    row = queue_probe(db, connector, actor_id, model)
    identifier = row.id
    db.commit()
    for _ in range(120):
        await asyncio.sleep(0.5)
        db.expire_all()
        latest = db.get(DebugConnectorProbe, identifier)
        if latest is None:
            return False
        if latest.state == "completed":
            result = latest.result or {}
            return (
                result.get("model") == model
                and result.get("cli_version") in SUPPORTED_VERSIONS
                and result.get("read_tool_executed") is True
                and bool(result.get("output"))
                and not result.get("error_code")
            )
        if latest.state == "failed":
            return False
    latest = db.get(DebugConnectorProbe, identifier)
    if latest:
        latest.state = "failed"
        db.commit()
    return False
