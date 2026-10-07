from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.user_activity.models import UserActivityEvent

EVENT_METADATA: dict[str, frozenset[str]] = {
    "auth.registered": frozenset({"platform", "auth_method", "app_version", "device_name"}),
    "auth.login_succeeded": frozenset({"platform", "auth_method", "app_version", "device_name"}),
    "profile.completed": frozenset(),
    "profile.updated": frozenset({"field_group"}),
    "workout.plan_generated": frozenset({"primary_goal", "training_days"}),
    "workout.plan_started": frozenset(),
    "workout.session_completed": frozenset({"week_number", "session_number"}),
    "workout.session_skipped": frozenset({"week_number", "session_number"}),
    "workout.weekly_checkin": frozenset({"week_number"}),
    "nutrition.plan_generated": frozenset({"revision"}),
    "nutrition.plan_started": frozenset(),
    "nutrition.daily_checkin": frozenset({"date"}),
    "body.measurement_recorded": frozenset({"weight_kg", "waist_cm", "hip_cm", "shoulder_cm"}),
    "body_analysis.completed": frozenset({"revision"}),
    "billing.order_paid": frozenset({"offer_code"}),
    "support.ticket_created": frozenset({"category"}),
}
_MAX_STRING_LENGTH = 128


class UnsafeActivityMetadataError(ValueError):
    pass


def _safe_metadata(
    event_type: str, metadata: dict[str, Any] | None
) -> dict[str, str | int | float | bool]:
    if event_type not in EVENT_METADATA:
        raise UnsafeActivityMetadataError("Unsupported activity event type")
    metadata = metadata or {}
    allowed = EVENT_METADATA[event_type]
    if set(metadata) - allowed:
        raise UnsafeActivityMetadataError("Metadata contains unsupported fields")
    result: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if key == "platform" and (
            not isinstance(value, str) or value not in {"web", "android", "ios"}
        ):
            raise UnsafeActivityMetadataError("Unsupported authentication platform")
        if key == "auth_method" and (
            not isinstance(value, str)
            or value not in {"password", "google", "apple", "phone_otp"}
        ):
            raise UnsafeActivityMetadataError("Unsupported authentication method")
        if isinstance(value, str):
            if len(value) > _MAX_STRING_LENGTH:
                raise UnsafeActivityMetadataError("Metadata string is too long")
        elif isinstance(value, int) and not isinstance(value, bool):
            if abs(value) > 2**53:
                raise UnsafeActivityMetadataError("Metadata number is out of bounds")
        elif isinstance(value, float):
            if not isfinite(value) or abs(value) > 1_000_000_000:
                raise UnsafeActivityMetadataError("Metadata number is out of bounds")
        elif not isinstance(value, bool):
            raise UnsafeActivityMetadataError("Metadata values must be bounded scalars")
        result[key] = value
    return result


def record_activity(
    db: Session,
    user_id: UUID,
    event_type: str,
    *,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
    deduplication_key: str | None = None,
) -> UserActivityEvent:
    safe = _safe_metadata(event_type, metadata)
    if resource_type is not None and len(resource_type) > 64:
        raise UnsafeActivityMetadataError("Resource type is too long")
    if resource_id is not None and len(resource_id) > 128:
        raise UnsafeActivityMetadataError("Resource id is too long")
    if deduplication_key is not None and len(deduplication_key) > 200:
        raise UnsafeActivityMetadataError("Deduplication key is too long")
    timestamp = occurred_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise UnsafeActivityMetadataError("occurred_at must be timezone-aware")
    values = dict(
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=safe,
        occurred_at=timestamp,
        deduplication_key=deduplication_key,
    )
    if deduplication_key is None:
        event = UserActivityEvent(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            safe_metadata=safe,
            occurred_at=timestamp,
        )
        db.add(event)
        db.flush()
        return event
    table = cast(Table, UserActivityEvent.__table__)
    statement = (
        insert(table)
        .values(id=uuid4(), **values)
        .on_conflict_do_nothing(constraint="uq_user_activity_events_deduplication_key")
        .returning(table.c.id)
    )
    event_id = db.execute(statement).scalar_one_or_none()
    if event_id is None:
        existing_event = db.scalar(
            select(UserActivityEvent).where(
                UserActivityEvent.deduplication_key == deduplication_key
            )
        )
        assert existing_event is not None
        if (
            existing_event.user_id != user_id
            or existing_event.event_type != event_type
            or existing_event.resource_type != resource_type
            or existing_event.resource_id != resource_id
        ):
            raise UnsafeActivityMetadataError("Deduplication key is already used by another event")
        return existing_event
    return db.get(UserActivityEvent, event_id)  # type: ignore[return-value]
