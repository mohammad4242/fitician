from datetime import UTC, datetime

from app.notifications.personal_reminders import daily_due_at
from tests.workout_reviews.test_review_access import _login, _user

ORIGIN = {"Origin": "http://localhost:5173"}


def test_reminder_window_uses_local_time_without_replaying_missed_days():
    assert daily_due_at(
        datetime(2026, 9, 29, 5, 35, tzinfo=UTC), "Asia/Tehran", "09:00"
    ) == datetime(2026, 9, 29, 5, 30, tzinfo=UTC)
    assert daily_due_at(datetime(2026, 9, 29, 5, 29, tzinfo=UTC), "Asia/Tehran", "09:00") is None
    assert daily_due_at(datetime(2026, 9, 29, 6, 1, tzinfo=UTC), "Asia/Tehran", "09:00") is None


def test_web_can_configure_opt_in_reminders_and_old_clients_preserve_them(
    client, db, test_settings
):
    member = _user(db)
    _login(client, db, test_settings, member)
    response = client.get("/api/v1/notifications/preferences")
    assert response.status_code == 200
    settings = response.json()
    assert settings["training_reminders"] is False
    assert settings["nutrition_reminders"] is False
    settings.pop("updated_at")
    settings.update(training_reminders=True, training_time="18:30", reminder_timezone="Asia/Tehran")
    assert (
        client.put("/api/v1/notifications/preferences", headers=ORIGIN, json=settings).status_code
        == 200
    )
    for key in [
        "messages",
        "training_reminders",
        "nutrition_reminders",
        "return_reminders",
        "training_time",
        "nutrition_time",
        "reminder_timezone",
    ]:
        settings.pop(key)
    assert (
        client.put("/api/v1/notifications/preferences", headers=ORIGIN, json=settings).json()[
            "training_reminders"
        ]
        is True
    )
    assert client.get("/api/v1/notifications/inbox").json()["items"] == []


def test_scheduler_deduplicates_and_cancels_completed_workouts(db):
    from datetime import date

    from sqlalchemy import select

    from app.notifications.models import (
        NotificationInboxItem,
        NotificationOutboxEvent,
        NotificationPreference,
    )
    from app.notifications.personal_reminders import (
        enqueue_personal_reminders,
        personal_event_is_current,
    )
    from app.workout_cycles.models import WorkoutCycleSession
    from tests.program_timeline.test_service import _cycle, _profile, _user, _workout_plan

    member = _user(db, "reminder-test@example.com")
    _profile(db, member.id)
    plan = _workout_plan(db, member.id, (1,))
    cycle = _cycle(db, member.id, plan, start_date=date(2026, 9, 29))
    db.add(
        NotificationPreference(
            user_id=member.id,
            training_reminders=True,
            training_time="09:00",
            reminder_timezone="UTC",
        )
    )
    db.commit()
    first = db.scalar(
        select(WorkoutCycleSession)
        .where(WorkoutCycleSession.cycle_id == cycle.id)
        .order_by(WorkoutCycleSession.session_number)
    )
    first.scheduled_date = date(2026, 9, 29)
    db.commit()
    now = datetime(2026, 9, 29, 9, 5, tzinfo=UTC)
    assert enqueue_personal_reminders(db, now=now) == 1
    assert enqueue_personal_reminders(db, now=now) == 0
    assert len(db.scalars(select(NotificationInboxItem)).all()) == 1
    event = db.scalar(select(NotificationOutboxEvent))
    assert personal_event_is_current(db, event, now) is True
    session = db.scalar(
        select(WorkoutCycleSession).where(
            WorkoutCycleSession.cycle_id == cycle.id,
            WorkoutCycleSession.scheduled_date == date(2026, 9, 29),
        )
    )
    session.status = "completed"
    session.completed_at = now
    db.flush()
    assert personal_event_is_current(db, event, now) is False
    assert enqueue_personal_reminders(db, now=datetime(2026, 9, 29, 11, tzinfo=UTC)) == 0


def test_missing_local_time_during_dst_is_not_replayed_later():
    assert (
        daily_due_at(datetime(2026, 3, 8, 7, 35, tzinfo=UTC), "America/New_York", "02:30") is None
    )


def test_return_reminder_requires_seven_days_and_is_weekly(db):
    from datetime import date, timedelta

    from sqlalchemy import select

    from app.notifications.models import NotificationInboxItem, NotificationPreference
    from app.notifications.personal_reminders import enqueue_personal_reminders
    from tests.program_timeline.test_service import _cycle, _profile, _user, _workout_plan

    member = _user(db, "return-reminder@example.com")
    _profile(db, member.id)
    plan = _workout_plan(db, member.id, (1,), duration_weeks=4)
    _cycle(db, member.id, plan, start_date=date(2026, 9, 1))
    db.add(
        NotificationPreference(user_id=member.id, return_reminders=True, reminder_timezone="UTC")
    )
    db.commit()
    early = datetime(2026, 9, 7, 9, 5, tzinfo=UTC)
    assert enqueue_personal_reminders(db, now=early) == 0
    first = early + timedelta(days=1)
    assert enqueue_personal_reminders(db, now=first) == 1
    item = db.scalar(select(NotificationInboxItem))
    item.created_at = first
    db.commit()
    assert enqueue_personal_reminders(db, now=first + timedelta(days=1)) == 0
    assert enqueue_personal_reminders(db, now=first + timedelta(days=7)) == 1


def test_nutrition_reminder_is_cancelled_after_daily_checkin(client, db):
    from datetime import date

    from sqlalchemy import select

    from app.notifications.models import NotificationOutboxEvent, NotificationPreference
    from app.notifications.personal_reminders import (
        enqueue_personal_reminders,
        personal_event_is_current,
    )
    from app.nutrition.enums import NutritionPlanLifecycleStatus
    from app.nutrition.models import NutritionDailyCheckIn
    from tests.program_timeline.test_service import _nutrition_plan, _set_nutrition_state

    plan = _nutrition_plan(client, db)
    _set_nutrition_state(db, plan, NutritionPlanLifecycleStatus.ACTIVE, start_date=date(2026, 9, 1))
    db.add(
        NotificationPreference(
            user_id=plan.user_id,
            nutrition_reminders=True,
            nutrition_time="09:00",
            reminder_timezone="UTC",
        )
    )
    db.commit()
    now = datetime(2026, 9, 29, 9, 5, tzinfo=UTC)
    assert enqueue_personal_reminders(db, now=now) == 1
    event = db.scalar(
        select(NotificationOutboxEvent).where(
            NotificationOutboxEvent.event_type == "nutrition_reminder"
        )
    )
    assert personal_event_is_current(db, event, now)
    db.add(
        NutritionDailyCheckIn(user_id=plan.user_id, entry_date=date(2026, 9, 29), status="on_plan")
    )
    db.flush()
    assert not personal_event_is_current(db, event, now)
