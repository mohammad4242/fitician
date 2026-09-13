from __future__ import annotations

from datetime import UTC, date, datetime
from numbers import Real
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.nutrition.calendar import (
    nutrition_absolute_day_number,
    nutrition_pattern_day_index,
)
from app.nutrition.enums import (
    NutritionPlanLifecycleStatus,
    NutritionPlanReviewStatus,
    NutritionPlanRole,
)
from app.nutrition.models import (
    NutritionPlanBundle,
    NutritionPlanGeneration,
    NutritionWeeklyPlan,
)
from app.profile.models import UserProfile
from app.program_timeline.schemas import (
    NutritionTimelineState,
    ProgramTimelineTodayResponse,
    TimelineNutritionResponse,
    TimelineWorkoutResponse,
    TimelineWorkoutSessionResponse,
    WorkoutTimelineState,
)
from app.time_context import local_date_for_timezone, validate_timezone_name
from app.workout_cycles.enums import WorkoutCycleSessionStatus, WorkoutCycleStatus
from app.workout_cycles.models import WorkoutCycle, WorkoutCycleSession
from app.workout_cycles.service import calculate_current_week
from app.workouts.enums import WorkoutPlanStatus
from app.workouts.models import WorkoutPlan

_PENDING_REVIEW_STATUSES = frozenset(
    {
        NutritionPlanLifecycleStatus.PENDING_PHYSICIAN_REVIEW,
        NutritionPlanLifecycleStatus.PHYSICIAN_REVIEW_IN_PROGRESS,
        NutritionPlanLifecycleStatus.AWAITING_LAB_INFORMATION,
        NutritionPlanLifecycleStatus.CHANGES_REQUESTED,
    }
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Program timeline timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _timeline_now(now: datetime | None) -> datetime:
    return _as_utc(now or datetime.now(UTC))


def _session_response(session: WorkoutCycleSession) -> TimelineWorkoutSessionResponse:
    day = session.workout_day
    return TimelineWorkoutSessionResponse(
        id=session.id,
        workout_day_id=session.workout_day_id,
        week_number=session.week_number,
        session_number=session.session_number,
        scheduled_date=session.scheduled_date,
        status=session.status,
        day_number=day.day_number,
        title_fa=day.title_fa,
        title_en=day.title_en,
        estimated_duration_minutes=day.estimated_duration_minutes,
    )


def _current_workout_cycle(
    db: Session,
    *,
    user_id: UUID,
) -> tuple[WorkoutPlan | None, WorkoutCycle | None]:
    plan = db.scalar(
        select(WorkoutPlan)
        .where(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.status == WorkoutPlanStatus.ACTIVE,
            WorkoutPlan.deleted_at.is_(None),
        )
        .options(selectinload(WorkoutPlan.days))
    )
    if plan is None:
        return None, None

    cycle = db.scalar(
        select(WorkoutCycle)
        .where(
            WorkoutCycle.user_id == user_id,
            WorkoutCycle.workout_plan_id == plan.id,
        )
        .options(selectinload(WorkoutCycle.sessions).selectinload(WorkoutCycleSession.workout_day))
        .order_by(WorkoutCycle.started_at.desc(), WorkoutCycle.id.desc())
    )
    return plan, cycle


def _workout_timeline(
    db: Session,
    *,
    user_id: UUID,
    timezone_name: str,
    local_date: date,
    now: datetime,
) -> TimelineWorkoutResponse:
    plan, cycle = _current_workout_cycle(db, user_id=user_id)
    if plan is None:
        return TimelineWorkoutResponse(state=WorkoutTimelineState.NO_PLAN)
    if cycle is None:
        return TimelineWorkoutResponse(
            state=WorkoutTimelineState.READY_TO_START,
            workout_plan_id=plan.id,
        )

    start_date = local_date_for_timezone(timezone_name, now=cycle.started_at)
    sessions = sorted(
        cycle.sessions,
        key=lambda session: (session.scheduled_date, session.session_number),
    )
    response_base = {
        "workout_plan_id": plan.id,
        "cycle_id": cycle.id,
        "start_date": start_date,
        "current_week": calculate_current_week(cycle.started_at, cycle.duration_weeks, now=now),
        "duration_weeks": cycle.duration_weeks,
        "completed_sessions": sum(
            session.status is WorkoutCycleSessionStatus.COMPLETED for session in sessions
        ),
        "total_sessions": len(sessions),
    }

    if start_date > local_date:
        return TimelineWorkoutResponse(
            state=WorkoutTimelineState.SCHEDULED_START,
            **response_base,
        )
    if cycle.status is WorkoutCycleStatus.COMPLETED:
        return TimelineWorkoutResponse(
            state=WorkoutTimelineState.CYCLE_COMPLETED,
            **response_base,
        )
    if not sessions:
        return TimelineWorkoutResponse(
            state=WorkoutTimelineState.LEGACY_CYCLE,
            **response_base,
        )

    unfinished = [
        session for session in sessions if session.status is WorkoutCycleSessionStatus.SCHEDULED
    ]
    overdue = next(
        (session for session in unfinished if session.scheduled_date < local_date),
        None,
    )
    today = next(
        (session for session in sessions if session.scheduled_date == local_date),
        None,
    )
    next_session = next(
        (session for session in unfinished if session.scheduled_date > local_date),
        None,
    )

    if overdue is not None:
        return TimelineWorkoutResponse(
            state=WorkoutTimelineState.OVERDUE,
            overdue_session=_session_response(overdue),
            next_session=_session_response(next_session) if next_session else None,
            today_session=_session_response(today) if today else None,
            **response_base,
        )
    if today is not None and today.status is WorkoutCycleSessionStatus.SCHEDULED:
        return TimelineWorkoutResponse(
            state=WorkoutTimelineState.WORKOUT_TODAY,
            today_session=_session_response(today),
            next_session=_session_response(next_session) if next_session else None,
            **response_base,
        )
    if today is not None and today.status is WorkoutCycleSessionStatus.COMPLETED:
        return TimelineWorkoutResponse(
            state=WorkoutTimelineState.COMPLETED_TODAY,
            today_session=_session_response(today),
            next_session=_session_response(next_session) if next_session else None,
            **response_base,
        )
    return TimelineWorkoutResponse(
        state=WorkoutTimelineState.REST_DAY,
        today_session=_session_response(today) if today else None,
        next_session=_session_response(next_session) if next_session else None,
        **response_base,
    )


def _latest_nutrition_plan(db: Session, *, user_id: UUID) -> NutritionWeeklyPlan | None:
    bundle = db.scalar(
        select(NutritionPlanBundle)
        .where(NutritionPlanBundle.user_id == user_id)
        .order_by(NutritionPlanBundle.created_at.desc())
        .limit(1)
    )
    if bundle is not None and bundle.selected_plan_id is not None:
        selected = db.scalar(
            _nutrition_plan_query().where(
                NutritionWeeklyPlan.id == bundle.selected_plan_id,
                NutritionWeeklyPlan.user_id == user_id,
                NutritionWeeklyPlan.is_user_visible.is_(True),
                NutritionPlanGeneration.plan_role != NutritionPlanRole.IDEAL_REFERENCE.value,
            )
        )
        if selected is not None:
            return selected

    return db.scalar(
        _nutrition_plan_query()
        .where(
            NutritionWeeklyPlan.user_id == user_id,
            NutritionWeeklyPlan.is_user_visible.is_(True),
            NutritionPlanGeneration.plan_role != NutritionPlanRole.IDEAL_REFERENCE.value,
        )
        .order_by(NutritionWeeklyPlan.revision.desc(), NutritionWeeklyPlan.created_at.desc())
        .limit(1)
    )


def _nutrition_plan_query():
    return (
        select(NutritionWeeklyPlan)
        .join(
            NutritionPlanGeneration,
            NutritionWeeklyPlan.generation_id == NutritionPlanGeneration.id,
        )
        .options(
            selectinload(NutritionWeeklyPlan.days),
            selectinload(NutritionWeeklyPlan.review),
            selectinload(NutritionWeeklyPlan.generation),
        )
    )


def _numeric_totals(raw: dict[str, object]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, Real) and not isinstance(value, bool):
            totals[key] = float(value)
        else:
            try:
                totals[key] = float(str(value))
            except (TypeError, ValueError):
                continue
    return totals


def _nutrition_timeline(
    db: Session,
    *,
    user_id: UUID,
    local_date: date,
) -> TimelineNutritionResponse:
    plan = _latest_nutrition_plan(db, user_id=user_id)
    if plan is None:
        return TimelineNutritionResponse(state=NutritionTimelineState.NO_PLAN)

    if (
        plan.lifecycle_status in _PENDING_REVIEW_STATUSES
        or plan.review is not None
        and plan.review.status is not NutritionPlanReviewStatus.APPROVED
    ):
        return TimelineNutritionResponse(
            state=NutritionTimelineState.PENDING_REVIEW,
            plan_id=plan.id,
            start_date=plan.start_date,
        )

    if plan.lifecycle_status is not NutritionPlanLifecycleStatus.ACTIVE:
        if plan.lifecycle_status in {
            NutritionPlanLifecycleStatus.GENERATED,
            NutritionPlanLifecycleStatus.PHYSICIAN_APPROVED,
            NutritionPlanLifecycleStatus.READY_TO_START,
        }:
            return TimelineNutritionResponse(
                state=NutritionTimelineState.READY_TO_START,
                plan_id=plan.id,
                start_date=plan.start_date,
            )
        return TimelineNutritionResponse(state=NutritionTimelineState.NO_PLAN)

    if plan.start_date > local_date:
        return TimelineNutritionResponse(
            state=NutritionTimelineState.SCHEDULED_START,
            plan_id=plan.id,
            start_date=plan.start_date,
        )

    pattern_index = nutrition_pattern_day_index(plan.start_date, local_date)
    day = next((day for day in plan.days if day.day_index == pattern_index), None)
    return TimelineNutritionResponse(
        state=NutritionTimelineState.ACTIVE,
        plan_id=plan.id,
        start_date=plan.start_date,
        absolute_day_number=nutrition_absolute_day_number(plan.start_date, local_date),
        pattern_day_index=pattern_index,
        day_id=day.id if day else None,
        nutrient_totals=_numeric_totals(day.nutrient_totals) if day else {},
    )


def build_program_timeline(
    db: Session,
    *,
    user_id: UUID,
    timezone_name: str | None = None,
    now: datetime | None = None,
) -> ProgramTimelineTodayResponse:
    current_at = _timeline_now(now)
    profile_timezone = db.scalar(select(UserProfile.timezone).where(UserProfile.user_id == user_id))
    timezone = validate_timezone_name(timezone_name or profile_timezone or "UTC")
    local_date = local_date_for_timezone(timezone, now=current_at)
    return ProgramTimelineTodayResponse(
        local_date=local_date,
        timezone=timezone,
        workout=_workout_timeline(
            db,
            user_id=user_id,
            timezone_name=timezone,
            local_date=local_date,
            now=current_at,
        ),
        nutrition=_nutrition_timeline(db, user_id=user_id, local_date=local_date),
    )
