from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.exercises.enums import MuscleGroup
from app.profile.enums import FitnessGoal, Sex, TrainingLocation
from app.profile.models import BodyMeasurement, UserProfile
from app.program_timeline.service import build_program_timeline
from app.workout_cycles.enums import WorkoutCycleSessionStatus
from app.workout_cycles.models import WorkoutCycle, WorkoutCycleSession
from app.workout_cycles.service import (
    WorkoutCycleAlreadyStartedError,
    WorkoutCycleSessionAlreadyFinishedError,
    WorkoutCycleSessionBeforeStartError,
    WorkoutCycleSessionDateConflictError,
    WorkoutCycleSessionNotFoundError,
    complete_current_cycle_session,
    get_current_active_cycle_for_user,
    reschedule_current_cycle_session,
    skip_current_cycle_session,
    start_cycle,
)
from app.workouts.enums import WorkoutPlanStatus
from app.workouts.models import WorkoutDay, WorkoutPlan


def make_user(db: Session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.flush()
    return user


def make_profile(db: Session, user_id: UUID) -> None:
    db.add(
        UserProfile(
            user_id=user_id,
            display_name="Session Athlete",
            birth_date=date(1995, 1, 1),
            sex=Sex.MALE,
            height_cm=180,
            fitness_goal=FitnessGoal.BUILD_MUSCLE,
            experience_level="beginner",
            training_days_per_week=4,
            preferred_weekdays=[0, 2, 4, 6],
            priority_muscles=[MuscleGroup.BACK.value],
            training_location=TrainingLocation.GYM,
            session_duration_minutes=60,
            plan_duration_weeks=4,
        )
    )
    db.add(BodyMeasurement(user_id=user_id, weight_kg=Decimal("80")))
    db.flush()


def make_plan(
    db: Session,
    user_id: UUID,
    *,
    weekdays: tuple[int | None, ...],
    duration_weeks: int = 4,
    profile_weekdays: list[int] | None = None,
) -> WorkoutPlan:
    snapshot: dict[str, object] = {"plan_duration_weeks": duration_weeks}
    if profile_weekdays is not None:
        snapshot["preferred_weekdays"] = profile_weekdays
    plan = WorkoutPlan(
        user_id=user_id,
        status=WorkoutPlanStatus.ACTIVE,
        generation_signature="a" * 64,
        profile_snapshot=snapshot,
        provider="fake",
        model_id="fake-model",
        prompt_version="v1",
        generation_policy_version="v1",
        candidate_set_hash="b" * 64,
        generation_method="coach_review",
    )
    plan.days = [
        WorkoutDay(
            day_number=index,
            title_en=f"Day {index}",
            title_fa=f"روز {index}",
            estimated_duration_minutes=45,
            weekday=weekday,
        )
        for index, weekday in enumerate(weekdays, start=1)
    ]
    db.add(plan)
    db.flush()
    return plan


def begin_cycle(
    db: Session,
    user_id: UUID,
    plan: WorkoutPlan,
    start_date: date = date(2026, 9, 12),
) -> WorkoutCycle:
    return start_cycle(
        db,
        user_id=user_id,
        workout_plan_id=plan.id,
        start_date=start_date,
        timezone_name="UTC",
    )


def test_start_cycle_on_workout_day_creates_today_session(db: Session) -> None:
    user = make_user(db, "session-day@example.com")
    plan = make_plan(db, user.id, weekdays=(0, 2))

    cycle = begin_cycle(db, user.id, plan)

    assert cycle.started_at.date() == date(2026, 9, 12)
    assert cycle.start_date == date(2026, 9, 12)
    assert cycle.start_timezone == "UTC"
    assert cycle.sessions[0].scheduled_date == date(2026, 9, 12)
    assert cycle.sessions[0].session_number == 1


def test_start_cycle_on_rest_day_does_not_force_first_session(db: Session) -> None:
    user = make_user(db, "session-rest@example.com")
    plan = make_plan(db, user.id, weekdays=(2,))

    cycle = begin_cycle(db, user.id, plan, date(2026, 9, 13))

    assert all(session.scheduled_date != date(2026, 9, 13) for session in cycle.sessions)
    assert cycle.sessions[0].scheduled_date == date(2026, 9, 14)
    assert cycle.sessions[0].session_number == 1


def test_four_day_plan_repeats_for_each_program_week(db: Session) -> None:
    user = make_user(db, "session-four-day@example.com")
    plan = make_plan(db, user.id, weekdays=(0, 2, 4, 6), duration_weeks=4)

    cycle = begin_cycle(db, user.id, plan)
    sessions = sorted(cycle.sessions, key=lambda item: item.session_number)

    assert len(sessions) == 16
    assert [session.week_number for session in sessions[:4]] == [1, 1, 1, 1]
    assert [session.week_number for session in sessions[4:8]] == [2, 2, 2, 2]
    assert sessions[4].scheduled_date == sessions[0].scheduled_date + timedelta(days=7)
    assert sessions[8].scheduled_date == sessions[0].scheduled_date + timedelta(days=14)


def test_fitician_weekday_zero_is_saturday(db: Session) -> None:
    user = make_user(db, "session-saturday@example.com")
    plan = make_plan(db, user.id, weekdays=(0,))

    cycle = begin_cycle(db, user.id, plan, date(2026, 9, 11))

    assert cycle.sessions[0].scheduled_date == date(2026, 9, 12)


def test_missing_weekdays_use_valid_profile_snapshot_fallback(db: Session) -> None:
    user = make_user(db, "session-profile-fallback@example.com")
    plan = make_plan(
        db,
        user.id,
        weekdays=(None, None),
        profile_weekdays=[1, 3],
    )

    cycle = begin_cycle(db, user.id, plan, date(2026, 9, 13))

    assert [session.scheduled_date for session in cycle.sessions[:2]] == [
        date(2026, 9, 13),
        date(2026, 9, 15),
    ]


def test_missing_weekdays_use_existing_engine_default_fallback(db: Session) -> None:
    user = make_user(db, "session-default-fallback@example.com")
    plan = make_plan(db, user.id, weekdays=(None, None, None, None))

    cycle = begin_cycle(db, user.id, plan)

    assert [session.scheduled_date for session in cycle.sessions[:4]] == [
        date(2026, 9, 12),
        date(2026, 9, 13),
        date(2026, 9, 15),
        date(2026, 9, 16),
    ]


def test_complete_session_transition_is_idempotently_rejected_after_finish(
    db: Session,
) -> None:
    user = make_user(db, "session-complete@example.com")
    plan = make_plan(db, user.id, weekdays=(0,))
    cycle = begin_cycle(db, user.id, plan)
    session = cycle.sessions[0]

    completed = complete_current_cycle_session(db, user_id=user.id, session_id=session.id)

    assert completed.status is WorkoutCycleSessionStatus.COMPLETED
    assert completed.completed_at is not None
    with pytest.raises(WorkoutCycleSessionAlreadyFinishedError):
        complete_current_cycle_session(db, user_id=user.id, session_id=session.id)


def test_skip_session_transition_sets_skipped_timestamp(db: Session) -> None:
    user = make_user(db, "session-skip@example.com")
    plan = make_plan(db, user.id, weekdays=(0,))
    cycle = begin_cycle(db, user.id, plan)

    skipped = skip_current_cycle_session(db, user_id=user.id, session_id=cycle.sessions[0].id)

    assert skipped.status is WorkoutCycleSessionStatus.SKIPPED
    assert skipped.skipped_at is not None


def test_reschedule_session_moves_only_unfinished_session(db: Session) -> None:
    user = make_user(db, "session-reschedule@example.com")
    plan = make_plan(db, user.id, weekdays=(0, 2))
    cycle = begin_cycle(db, user.id, plan)
    session = cycle.sessions[0]

    moved = reschedule_current_cycle_session(
        db,
        user_id=user.id,
        session_id=session.id,
        scheduled_date=date(2026, 9, 13),
    )

    assert moved.scheduled_date == date(2026, 9, 13)
    assert moved.status is WorkoutCycleSessionStatus.SCHEDULED


def test_reschedule_rejects_collision_and_date_before_cycle_start(db: Session) -> None:
    user = make_user(db, "session-reschedule-errors@example.com")
    plan = make_plan(db, user.id, weekdays=(0, 2))
    cycle = begin_cycle(db, user.id, plan)
    first = cycle.sessions[0]
    complete_current_cycle_session(
        db,
        user_id=user.id,
        session_id=first.id,
        now=datetime(2026, 9, 12, 12, tzinfo=UTC),
    )
    session = cycle.sessions[1]

    with pytest.raises(WorkoutCycleSessionDateConflictError):
        reschedule_current_cycle_session(
            db,
            user_id=user.id,
            session_id=session.id,
            scheduled_date=first.scheduled_date,
        )
    with pytest.raises(WorkoutCycleSessionBeforeStartError):
        reschedule_current_cycle_session(
            db,
            user_id=user.id,
            session_id=session.id,
            scheduled_date=date(2026, 9, 11),
        )


def test_finished_session_cannot_be_rescheduled(db: Session) -> None:
    user = make_user(db, "session-finished-reschedule@example.com")
    plan = make_plan(db, user.id, weekdays=(0,))
    cycle = begin_cycle(db, user.id, plan)
    session = complete_current_cycle_session(db, user_id=user.id, session_id=cycle.sessions[0].id)

    with pytest.raises(WorkoutCycleSessionAlreadyFinishedError):
        reschedule_current_cycle_session(
            db,
            user_id=user.id,
            session_id=session.id,
            scheduled_date=date(2026, 9, 13),
        )


def test_legacy_cycle_has_no_manufactured_exact_sessions(db: Session) -> None:
    user = make_user(db, "session-legacy@example.com")
    plan = make_plan(db, user.id, weekdays=())
    cycle = WorkoutCycle(
        user_id=user.id,
        workout_plan_id=plan.id,
        duration_weeks=4,
    )
    db.add(cycle)
    db.flush()

    assert (
        db.scalars(
            select(WorkoutCycleSession).where(WorkoutCycleSession.cycle_id == cycle.id)
        ).all()
        == []
    )


def test_start_cycle_is_idempotent_for_same_date_and_conflicts_for_new_date(db: Session) -> None:
    user = make_user(db, "session-idempotency@example.com")
    plan = make_plan(db, user.id, weekdays=(0,))

    first = begin_cycle(db, user.id, plan)
    same = begin_cycle(db, user.id, plan)

    assert same.id == first.id
    with pytest.raises(WorkoutCycleAlreadyStartedError):
        begin_cycle(db, user.id, plan, date(2026, 9, 13))


def test_session_not_found_is_not_silent(db: Session) -> None:
    user = make_user(db, "session-not-found@example.com")

    with pytest.raises(WorkoutCycleSessionNotFoundError):
        complete_current_cycle_session(db, user_id=user.id, session_id=UUID(int=0))


def test_current_cycle_ignores_cycle_for_superseded_workout_plan(db: Session) -> None:
    user = make_user(db, "session-current-plan@example.com")
    old_plan = make_plan(db, user.id, weekdays=(0,))
    old_cycle = begin_cycle(db, user.id, old_plan)
    old_plan.status = WorkoutPlanStatus.SUPERSEDED
    new_plan = make_plan(db, user.id, weekdays=(2,))
    db.flush()

    assert old_cycle.workout_plan_id != new_plan.id
    assert get_current_active_cycle_for_user(db, user_id=user.id) is None


def test_start_cycle_idempotency_uses_immutable_logical_date_after_timezone_change(
    db: Session,
) -> None:
    user = make_user(db, "session-travel-idempotency@example.com")
    make_profile(db, user.id)
    plan = make_plan(db, user.id, weekdays=(0,))
    first = start_cycle(
        db,
        user_id=user.id,
        workout_plan_id=plan.id,
        start_date=date(2026, 9, 12),
        timezone_name="Asia/Tehran",
    )

    same = start_cycle(
        db,
        user_id=user.id,
        workout_plan_id=plan.id,
        start_date=date(2026, 9, 12),
        timezone_name="America/Los_Angeles",
    )

    assert same.id == first.id
    assert same.start_date == date(2026, 9, 12)
    assert same.start_timezone == "Asia/Tehran"


def test_future_and_later_unresolved_sessions_are_not_actionable(db: Session) -> None:
    user = make_user(db, "session-action-order@example.com")
    make_profile(db, user.id)
    plan = make_plan(db, user.id, weekdays=(1, 3))
    cycle = begin_cycle(db, user.id, plan, date(2026, 9, 20))

    with pytest.raises(ValueError, match="not actionable"):
        complete_current_cycle_session(
            db,
            user_id=user.id,
            session_id=cycle.sessions[0].id,
            now=datetime(2026, 9, 19, 12, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="not actionable"):
        skip_current_cycle_session(
            db,
            user_id=user.id,
            session_id=cycle.sessions[1].id,
            now=datetime(2026, 9, 23, 12, tzinfo=UTC),
        )


def test_resolving_actionable_session_advances_sequence(db: Session) -> None:
    user = make_user(db, "session-action-advance@example.com")
    make_profile(db, user.id)
    plan = make_plan(db, user.id, weekdays=(1, 3))
    cycle = begin_cycle(db, user.id, plan, date(2026, 9, 20))
    now = datetime(2026, 9, 23, 12, tzinfo=UTC)

    with pytest.raises(ValueError, match="not actionable"):
        complete_current_cycle_session(
            db, user_id=user.id, session_id=cycle.sessions[1].id, now=now
        )
    complete_current_cycle_session(db, user_id=user.id, session_id=cycle.sessions[0].id, now=now)
    completed = complete_current_cycle_session(
        db, user_id=user.id, session_id=cycle.sessions[1].id, now=now
    )

    assert completed.status is WorkoutCycleSessionStatus.COMPLETED


def test_do_today_cascades_later_unresolved_sessions_and_preserves_spacing(
    db: Session,
) -> None:
    user = make_user(db, "session-do-today@example.com")
    make_profile(db, user.id)
    plan = make_plan(db, user.id, weekdays=(2, 4, 6))
    cycle = begin_cycle(db, user.id, plan, date(2026, 9, 13))
    sessions = sorted(cycle.sessions, key=lambda item: item.session_number)

    moved = reschedule_current_cycle_session(
        db,
        user_id=user.id,
        session_id=sessions[0].id,
        scheduled_date=date(2026, 9, 16),
        now=datetime(2026, 9, 16, 12, tzinfo=UTC),
    )

    assert moved.scheduled_date == date(2026, 9, 16)
    assert [item.scheduled_date for item in sessions[:4]] == [
        date(2026, 9, 16),
        date(2026, 9, 18),
        date(2026, 9, 20),
        date(2026, 9, 23),
    ]
    timeline = build_program_timeline(
        db,
        user_id=user.id,
        now=datetime(2026, 9, 16, 12, tzinfo=UTC),
    )
    assert timeline.workout.state.value == "workout_today"
    assert timeline.workout.today_session is not None
    assert timeline.workout.today_session.id == sessions[0].id


def test_cascade_never_rewrites_finished_sessions(db: Session) -> None:
    user = make_user(db, "session-cascade-history@example.com")
    make_profile(db, user.id)
    plan = make_plan(db, user.id, weekdays=(1, 3, 5))
    cycle = begin_cycle(db, user.id, plan, date(2026, 9, 13))
    sessions = sorted(cycle.sessions, key=lambda item: item.session_number)
    complete_current_cycle_session(
        db,
        user_id=user.id,
        session_id=sessions[0].id,
        now=datetime(2026, 9, 15, 12, tzinfo=UTC),
    )
    first_date = sessions[0].scheduled_date

    reschedule_current_cycle_session(
        db,
        user_id=user.id,
        session_id=sessions[1].id,
        scheduled_date=date(2026, 9, 25),
        now=datetime(2026, 9, 16, 12, tzinfo=UTC),
    )

    assert sessions[0].status is WorkoutCycleSessionStatus.COMPLETED
    assert sessions[0].scheduled_date == first_date
    assert sessions[1].scheduled_date == date(2026, 9, 25)
    assert sessions[2].scheduled_date == date(2026, 9, 27)
    unresolved_dates = [
        item.scheduled_date
        for item in sessions
        if item.status is WorkoutCycleSessionStatus.SCHEDULED
    ]
    assert len(unresolved_dates) == len(set(unresolved_dates))
