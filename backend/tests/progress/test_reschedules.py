from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.progress.service import overview
from app.workout_cycles.models import WorkoutSessionRescheduleEvent
from app.workout_cycles.service import reschedule_current_cycle_session
from tests.workout_cycles.test_session_service import begin_cycle, make_plan, make_profile
from tests.workout_reviews.test_review_access import _user


def test_reschedule_records_real_shift_and_preserves_due_denominator(db):
    user = _user(db)
    make_profile(db, user.id)
    start = date(2026, 9, 26)
    cycle = begin_cycle(db, user.id, make_plan(db, user.id, weekdays=(0, 2, 4)), start)
    first = min(cycle.sessions, key=lambda s: s.scheduled_date)
    initial = first.scheduled_date
    current = datetime.combine(start, datetime.min.time(), UTC)
    for row in cycle.sessions:
        row.reschedule_history_started_at = current
    reschedule_current_cycle_session(
        db,
        user_id=user.id,
        session_id=first.id,
        scheduled_date=initial + timedelta(days=1),
        now=current,
    )
    events = list(
        db.scalars(
            select(WorkoutSessionRescheduleEvent).where(
                WorkoutSessionRescheduleEvent.session_id == first.id
            )
        )
    )
    assert len(events) == 1
    assert events[0].from_date == initial and events[0].to_date == initial + timedelta(days=1)
    result = overview(db, user.id, preset="week", timezone="UTC", now=current + timedelta(days=6))
    assert result.training.rescheduled_sessions == 1
    assert result.training.due_sessions == 3
    assert result.training.completed_sessions == 0
    assert result.training.adherence_percent == 0


def test_pre_history_period_does_not_claim_zero_reschedules(db):
    user = _user(db)
    make_profile(db, user.id)
    start = date(2026, 9, 26)
    cycle = begin_cycle(db, user.id, make_plan(db, user.id, weekdays=(0, 2, 4)), start)
    for session in cycle.sessions:
        session.created_at = datetime(2026, 9, 26, tzinfo=UTC)
    db.flush()
    result = overview(
        db, user.id, preset="week", timezone="UTC", now=datetime(2026, 10, 2, tzinfo=UTC)
    )
    assert result.training.rescheduled_sessions is None
