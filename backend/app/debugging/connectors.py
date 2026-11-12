"""Explicit laptop enrollment and durable outbound tool delivery; no inbound remote shell."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.observability.environment import diagnostics_environment

from .models import DebugConnector, DebugConnectorCall, DebugMessage, DebugRun, DebugThread
from .privacy import sanitize_payload, sanitize_text
from .service import ACTIVE

REPOSITORY = "mohammad4242/fitician"
TOOLS = frozenset(
    {
        "fitician_read_file",
        "fitician_search_code",
        "fitician_write_file",
        "fitician_diff",
        "fitician_run_tests",
        "fitician_commit",
        "fitician_create_pr",
        "fitician_codex_turn",
    }
)
MUTATIONS = frozenset({"fitician_write_file", "fitician_commit", "fitician_create_pr"})


def enroll_connector(db: Session, actor_id: UUID, name: str) -> tuple[DebugConnector, str]:
    actor = db.get(User, actor_id)
    if actor is None or not actor.is_admin:
        raise ValueError("connector_not_authorized")
    token = secrets.token_urlsafe(48)
    row = DebugConnector(
        actor_id=actor_id,
        name=sanitize_text(name)[:80],
        environment=diagnostics_environment(),
        repository=REPOSITORY,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
    )
    db.add(row)
    db.flush()
    audit_connector(db, actor_id, row.id, "enrolled")
    return row, token


def authenticate_connector(db: Session, connector_id: UUID, token: str) -> DebugConnector:
    row = db.get(DebugConnector, connector_id)
    actor = db.get(User, row.actor_id) if row and row.actor_id else None
    if (
        actor is None
        or not actor.is_admin
        or row is None
        or row.revoked
        or row.environment != diagnostics_environment()
        or not secrets.compare_digest(row.token_hash, hashlib.sha256(token.encode()).hexdigest())
    ):
        raise ValueError("connector_not_authorized")
    return row


def enqueue_call(
    db: Session,
    run: DebugRun,
    connector: DebugConnector,
    call_key: str,
    tool: str,
    arguments: dict[str, Any],
) -> DebugConnectorCall:
    _authorize_run(db, run)
    thread = db.get(DebugThread, run.thread_id)
    if (
        connector.revoked
        or thread is None
        or connector.environment != thread.environment
        or connector.repository != REPOSITORY
    ):
        raise ValueError("connector_scope_mismatch")
    if run.state not in ACTIVE or run.cancel_requested or tool not in TOOLS:
        raise ValueError("tool_not_authorized")
    if tool in MUTATIONS and run.action != "prepare_fix":
        raise ValueError("mutation_not_authorized")
    encoded = json.dumps(arguments, sort_keys=True)
    if len(encoded.encode()) > 131072:
        raise ValueError("tool_request_too_large")
    # Reject rather than silently changing a patch or storing a secret in a tool request.
    if sanitize_text(encoded) != encoded:
        raise ValueError("sensitive_tool_request_rejected")
    digest = hashlib.sha256((tool + encoded).encode()).hexdigest()
    existing = db.scalar(
        select(DebugConnectorCall).where(
            DebugConnectorCall.run_id == run.id, DebugConnectorCall.call_key == call_key
        )
    )
    if existing:
        if existing.request_hash != digest:
            raise ValueError("tool_idempotency_conflict")
        return existing
    row = DebugConnectorCall(
        run_id=run.id,
        connector_id=connector.id,
        call_key=call_key,
        tool=tool,
        arguments=arguments,
        request_hash=digest,
    )
    db.add(row)
    db.flush()
    return row


def claim_call(db: Session, connector: DebugConnector) -> dict[str, Any] | None:
    now = datetime.now(UTC)
    row = db.scalar(
        select(DebugConnectorCall)
        .join(DebugRun)
        .where(
            DebugConnectorCall.connector_id == connector.id,
            or_(
                DebugConnectorCall.state == "queued",
                (DebugConnectorCall.state == "running") & (DebugConnectorCall.lease_until < now),
            ),
            DebugRun.state.in_(ACTIVE),
            DebugRun.cancel_requested.is_(False),
        )
        .order_by(DebugConnectorCall.created_at)
        .with_for_update(skip_locked=True, of=DebugConnectorCall)
        .limit(1)
    )
    if row is None:
        return None
    run = db.get(DebugRun, row.run_id)
    assert run is not None
    _authorize_run(db, run)
    row.state = "running"
    row.lease_token = uuid4()
    row.lease_until = now + timedelta(seconds=180)
    snapshot = run.evidence.get("snapshot") or {}
    return {
        "id": str(row.id),
        "run_id": str(run.id),
        "thread_id": str(run.thread_id),
        "lease_token": str(row.lease_token),
        "tool": row.tool,
        "arguments": row.arguments,
        "action": run.action,
        "repository": connector.repository,
        "environment": connector.environment,
        "release_commit": snapshot.get("release_commit"),
        "config": run.config_snapshot,
        "evidence": run.evidence,
    }


def finish_call(
    db: Session, connector: DebugConnector, call_id: UUID, lease_token: UUID, result: dict[str, Any]
) -> None:
    row = db.scalar(
        select(DebugConnectorCall)
        .where(DebugConnectorCall.id == call_id, DebugConnectorCall.connector_id == connector.id)
        .with_for_update()
    )
    if row is None or row.lease_token != lease_token:
        raise ValueError("connector_lease_lost")
    if row.state == "completed":
        return
    run = db.get(DebugRun, row.run_id)
    if run is None:
        raise ValueError("run_no_longer_authorized")
    _authorize_run(db, run)
    if len(json.dumps(result).encode()) > 131072:
        raise ValueError("tool_result_too_large")
    row.result = json.loads(json.dumps(sanitize_payload(result)))
    row.state = "completed"
    row.lease_until = None


def _authorize_run(db: Session, run: DebugRun) -> None:
    message = db.get(DebugMessage, run.message_id)
    actor = db.get(User, message.actor_id) if message and message.actor_id else None
    thread = db.get(DebugThread, run.thread_id)
    if (
        actor is None
        or not actor.is_admin
        or run.cancel_requested
        or run.state not in ACTIVE
        or thread is None
        or thread.environment != diagnostics_environment()
    ):
        raise ValueError("run_no_longer_authorized")


def update_call(
    db: Session,
    connector: DebugConnector,
    call_id: UUID,
    lease_token: UUID,
    sequence: int,
    kind: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from .service import append_event

    row = db.scalar(
        select(DebugConnectorCall)
        .where(
            DebugConnectorCall.id == call_id,
            DebugConnectorCall.connector_id == connector.id,
        )
        .with_for_update()
    )
    if row is None or row.lease_token != lease_token or row.state != "running":
        raise ValueError("connector_lease_lost")
    run = db.scalar(select(DebugRun).where(DebugRun.id == row.run_id).with_for_update())
    if run is None:
        raise ValueError("run_no_longer_authorized")
    _authorize_run(db, run)
    row.lease_until = datetime.now(UTC) + timedelta(seconds=180)
    connector.last_seen = datetime.now(UTC)
    if sequence > row.progress_sequence:
        if sequence != row.progress_sequence + 1 or kind not in {
            "tool_started",
            "tool_completed",
            "tool_failed",
            "runtime_started",
            "runtime_completed",
            "tool_progress",
        }:
            raise ValueError("invalid_progress_sequence")
        row.progress_sequence = sequence
        if kind == "tool_started":
            if payload.get("tool") == "fitician_run_tests":
                run.state = "testing"
            elif payload.get("tool") in MUTATIONS:
                run.state = "editing"
        # Neither arbitrary output nor model reasoning is accepted in progress events.
        safe = {
            key: value
            for key, value in payload.items()
            if key in {"tool", "status", "model", "commit", "branch", "pr_url"}
        }
        append_event(
            db,
            run,
            kind,
            {**json.loads(json.dumps(sanitize_payload(safe))), "call_id": str(row.id)},
        )
    return {"cancel_requested": False, "sequence": row.progress_sequence}


def audit_connector(db: Session, actor_id: UUID, connector_id: UUID, operation: str) -> None:
    from app.body_analysis.admin_config.enums import AIAuditAction, AITaskType
    from app.body_analysis.admin_config.models import AIAuditEvent

    db.add(
        AIAuditEvent(
            actor_user_id=actor_id,
            action=AIAuditAction.CONFIG_UPDATED,
            task_type=AITaskType.DEBUG_AGENT,
            changed_fields=[f"debug_connector_{operation}", str(connector_id)],
        )
    )
