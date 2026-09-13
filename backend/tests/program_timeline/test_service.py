from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.models import User
from app.exercises.enums import MuscleGroup
from app.nutrition.enums import NutritionPlanLifecycleStatus
from app.nutrition.models import NutritionWeeklyPlan
from app.profile.enums import FitnessGoal, Sex, TrainingLocation
from app.profile.models import BodyMeasurement, UserProfile
from app.program_timeline.service import build_program_timeline
from app.workout_cycles.enums import WorkoutCycleStatus
from app.workout_cycles.models import WorkoutCycle
from app.workout_cycles.service import complete_current_cycle_session, start_cycle
from app.workouts.enums import WorkoutPlanStatus
from app.workouts.models import WorkoutDay, WorkoutPlan
from tests.nutrition.test_clinical_review_api import _member_plan


def _user(db: Session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.flush()
    return user


def _profile(db: Session, user_id: UUID, *, timezone: str = "UTC") -> None:
    db.add(
        UserProfile(
            user_id=user_id,
            timezone=timezone,
            display_name="Timeline Athlete",
            birth_date=date(1995, 1, 1),
            sex=Sex.MALE,
            height_cm=180,
            fitness_goal=FitnessGoal.BUILD_MUSCLE,
            experience_level="beginner",
            training_days_per_week=3,
            preferred_weekdays=[1, 2, 4],
            priority_muscles=[MuscleGroup.BACK.value],
            training_location=TrainingLocation.GYM,
            session_duration_minutes=60,
            plan_duration_weeks=4,
        )
    )
    db.add(BodyMeasurement(user_id=user_id, weight_kg=Decimal("80")))
    db.flush()


def _workout_plan(
    db: Session,
    user_id: UUID,
    weekdays: tuple[int, ...],
    *,
    duration_weeks: int = 4,
) -> WorkoutPlan:
    plan = WorkoutPlan(
        user_id=user_id,
        status=WorkoutPlanStatus.ACTIVE,
        generation_signature="a" * 64,
        profile_snapshot={"plan_duration_weeks": duration_weeks},
        provider="fake",
        model_id="fake-model",
        prompt_version="v1",
        generation_policy_version="v1",
        candidate_set_hash="b" * 64,
        generation_method="deterministic",
        days=[
            WorkoutDay(
                day_number=index,
                title_en=f"Day {index}",
                title_fa=f"روز {index}",
                estimated_duration_minutes=45,
                weekday=weekday,
            )
            for index, weekday in enumerate(weekdays, start=1)
        ],
    )
    db.add(plan)
    db.flush()
    return plan


def _cycle(
    db: Session,
    user_id: UUID,
    plan: WorkoutPlan,
    start_date: date = date(2026, 9, 13),
    timezone_name: str = "UTC",
) -> WorkoutCycle:
    return start_cycle(
        db,
        user_id=user_id,
        workout_plan_id=plan.id,
        start_date=start_date,
        timezone_name=timezone_name,
    )


def _nutrition_plan(client, db: Session) -> NutritionWeeklyPlan:
    response = _member_plan(client, db)
    plan = db.get(NutritionWeeklyPlan, response["id"])
    assert plan is not None
    return plan


def _set_nutrition_state(
    db: Session,
    plan: NutritionWeeklyPlan,
    status: NutritionPlanLifecycleStatus,
    *,
    start_date: date,
) -> None:
    if plan.review is not None:
        db.delete(plan.review)
        plan.review = None
    plan.lifecycle_status = status
    plan.start_date = start_date
    for day in plan.days:
        day.plan_date = start_date + timedelta(days=day.day_index)
    db.flush()


def test_workout_no_plan_and_ready_to_start_states(client, db: Session) -> None:
    user = _user(db, "timeline-no-plan@example.com")
    no_plan = build_program_timeline(db, user_id=user.id, now=datetime(2026, 9, 13, tzinfo=UTC))
    assert no_plan.workout.state.value == "no_plan"

    plan = _workout_plan(db, user.id, (1,))
    ready = build_program_timeline(db, user_id=user.id, now=datetime(2026, 9, 13, tzinfo=UTC))
    assert ready.workout.state.value == "ready_to_start"
    assert ready.workout.workout_plan_id == plan.id


def test_workout_scheduled_today_and_rest_day_use_real_sessions(db: Session) -> None:
    user = _user(db, "timeline-workout-day@example.com")
    _profile(db, user.id)
    sunday_plan = _workout_plan(db, user.id, (1,))
    cycle = _cycle(db, user.id, sunday_plan)

    today = build_program_timeline(db, user_id=user.id, now=datetime(2026, 9, 13, 12, tzinfo=UTC))
    assert today.workout.state.value == "workout_today"
    assert today.workout.today_session is not None
    assert today.workout.today_session.workout_day_id == sunday_plan.days[0].id

    cycle.status = WorkoutCycleStatus.COMPLETED
    cycle.completed_at = datetime(2026, 9, 13, 13, tzinfo=UTC)
    db.flush()
    completed = build_program_timeline(
        db, user_id=user.id, now=datetime(2026, 9, 13, 12, tzinfo=UTC)
    )
    assert completed.workout.state.value == "cycle_completed"


def test_workout_rest_day_points_to_next_future_session(db: Session) -> None:
    user = _user(db, "timeline-rest@example.com")
    _profile(db, user.id)
    plan = _workout_plan(db, user.id, (2,))
    _cycle(db, user.id, plan)

    timeline = build_program_timeline(
        db, user_id=user.id, now=datetime(2026, 9, 13, 12, tzinfo=UTC)
    )

    assert timeline.workout.state.value == "rest_day"
    assert timeline.workout.today_session is None
    assert timeline.workout.next_session is not None
    assert timeline.workout.next_session.scheduled_date == date(2026, 9, 14)
    assert timeline.workout.next_session.session_number == 1


def test_workout_overdue_has_priority_over_later_sessions(db: Session) -> None:
    user = _user(db, "timeline-overdue@example.com")
    _profile(db, user.id)
    plan = _workout_plan(db, user.id, (2, 4, 6))
    _cycle(db, user.id, plan)

    timeline = build_program_timeline(
        db, user_id=user.id, now=datetime(2026, 9, 17, 12, tzinfo=UTC)
    )

    assert timeline.workout.state.value == "overdue"
    assert timeline.workout.overdue_session is not None
    assert timeline.workout.overdue_session.scheduled_date == date(2026, 9, 14)
    assert timeline.workout.overdue_session.session_number == 1


def test_completed_today_exposes_next_future_session(db: Session) -> None:
    user = _user(db, "timeline-completed@example.com")
    _profile(db, user.id)
    plan = _workout_plan(db, user.id, (1, 2))
    cycle = _cycle(db, user.id, plan)
    complete_current_cycle_session(db, user_id=user.id, session_id=cycle.sessions[0].id)

    timeline = build_program_timeline(
        db, user_id=user.id, now=datetime(2026, 9, 13, 12, tzinfo=UTC)
    )

    assert timeline.workout.state.value == "completed_today"
    assert timeline.workout.next_session is not None
    assert timeline.workout.next_session.scheduled_date == date(2026, 9, 14)


def test_legacy_cycle_is_neutral_and_cycle_completed_is_explicit(db: Session) -> None:
    user = _user(db, "timeline-legacy@example.com")
    _profile(db, user.id)
    plan = _workout_plan(db, user.id, (1,))
    legacy = WorkoutCycle(
        user_id=user.id,
        workout_plan_id=plan.id,
        duration_weeks=4,
        started_at=datetime(2026, 9, 13, tzinfo=UTC),
    )
    db.add(legacy)
    db.flush()

    timeline = build_program_timeline(
        db, user_id=user.id, now=datetime(2026, 9, 15, 12, tzinfo=UTC)
    )
    assert timeline.workout.state.value == "legacy_cycle"
    assert timeline.workout.overdue_session is None

    legacy.status = WorkoutCycleStatus.COMPLETED
    legacy.completed_at = datetime(2026, 9, 15, 13, tzinfo=UTC)
    db.flush()
    completed = build_program_timeline(
        db, user_id=user.id, now=datetime(2026, 9, 15, 12, tzinfo=UTC)
    )
    assert completed.workout.state.value == "cycle_completed"


def test_scheduled_workout_cycle_uses_local_start_date(db: Session) -> None:
    user = _user(db, "timeline-scheduled@example.com")
    _profile(db, user.id, timezone="Asia/Tehran")
    plan = _workout_plan(db, user.id, (2,))
    _cycle(db, user.id, plan, date(2026, 9, 14), timezone_name="Asia/Tehran")

    timeline = build_program_timeline(
        db,
        user_id=user.id,
        now=datetime(2026, 9, 13, 21, tzinfo=UTC),
    )

    assert timeline.local_date == date(2026, 9, 14)
    assert timeline.workout.state.value == "workout_today"


def test_nutrition_timeline_states_and_recurring_day(client, db: Session) -> None:
    plan = _nutrition_plan(client, db)
    user_id = plan.user_id
    pending = build_program_timeline(db, user_id=user_id, now=datetime(2026, 9, 13, tzinfo=UTC))
    assert pending.nutrition.state.value == "pending_review"

    _set_nutrition_state(
        db, plan, NutritionPlanLifecycleStatus.READY_TO_START, start_date=date(2026, 9, 13)
    )
    ready = build_program_timeline(db, user_id=user_id, now=datetime(2026, 9, 13, tzinfo=UTC))
    assert ready.nutrition.state.value == "ready_to_start"

    _set_nutrition_state(
        db, plan, NutritionPlanLifecycleStatus.ACTIVE, start_date=date(2026, 9, 20)
    )
    scheduled = build_program_timeline(db, user_id=user_id, now=datetime(2026, 9, 13, tzinfo=UTC))
    assert scheduled.nutrition.state.value == "scheduled_start"

    _set_nutrition_state(db, plan, NutritionPlanLifecycleStatus.ACTIVE, start_date=date(2026, 9, 6))
    active = build_program_timeline(db, user_id=user_id, now=datetime(2026, 9, 13, tzinfo=UTC))
    assert active.nutrition.state.value == "active"
    assert active.nutrition.absolute_day_number == 8
    assert active.nutrition.pattern_day_index == 0
    assert active.nutrition.day_id == plan.days[0].id
