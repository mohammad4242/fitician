"""Bounded reconciliation of existing durable jobs, independent of process restarts."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.body_analysis.models import BodyAnalysis
from app.body_analysis.providers.models import ProviderErrorCode
from app.notifications.models import NotificationEventDelivery, NotificationOutboxEvent
from app.nutrition.models import NutritionFoodPhotoAnalysisJob, NutritionFoodPhotoEstimate
from app.observability.diagnostics_models import DiagnosticEvent
from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event

_KNOWN_CODES = {code.value for code in ProviderErrorCode} | {
    "TOKEN_UNAVAILABLE",
    "PROVIDER_UNAVAILABLE",
    "PROVIDER_ERROR",
    "INVALID_TOKEN",
    "TOKEN_OWNER_MISMATCH",
    "NOTIFICATION_NO_LONGER_DUE",
}


def reconcile_job_failures(db: Session) -> int:
    recorded = 0
    specifications: tuple[tuple[str, Any, str, str], ...] = (
        ("body_analysis", BodyAnalysis, "failed", "error_code"),
        ("food_photo", NutritionFoodPhotoAnalysisJob, "failed", "last_error_code"),
        ("notifications", NotificationEventDelivery, "dead_letter", "last_error"),
    )
    for component, model, failure_status, code_field in specifications:
        already_seen = (
            select(DiagnosticEvent.id)
            .where(
                DiagnosticEvent.resource_id == model.id,
                DiagnosticEvent.component == component,
                DiagnosticEvent.retry_count == model.attempt_count,
            )
            .exists()
        )
        jobs = db.scalars(
            select(model)
            .where(
                model.status == failure_status,
                model.created_at >= datetime.now(UTC) - timedelta(days=30),
                ~already_seen,
            )
            .order_by(model.created_at)
            .limit(100)
        ).all()
        for job in jobs:
            code = getattr(job, code_field, None)
            code = code if code in _KNOWN_CODES else "BACKGROUND_JOB_FAILED"
            # Expired/disabled device subscriptions are expected business outcomes.
            expected = code in {"TOKEN_UNAVAILABLE", "INVALID_TOKEN", "NOTIFICATION_NO_LONGER_DUE"}
            user_id = None
            correlation_id = getattr(job, "correlation_id", None)
            if component == "body_analysis":
                user_id = job.session.user_id
            elif component == "food_photo":
                user_id = db.scalar(
                    select(NutritionFoodPhotoEstimate.user_id).where(
                        NutritionFoodPhotoEstimate.id == job.estimate_id
                    )
                )
            elif component == "notifications":
                outbox = db.get(NotificationOutboxEvent, job.event_id)
                if outbox is not None:
                    user_id, correlation_id = outbox.user_id, outbox.correlation_id
            if correlation_id is not None and not re.fullmatch(
                r"[A-Za-z0-9_.:-]{1,128}", correlation_id
            ):
                correlation_id = None
            record_event(
                db,
                EventInput(
                    event_id=uuid5(
                        NAMESPACE_URL, f"fitician:job:{component}:{job.id}:{job.attempt_count}"
                    ),
                    component=component,
                    operation="background_job",
                    stage="terminal_failure",
                    platform="worker",
                    category="business_rejection" if expected else "job_failure",
                    severity="warning" if expected else "error",
                    error_code=code,
                    outcome="failure",
                    resource_id=job.id,
                    retry_count=min(job.attempt_count, 100),
                    request_id=correlation_id,
                ),
                user_id=user_id,
            )
            recorded += 1
    return recorded
