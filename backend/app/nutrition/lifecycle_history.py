"""Transactional lifecycle observations for date-based nutrition charts.

Register once alongside model metadata. ORM transitions and visibility changes
are captured before flush; plan nutrient snapshots remain the source of truth.
Bulk lifecycle writes must explicitly call record_lifecycle.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.nutrition.models import NutritionWeeklyPlan


def record_lifecycle(
    db: Session, plan: NutritionWeeklyPlan, *, now: datetime | None = None
) -> None:
    from app.nutrition.models import NutritionPlanLifecycleEvent
    from app.profile.models import UserProfile

    current = now or datetime.now(UTC)
    with db.no_autoflush:
        profile = db.get(UserProfile, plan.user_id)
        zone = profile.timezone if profile else "Asia/Tehran"
    db.add(
        NutritionPlanLifecycleEvent(
            user_id=plan.user_id,
            plan_id=plan.id,
            plan=plan,
            lifecycle_status=str(plan.lifecycle_status),
            is_user_visible=plan.is_user_visible if plan.is_user_visible is not None else True,
            start_date=plan.start_date,
            effective_on=current.astimezone(ZoneInfo(zone)).date(),
            occurred_at=current,
            source="transition",
        )
    )
    # Avoid duplicate events if an explicit transition is followed by an ORM flush.
    db.info.setdefault("nutrition_lifecycle_recorded", {})[id(plan)] = (
        str(plan.lifecycle_status),
        plan.is_user_visible,
        plan.start_date,
        plan.started_at,
    )


def _capture(db: Session, _context: Any, _instances: Any) -> None:
    from app.nutrition.models import NutritionWeeklyPlan

    recorded = db.info.setdefault("nutrition_lifecycle_recorded", {})
    for obj in list(db.new) + list(db.dirty):
        if not isinstance(obj, NutritionWeeklyPlan):
            continue
        if obj.id is None:
            obj.id = uuid4()
        state = inspect(obj)
        fields = ("lifecycle_status", "is_user_visible", "start_date", "started_at")
        if not any(state.attrs[field].history.has_changes() for field in fields):
            continue
        snapshot = (str(obj.lifecycle_status), obj.is_user_visible, obj.start_date, obj.started_at)
        if recorded.get(id(obj)) == snapshot:
            continue
        # started_at captures the actual activation timestamp (including tests).
        activation = state.attrs.started_at.history.has_changes() and obj.started_at is not None
        record_lifecycle(db, obj, now=obj.started_at if activation else None)


def _clear(db: Session) -> None:
    db.info.pop("nutrition_lifecycle_recorded", None)


def register_lifecycle_history() -> None:
    if not event.contains(Session, "before_flush", _capture):
        event.listen(Session, "before_flush", _capture)
        event.listen(Session, "after_commit", _clear)
        event.listen(Session, "after_rollback", _clear)
