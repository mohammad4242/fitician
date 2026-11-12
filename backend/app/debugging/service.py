from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.body_analysis.admin_config.enums import AITaskType
from app.body_analysis.admin_config.models import AITaskConfig
from app.observability.diagnostics_models import DiagnosticEvent, DiagnosticIssue
from app.observability.environment import diagnostics_environment
from app.observability.evidence import evidence_package

from .models import DebugMessage, DebugRun, DebugRunEvent, DebugThread
from .privacy import sanitize_text

ACTIVE = (
    "queued",
    "investigating",
    "editing",
    "testing",
    "awaiting_authorization",
    "deploying",
    "verifying",
)


def get_thread(db: Session, issue_id: UUID) -> DebugThread:
    if db.get(DiagnosticIssue, issue_id) is None:
        raise ValueError("issue_not_found")
    environment = diagnostics_environment()
    db.execute(
        insert(DebugThread)
        .values(issue_id=issue_id, environment=environment)
        .on_conflict_do_nothing(index_elements=["issue_id", "environment"])
    )
    thread = db.scalar(
        select(DebugThread)
        .where(DebugThread.issue_id == issue_id, DebugThread.environment == environment)
        .with_for_update()
    )
    assert thread is not None
    return thread


def append_event(db: Session, run: DebugRun, kind: str, payload: dict[str, object]) -> None:
    # Caller owns the run row lock, serializing event sequence allocation.
    sequence = (
        db.scalar(select(func.max(DebugRunEvent.sequence)).where(DebugRunEvent.run_id == run.id))
        or 0
    ) + 1
    db.add(DebugRunEvent(run_id=run.id, sequence=sequence, kind=kind, payload=payload))
    db.flush()


def submit_message(
    db: Session,
    issue_id: UUID,
    actor_id: UUID,
    content: str,
    key: str,
    occurrence_id: UUID | None = None,
    action: str = "analyze",
) -> DebugRun:
    thread = get_thread(db, issue_id)
    safe = sanitize_text(content).strip()
    if not safe or len(content) > 8000:
        raise ValueError("invalid_message")
    if action not in ("analyze", "prepare_fix"):
        raise ValueError("unsupported_action")
    if occurrence_id is not None:
        occurrence = db.get(DiagnosticEvent, occurrence_id)
        if occurrence is None or occurrence.issue_id != issue_id:
            raise ValueError("occurrence_not_found")
    digest = hashlib.sha256(json.dumps([safe, str(occurrence_id), action]).encode()).hexdigest()
    existing = db.scalar(
        select(DebugMessage).where(
            DebugMessage.thread_id == thread.id, DebugMessage.submission_key == key
        )
    )
    if existing:
        if existing.request_hash != digest:
            raise ValueError("idempotency_conflict")
        run = db.scalar(select(DebugRun).where(DebugRun.message_id == existing.id))
        assert run is not None
        return run
    if db.scalar(
        select(DebugRun.id).where(DebugRun.thread_id == thread.id, DebugRun.state.in_(ACTIVE))
    ):
        raise ValueError("run_already_active")
    if (
        db.scalar(
            select(func.count(DebugRun.id))
            .join(DebugThread)
            .where(DebugRun.state.in_(ACTIVE), DebugThread.environment == thread.environment)
        )
        or 0
    ) >= 50:
        raise ValueError("debug_queue_capacity_reached")
    message = DebugMessage(
        thread_id=thread.id,
        actor_id=actor_id,
        role="user",
        content=safe,
        submission_key=key,
        request_hash=digest,
    )
    db.add(message)
    db.flush()
    config = db.scalar(select(AITaskConfig).where(AITaskConfig.task_type == AITaskType.DEBUG_AGENT))
    snapshot: dict[str, Any] = (
        {
            name: getattr(config, name)
            for name in (
                "provider",
                "execution_backend",
                "agent_name",
                "agent_model_id",
                "agent_profile_id",
                "primary_model_id",
                "max_output_tokens",
                "timeout_seconds",
                "enabled",
            )
        }
        if config
        else {"enabled": False}
    )
    from .runtime_profiles import snapshot_connector

    snapshot["connector_id"] = snapshot_connector(db, snapshot)
    snapshot["config_updated_at"] = config.updated_at.isoformat() if config else None
    snapshot["effective_temperature"] = None  # No unsupported model option is claimed as effective.
    snapshot["routing_restrictions"] = list(config.routing_restrictions) if config else []
    evidence = evidence_package(db, issue_id, occurrence_id)
    snapshot_payload = evidence.get("snapshot") or {}
    evidence["occurrence_id"] = (
        str(occurrence_id) if occurrence_id else snapshot_payload.get("event_id")
    )
    run = DebugRun(
        thread_id=thread.id,
        message_id=message.id,
        action=action,
        config_snapshot=snapshot,
        evidence=evidence,
    )
    db.add(run)
    db.flush()
    append_event(db, run, "queued", {"action": action})
    return run


def claim_run(db: Session) -> DebugRun | None:
    now = datetime.now(UTC)
    run = db.scalar(
        select(DebugRun)
        .where(
            or_(
                DebugRun.state == "queued",
                DebugRun.state.in_(("investigating", "editing", "testing"))
                & (DebugRun.lease_until < now),
            )
        )
        .order_by(DebugRun.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if run is None:
        return None
    if run.attempt >= 3:
        run.state = "failed"
        run.error_code = "restart_retry_exhausted"
        append_event(db, run, "failed", {"code": run.error_code})
        return None
    run.state = "investigating"
    run.attempt += 1
    run.lease_token = uuid4()
    timeout = min(max(int(run.config_snapshot.get("timeout_seconds", 420)), 10), 600)
    run.lease_until = now + timedelta(seconds=timeout + 30)
    append_event(db, run, "investigating", {"attempt": run.attempt})
    db.flush()
    return run


def cancel_run(db: Session, issue_id: UUID, run_id: UUID) -> DebugRun:
    thread = get_thread(db, issue_id)
    run = db.scalar(
        select(DebugRun)
        .where(DebugRun.id == run_id, DebugRun.thread_id == thread.id)
        .with_for_update()
    )
    if run is None:
        raise ValueError("run_not_found")
    if run.state not in ACTIVE or run.cancel_requested:
        return run
    run.cancel_requested = True
    if run.state == "queued":
        run.state = "cancelled"
    append_event(db, run, "cancel_requested", {})
    return run
