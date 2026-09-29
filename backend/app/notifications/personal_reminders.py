from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.nutrition.models import NutritionConsumptionEntry, NutritionDailyCheckIn
from app.profile.models import UserProfile
from app.program_timeline.schemas import ProgramTimelineTodayResponse
from app.program_timeline.service import build_program_timeline
from app.workout_cycles.models import WorkoutCycle, WorkoutCycleSession

from .inbox import publish_inbox_notification
from .models import NotificationInboxItem, NotificationOutboxEvent, NotificationPreference


def daily_due_at(now: datetime, timezone: str, clock: str | None) -> datetime | None:
    if clock is None:
        return None
    local = now.astimezone(ZoneInfo(timezone))
    hour, minute = map(int, clock.split(":"))
    due = local.replace(hour=hour, minute=minute, second=0, microsecond=0).astimezone(UTC)
    actual_local = due.astimezone(ZoneInfo(timezone))
    if (actual_local.hour, actual_local.minute) != (hour, minute):
        return None
    return due if timedelta(0) <= now - due <= timedelta(minutes=30) else None


def _timezone(db: Session, preference: NotificationPreference) -> str:
    return (
        preference.reminder_timezone
        or db.scalar(select(UserProfile.timezone).where(UserProfile.user_id == preference.user_id))
        or "Asia/Tehran"
    )


def _last_activity(
    db: Session, user_id: UUID, timeline: ProgramTimelineTodayResponse, timezone: str
) -> datetime | None:
    values = [
        db.scalar(
            select(func.max(WorkoutCycleSession.completed_at))
            .join(WorkoutCycle)
            .where(WorkoutCycle.user_id == user_id)
        ),
        db.scalar(
            select(func.max(NutritionDailyCheckIn.updated_at)).where(
                NutritionDailyCheckIn.user_id == user_id,
                NutritionDailyCheckIn.status != "not_recorded",
            )
        ),
        db.scalar(
            select(func.max(NutritionConsumptionEntry.created_at)).where(
                NutritionConsumptionEntry.user_id == user_id
            )
        ),
    ]
    for start in [timeline.workout.start_date, timeline.nutrition.start_date]:
        if start is not None:
            values.append(
                datetime.combine(start, datetime.min.time(), tzinfo=ZoneInfo(timezone)).astimezone(
                    UTC
                )
            )
    return max((value for value in values if value is not None), default=None)


def _eligible(
    db: Session, preference: NotificationPreference, event_type: str, now: datetime
) -> tuple[bool, dict[str, object]]:
    timezone = _timezone(db, preference)
    timeline = build_program_timeline(
        db, user_id=preference.user_id, timezone_name=timezone, now=now
    )
    data: dict[str, object] = {"local_date": timeline.local_date.isoformat()}
    if event_type == "training_reminder":
        session = (
            db.scalar(
                select(WorkoutCycleSession).where(
                    WorkoutCycleSession.cycle_id == timeline.workout.cycle_id,
                    WorkoutCycleSession.scheduled_date == timeline.local_date,
                    WorkoutCycleSession.status == "scheduled",
                )
            )
            if timeline.workout.cycle_id
            else None
        )
        if session is not None:
            data["session_id"] = str(session.id)
        return session is not None and timeline.workout.state in {
            "workout_today",
            "rest_day",
            "overdue",
        }, data
    if event_type == "nutrition_reminder":
        recorded = db.scalar(
            select(NutritionDailyCheckIn.id).where(
                NutritionDailyCheckIn.user_id == preference.user_id,
                NutritionDailyCheckIn.entry_date == timeline.local_date,
            )
        )
        return timeline.nutrition.state == "active" and recorded is None, data
    active = (
        timeline.workout.state
        in {"workout_today", "rest_day", "overdue", "completed_today", "legacy_cycle"}
        or timeline.nutrition.state == "active"
    )
    last = _last_activity(db, preference.user_id, timeline, timezone)
    previous = db.scalar(
        select(func.max(NotificationInboxItem.created_at)).where(
            NotificationInboxItem.user_id == preference.user_id,
            NotificationInboxItem.event_type == "return_reminder",
        )
    )
    return active and last is not None and now - last >= timedelta(days=7) and (
        previous is None or now - previous >= timedelta(days=7)
    ), data


def enqueue_personal_reminders(db: Session, *, now: datetime) -> int:
    preferences = db.scalars(
        select(NotificationPreference)
        .where(
            NotificationPreference.enabled.is_(True),
            or_(
                NotificationPreference.training_reminders.is_(True),
                NotificationPreference.nutrition_reminders.is_(True),
                NotificationPreference.return_reminders.is_(True),
            ),
        )
        .with_for_update(skip_locked=True)
    ).all()
    count = 0
    for preference in preferences:
        timezone = _timezone(db, preference)
        for event_type, category, clock in [
            ("training_reminder", "training_reminders", preference.training_time),
            ("nutrition_reminder", "nutrition_reminders", preference.nutrition_time),
            (
                "return_reminder",
                "return_reminders",
                preference.nutrition_time or preference.training_time or "09:00",
            ),
        ]:
            if not getattr(preference, category):
                continue
            due = daily_due_at(now, timezone, clock)
            if due is None:
                continue
            eligible, data = _eligible(db, preference, event_type, now)
            if not eligible:
                continue
            data["due_at"] = due.isoformat()
            key = f"personal:{event_type}:{data['local_date']}"
            existing = db.scalar(
                select(NotificationInboxItem.id).where(
                    NotificationInboxItem.user_id == preference.user_id,
                    NotificationInboxItem.deduplication_key == key,
                )
            )
            publish_inbox_notification(
                db, preference.user_id, event_type, category, key, data, due_at=due
            )
            count += int(existing is None)
    db.commit()
    return count


def personal_event_is_current(db: Session, event: NotificationOutboxEvent, now: datetime) -> bool:
    if event.category not in {"training_reminders", "nutrition_reminders", "return_reminders"}:
        return True
    preference = db.get(NotificationPreference, event.user_id)
    if preference is None or not preference.enabled or not getattr(preference, event.category):
        return False
    data = event.payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("due_at"), str):
        return False
    due = datetime.fromisoformat(data["due_at"])
    if not timedelta(0) <= now - due <= timedelta(minutes=30):
        return False
    clock = (
        preference.training_time
        if event.category == "training_reminders"
        else preference.nutrition_time
    )
    if event.category == "return_reminders":
        clock = preference.nutrition_time or preference.training_time or "09:00"
    if daily_due_at(now, _timezone(db, preference), clock) != due:
        return False
    if event.category == "return_reminders":
        timezone = _timezone(db, preference)
        timeline = build_program_timeline(
            db, user_id=preference.user_id, timezone_name=timezone, now=now
        )
        last = _last_activity(db, preference.user_id, timeline, timezone)
        return (
            (
                timeline.workout.state
                in {"workout_today", "rest_day", "overdue", "completed_today", "legacy_cycle"}
                or timeline.nutrition.state == "active"
            )
            and last is not None
            and now - last >= timedelta(days=7)
        )
    eligible, fresh = _eligible(db, preference, event.event_type, now)
    return eligible and fresh["local_date"] == data.get("local_date")
