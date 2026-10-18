from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.session import isolated_session

from .diagnostics_models import (
    DiagnosticAlert,
    DiagnosticEvent,
    DiagnosticIssue,
    DiagnosticStatusHistory,
)
from .diagnostics_schemas import EventInput

logger = logging.getLogger(__name__)

_TITLES = {
    "application_bug": "Application error",
    "api_failure": "API request failed",
    "database_failure": "Database failure",
    "infrastructure_failure": "Infrastructure failure",
    "provider_failure": "Provider failure",
    "engine_validation": "Generation validation failed",
    "invalid_input": "Invalid input",
    "business_rejection": "Operation rejected",
    "quota_limit": "Quota limit reached",
    "safety_restriction": "Safety restriction",
    "auth_failure": "Authentication failed",
    "unknown": "Unexpected issue",
    "job_failure": "Background job failed",
    "interrupted": "Operation interrupted",
    "client_runtime": "Application runtime issue",
}
_EXPECTED_CATEGORIES = {
    "quota_limit",
    "invalid_input",
    "safety_restriction",
    "business_rejection",
    "auth_failure",
}
_ISSUE_OUTCOMES = {"failure", "timeout", "blocked"}


def _fingerprint(event: EventInput) -> str:
    material = "\x1f".join(
        (
            event.component,
            event.operation,
            event.stage,
            event.error_code,
            event.exception_type or "",
            event.source_location or "",
        )
    )
    return hashlib.sha256(material.encode()).hexdigest()


def record_event(
    db: Session,
    event: EventInput,
    *,
    user_id: UUID | None = None,
    trusted: bool = True,
) -> DiagnosticEvent:
    """Deduplicate, append, and group only actionable failures; caller owns commit."""
    now = datetime.now(UTC)
    event_id = event.event_id or uuid4()
    event_values = {
        **{
            key: getattr(event, key)
            for key in (
                "app_version",
                "origin_platform",
                "trace_id",
                "span_id",
                "parent_span_id",
                "record_type",
                "started_at",
                "ended_at",
                "offset_ms",
                "clock_domain",
                "dropped_count",
                "expected_span_count",
            )
        },
        "id": event_id,
        "issue_id": None,
        "request_id": event.request_id,
        "operation_id": event.operation_id,
        "user_id": user_id,
        "component": event.component,
        "operation": event.operation,
        "stage": event.stage,
        "platform": event.platform,
        "version": event.version,
        "build": event.build,
        "category": event.category,
        "severity": event.severity,
        "error_code": event.error_code,
        "exception_type": event.exception_type,
        "source_location": event.source_location,
        "input_fingerprint": event.input_fingerprint,
        "resource_id": event.resource_id,
        "outcome": event.outcome,
        "duration_ms": event.duration_ms,
        "retry_count": event.retry_count,
        "http_status": event.http_status,
        "os_version": event.os_version,
        "timestamp": now,
    }
    inserted_id = db.scalar(
        insert(DiagnosticEvent)
        .values(**event_values)
        .on_conflict_do_nothing(index_elements=[DiagnosticEvent.id])
        .returning(DiagnosticEvent.id)
    )
    if inserted_id is None:
        existing = db.get(DiagnosticEvent, event_id)
        assert existing is not None
        return existing

    creates_issue = (
        event.record_type == "event"
        and event.severity in {"error", "critical"}
        and event.outcome in _ISSUE_OUTCOMES
        and event.category not in _EXPECTED_CATEGORIES
    )
    if not creates_issue:
        db.flush()
        row = db.get(DiagnosticEvent, event_id)
        assert row is not None
        return row

    fingerprint = _fingerprint(event)
    upsert_stmt = (
        insert(DiagnosticIssue)
        .values(
            fingerprint=fingerprint,
            component=event.component,
            operation=event.operation,
            stage=event.stage,
            platform=event.platform,
            severity=event.severity,
            category=event.category,
            error_code=event.error_code,
            exception_type=event.exception_type,
            source_location=event.source_location,
            confidence=(
                "confirmed"
                if trusted and event.exception_type == "ZeroDivisionError" and event.source_location
                else "unknown"
            ),
            title=_TITLES[event.category],
            first_seen=now,
            last_seen=now,
            count=1,
            status="new",
            regression_count=0,
        )
        .on_conflict_do_update(
            index_elements=[DiagnosticIssue.fingerprint],
            set_={
                "last_seen": now,
                "severity": case(
                    (DiagnosticIssue.severity == "critical", "critical"), else_=event.severity
                ),
                "count": DiagnosticIssue.count + 1,
                "regression_count": case(
                    (DiagnosticIssue.status == "resolved", DiagnosticIssue.regression_count + 1),
                    else_=DiagnosticIssue.regression_count,
                ),
                "status": case(
                    (DiagnosticIssue.status == "resolved", "new"),
                    else_=DiagnosticIssue.status,
                ),
            },
        )
        .returning(DiagnosticIssue.id)
    )
    issue_id = db.scalar(upsert_stmt)
    assert issue_id is not None
    db.execute(
        update(DiagnosticEvent).where(DiagnosticEvent.id == event_id).values(issue_id=issue_id)
    )
    db.flush()

    issue = db.get(DiagnosticIssue, issue_id)
    assert issue is not None
    db.refresh(issue)
    since = now - timedelta(minutes=10)
    critical = event.severity == "critical" and issue.status == "new"
    recent_errors = (
        db.scalar(
            select(func.count())
            .select_from(DiagnosticEvent)
            .where(
                DiagnosticEvent.issue_id == issue_id,
                DiagnosticEvent.severity == "error",
                DiagnosticEvent.timestamp >= since,
            )
        )
        or 0
    )
    repeated_error = event.severity == "error" and recent_errors >= 5
    cooldown_elapsed = issue.last_alert_at is None or issue.last_alert_at <= now - timedelta(
        hours=1
    )
    if cooldown_elapsed and (critical or repeated_error):
        reason = "new_critical" if critical else "error_threshold"
        db.add(DiagnosticAlert(issue_id=issue_id, created_at=now, reason=reason))
        issue.last_alert_at = now
    row = db.get(DiagnosticEvent, event_id)
    assert row is not None
    return row


def safe_record(settings: Settings, event: EventInput, *, user_id: UUID | None = None) -> None:
    """Fail-open background writer, isolated from an owning request transaction."""
    try:
        with isolated_session(settings) as db:
            record_event(db, event, user_id=user_id)
            db.commit()
    except Exception as exc:  # diagnostics must never become the application failure
        logger.warning("diagnostics persistence failed (%s)", type(exc).__name__)


def change_status(
    db: Session,
    issue: DiagnosticIssue,
    *,
    status: str,
    actor_user_id: UUID,
    note: str | None,
) -> DiagnosticStatusHistory:
    history = DiagnosticStatusHistory(
        issue_id=issue.id,
        actor_user_id=actor_user_id,
        previous_status=issue.status,
        new_status=status,
        note=note,
    )
    issue.status = status
    db.add(history)
    db.flush()
    return history


def cleanup_retention(
    db: Session, *, now: datetime | None = None, limit: int = 1000
) -> dict[str, int]:
    """Bound each cleanup run and retain only the newest 100k events."""
    moment = now or datetime.now(UTC)
    batch = min(max(limit, 1), 1000)
    event_ids = (
        select(DiagnosticEvent.id)
        .where(DiagnosticEvent.timestamp < moment - timedelta(days=30))
        .order_by(DiagnosticEvent.timestamp)
        .limit(batch)
    )
    result = db.execute(delete(DiagnosticEvent).where(DiagnosticEvent.id.in_(event_ids)))
    expired_count = int(getattr(result, "rowcount", 0) or 0)
    excess = max((db.scalar(select(func.count()).select_from(DiagnosticEvent)) or 0) - 100_000, 0)
    if excess:
        old_ids = (
            select(DiagnosticEvent.id).order_by(DiagnosticEvent.timestamp).limit(min(excess, batch))
        )
        result = db.execute(delete(DiagnosticEvent).where(DiagnosticEvent.id.in_(old_ids)))
        expired_count += int(getattr(result, "rowcount", 0) or 0)
    removed: dict[str, int] = {"events": expired_count}
    for model, date_field, key in (
        (DiagnosticAlert, DiagnosticAlert.created_at, "alerts"),
        (DiagnosticStatusHistory, DiagnosticStatusHistory.created_at, "history"),
        (DiagnosticIssue, DiagnosticIssue.last_seen, "issues"),
    ):
        ids = select(model.id).where(date_field < moment - timedelta(days=90)).limit(batch)
        result = db.execute(delete(model).where(model.id.in_(ids)))
        removed[key] = int(getattr(result, "rowcount", 0) or 0)
        excess_rows = max((db.scalar(select(func.count()).select_from(model)) or 0) - 10_000, 0)
        if excess_rows:
            oldest = select(model.id).order_by(date_field).limit(min(excess_rows, batch))
            result = db.execute(delete(model).where(model.id.in_(oldest)))
            removed[key] += int(getattr(result, "rowcount", 0) or 0)
    return removed


def abandoned_attempts(db: Session, *, since: datetime | None = None) -> list[DiagnosticEvent]:
    """An observed start without a terminal event is unknown, never proof of a failed plan."""
    from sqlalchemy.orm import aliased

    terminal = aliased(DiagnosticEvent)
    now = datetime.now(UTC)
    query = (
        select(DiagnosticEvent)
        .where(
            DiagnosticEvent.record_type == "event",
            DiagnosticEvent.outcome == "started",
            DiagnosticEvent.operation_id.is_not(None),
            DiagnosticEvent.timestamp < now - timedelta(minutes=30),
            DiagnosticEvent.timestamp >= (since or now - timedelta(days=1)),
            ~select(terminal.id)
            .where(
                terminal.record_type == "event",
                terminal.operation_id == DiagnosticEvent.operation_id,
                terminal.outcome.not_in(("started", "stage")),
            )
            .exists(),
        )
        .order_by(DiagnosticEvent.timestamp)
        .limit(100)
    )
    return list(db.scalars(query))


def detect_abandoned_attempts(db: Session) -> int:
    from uuid import NAMESPACE_URL, uuid5

    attempts = abandoned_attempts(db)
    for attempt in attempts:
        record_event(
            db,
            EventInput(
                event_id=uuid5(NAMESPACE_URL, f"fitician:unconfirmed:{attempt.operation_id}"),
                request_id=attempt.request_id,
                operation_id=attempt.operation_id,
                component=attempt.component,
                operation=attempt.operation,
                stage="outcome_unconfirmed",
                platform=attempt.platform,
                category="interrupted",
                severity="warning",
                error_code="WORKFLOW_OUTCOME_UNCONFIRMED",
                outcome="timeout",
            ),
            user_id=attempt.user_id,
        )
    return len(attempts)


def quota_integrity(db: Session, *, since: datetime) -> dict[str, int]:
    """Compare durable charge references; a missing resource requires investigation."""
    from sqlalchemy import String, cast

    from app.entitlements.models import EntitlementQuotaReservation, EntitlementUsageEvent
    from app.nutrition.models import NutritionPlanBundle
    from app.workouts.models import WorkoutPlan

    total = 0
    missing = 0
    for code, prefix, model in (
        ("training.plan.generate", "workout-plan:", WorkoutPlan),
        ("nutrition.plan.generate", "nutrition-plan-bundle:", NutritionPlanBundle),
    ):
        scoped = (
            EntitlementUsageEvent.entitlement_key == code,
            EntitlementUsageEvent.occurred_at >= since,
        )
        total += (
            db.scalar(select(func.count()).select_from(EntitlementUsageEvent).where(*scoped)) or 0
        )
        missing += (
            db.scalar(
                select(func.count())
                .select_from(EntitlementUsageEvent)
                .where(
                    *scoped,
                    ~select(model.id)
                    .where(
                        EntitlementUsageEvent.resource_key
                        == func.concat(prefix, cast(model.id, String)),
                        EntitlementUsageEvent.user_id == model.user_id,
                    )
                    .exists(),
                )
            )
            or 0
        )
    reserved = (
        db.scalar(
            select(func.count())
            .select_from(EntitlementQuotaReservation)
            .where(EntitlementQuotaReservation.created_at >= since)
        )
        or 0
    )
    return {"charges": total, "pending_reservations": reserved, "unresolved_resources": missing}
