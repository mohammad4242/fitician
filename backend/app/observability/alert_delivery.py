"""Durable SMS aggregation. No provider call takes place inside a database transaction."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import case, func, select, text
from sqlalchemy.orm import Session

from app.config import Settings

from .alert_sms import SmsReceipt, compose_alert_message
from .diagnostics_models import DiagnosticAlertAttempt, DiagnosticAlertDelivery, DiagnosticIssue
from .environment import diagnostics_environment


def enqueue_alerts(db: Session, settings: Settings, *, now: datetime) -> int:
    if not settings.diagnostics_alert_enabled or not settings.diagnostics_alert_enabled_at:
        return 0
    environment = diagnostics_environment()
    current = (
        select(DiagnosticAlertDelivery.id)
        .where(
            DiagnosticAlertDelivery.issue_id == DiagnosticIssue.id,
            DiagnosticAlertDelivery.environment == environment,
            DiagnosticAlertDelivery.occurrence_total >= DiagnosticIssue.count,
        )
        .exists()
    )
    issues = db.scalars(
        select(DiagnosticIssue)
        .where(
            DiagnosticIssue.last_seen >= settings.diagnostics_alert_enabled_at,
            DiagnosticIssue.status.in_(["new", "investigating"]),
            DiagnosticIssue.component.not_in(
                ["diagnostics-alert-worker", "diagnostics-sync-worker", "sentry_sdk"]
            ),
            ~current,
        )
        .order_by(DiagnosticIssue.last_seen)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    count = 0
    for issue in issues:
        row = db.scalar(
            select(DiagnosticAlertDelivery).where(
                DiagnosticAlertDelivery.issue_id == issue.id,
                DiagnosticAlertDelivery.environment == environment,
            )
        )
        delay = (
            0 if issue.severity == "critical" else settings.diagnostics_alert_aggregation_seconds
        )
        if row is None:
            row = DiagnosticAlertDelivery(
                issue_id=issue.id,
                environment=environment,
                occurrence_total=issue.count,
                regression_count=issue.regression_count,
                available_at=now + timedelta(seconds=delay),
            )
            db.add(row)
        elif row.state == "sending":
            continue
        elif row.state in {"queued", "retrying"}:
            row.occurrence_total = issue.count
        else:
            regressed = issue.regression_count > row.regression_count
            row.generation += 1
            row.regression_count = issue.regression_count
            row.occurrence_total = issue.count
            row.state = "queued"
            row.attempts = 0
            row.error_code = None
            row.provider_message_id = None
            row.available_at = max(
                now + timedelta(seconds=delay),
                row.last_dispatch_at
                + timedelta(seconds=settings.diagnostics_alert_cooldown_seconds)
                if row.last_dispatch_at and not regressed
                else now,
            )
        count += 1
    db.flush()
    return count


def claim_alert(db: Session, settings: Settings, *, now: datetime) -> dict[str, Any] | None:
    if not settings.diagnostics_alert_enabled or not settings.diagnostics_alert_enabled_at:
        return None
    environment = diagnostics_environment()
    key = int.from_bytes(hashlib.sha256(("fitician-alert:" + environment).encode()).digest()[:8])
    if not db.scalar(
        text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key & ((1 << 63) - 1)}
    ):
        return None
    for stale in db.scalars(
        select(DiagnosticAlertDelivery)
        .where(
            DiagnosticAlertDelivery.environment == environment,
            DiagnosticAlertDelivery.state == "sending",
            DiagnosticAlertDelivery.lease_until < now,
        )
        .with_for_update(skip_locked=True)
    ):
        stale.state = "uncertain"
        stale.error_code = "worker_acknowledgment_unknown"
        if attempt := db.get(DiagnosticAlertAttempt, stale.current_attempt_id):
            attempt.state = "uncertain"
            attempt.error_code = stale.error_code
            attempt.finished_at = now
            stale.covered_count = attempt.occurrence_total
            attempt.next_receipt_at = now + timedelta(seconds=30)
    attempts = (
        select(DiagnosticAlertAttempt)
        .join(DiagnosticAlertDelivery)
        .where(DiagnosticAlertDelivery.environment == environment)
    )
    last = db.scalar(select(func.max(attempts.subquery().c.started_at)))
    if last and now < last + timedelta(seconds=settings.diagnostics_alert_min_interval_seconds):
        return None
    hourly = (
        db.scalar(
            select(func.count()).select_from(
                attempts.where(
                    DiagnosticAlertAttempt.started_at > now - timedelta(hours=1)
                ).subquery()
            )
        )
        or 0
    )
    if hourly >= settings.diagnostics_alert_max_per_hour:
        return None
    row = db.scalar(
        select(DiagnosticAlertDelivery)
        .join(DiagnosticIssue)
        .where(
            DiagnosticAlertDelivery.environment == environment,
            DiagnosticAlertDelivery.state.in_(["queued", "retrying"]),
            DiagnosticAlertDelivery.available_at <= now,
        )
        .order_by(
            case((DiagnosticIssue.severity == "critical", 0), else_=1),
            DiagnosticAlertDelivery.available_at,
        )
        .with_for_update(skip_locked=True, of=DiagnosticAlertDelivery)
        .limit(1)
    )
    if row is None:
        return None
    issue = db.get(DiagnosticIssue, row.issue_id)
    if issue is None or issue.status in {"resolved", "ignored"}:
        row.state = "suppressed"
        row.covered_count = row.occurrence_total
        return None
    identifier = uuid4()
    message = compose_alert_message(
        issue.id,
        issue.category,
        issue.operation,
        row.occurrence_total - row.covered_count,
        settings.frontend_origin,
        notice_id=identifier,
    )
    row.attempts += 1
    attempt = DiagnosticAlertAttempt(
        id=identifier,
        delivery_id=row.id,
        generation=row.generation,
        dispatch_index=row.attempts,
        occurrence_total=row.occurrence_total,
        message=message,
        started_at=now,
    )
    db.add(attempt)
    db.flush()
    row.state = "sending"
    row.current_attempt_id = attempt.id
    row.last_dispatch_at = now
    row.lease_until = now + timedelta(seconds=60)
    return {"attempt_id": attempt.id, "text": message}


def complete_alert(db: Session, attempt_id: UUID, receipt: SmsReceipt, *, now: datetime) -> None:
    attempt = db.get(DiagnosticAlertAttempt, attempt_id)
    if attempt is None:
        raise ValueError("alert_attempt_not_found")
    row = db.scalar(
        select(DiagnosticAlertDelivery)
        .where(DiagnosticAlertDelivery.id == attempt.delivery_id)
        .with_for_update()
    )
    if row is None or row.environment != diagnostics_environment():
        raise ValueError("alert_scope_mismatch")
    if row.current_attempt_id != attempt.id or row.state != "sending":
        return
    if receipt.state not in {"accepted", "failed", "retrying", "uncertain"}:
        raise ValueError("invalid_alert_receipt")
    state = "failed" if receipt.state == "retrying" and row.attempts >= 5 else receipt.state
    row.state = attempt.state = state
    row.error_code = attempt.error_code = receipt.error_code
    row.provider_message_id = attempt.provider_message_id = receipt.provider_id
    attempt.finished_at = now
    row.lease_until = None
    if state == "retrying":
        row.available_at = now + timedelta(seconds=max(receipt.retry_after, 30 * 2**row.attempts))
    else:
        row.covered_count = attempt.occurrence_total
    if state in {"accepted", "uncertain"}:
        attempt.next_receipt_at = now + timedelta(seconds=30)


def claim_receipt(db: Session, *, now: datetime) -> UUID | None:
    attempt = db.scalar(
        select(DiagnosticAlertAttempt)
        .join(DiagnosticAlertDelivery)
        .where(
            DiagnosticAlertDelivery.environment == diagnostics_environment(),
            DiagnosticAlertAttempt.state.in_(["accepted", "uncertain"]),
            DiagnosticAlertAttempt.next_receipt_at <= now,
            DiagnosticAlertAttempt.receipt_attempts < 12,
        )
        .order_by(DiagnosticAlertAttempt.next_receipt_at)
        .limit(1)
        .with_for_update(skip_locked=True, of=DiagnosticAlertAttempt)
    )
    if attempt is None:
        return None
    attempt.receipt_attempts += 1
    attempt.next_receipt_at = now + timedelta(seconds=60)
    return attempt.id


def record_receipt(db: Session, attempt_id: UUID, receipt: SmsReceipt, *, now: datetime) -> None:
    attempt = db.scalar(
        select(DiagnosticAlertAttempt)
        .join(DiagnosticAlertDelivery)
        .where(
            DiagnosticAlertAttempt.id == attempt_id,
            DiagnosticAlertDelivery.environment == diagnostics_environment(),
        )
        .with_for_update(of=DiagnosticAlertAttempt)
    )
    if attempt is None or attempt.state not in {"accepted", "uncertain"}:
        return
    if receipt.state not in {"accepted", "uncertain", "provider_delivered", "delivery_failed"}:
        raise ValueError("invalid_alert_receipt")
    if receipt.state != "uncertain":
        attempt.state = receipt.state
    if receipt.provider_id:
        attempt.provider_message_id = receipt.provider_id
    attempt.error_code = receipt.error_code
    if attempt.state in {"provider_delivered", "delivery_failed"} or attempt.receipt_attempts >= 12:
        attempt.next_receipt_at = None
        if attempt.state in {"accepted", "uncertain"}:
            attempt.error_code = "receipt_verification_exhausted"
    else:
        attempt.next_receipt_at = now + timedelta(
            seconds=min(3600, 30 * 2**attempt.receipt_attempts)
        )
    row = db.scalar(
        select(DiagnosticAlertDelivery)
        .where(DiagnosticAlertDelivery.id == attempt.delivery_id)
        .with_for_update()
    )
    if row and row.current_attempt_id == attempt.id and row.state in {"accepted", "uncertain"}:
        row.state = attempt.state
        row.provider_message_id = attempt.provider_message_id
        row.error_code = attempt.error_code
