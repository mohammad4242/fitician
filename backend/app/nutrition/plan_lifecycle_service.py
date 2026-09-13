from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session, selectinload

from app.auth.models import User
from app.nutrition.enums import (
    NutritionPlanLifecycleStatus,
    NutritionPlanReviewStatus,
    NutritionPlanRole,
)
from app.nutrition.exceptions import (
    NutritionPlanStartConflictError,
    NutritionPlanStartNotFoundError,
)
from app.nutrition.models import (
    NutritionPlanGeneration,
    NutritionWeeklyPlan,
    NutritionWeeklyPlanDay,
    NutritionWeeklyPlanMeal,
)
from app.nutrition.plan_service import weekly_plan_response
from app.nutrition.schemas import WeeklyPlanResponse
from app.profile.models import UserProfile
from app.time_context import validate_timezone_name


def _plan_query() -> Select[tuple[NutritionWeeklyPlan]]:
    return select(NutritionWeeklyPlan).options(
        selectinload(NutritionWeeklyPlan.generation).selectinload(NutritionPlanGeneration.bundle),
        selectinload(NutritionWeeklyPlan.review),
        selectinload(NutritionWeeklyPlan.nutrients),
        selectinload(NutritionWeeklyPlan.days)
        .selectinload(NutritionWeeklyPlanDay.meals)
        .selectinload(NutritionWeeklyPlanMeal.foods),
    )


def _load_owned_plan(
    db: Session, *, user_id: UUID, plan_id: UUID, lock: bool
) -> NutritionWeeklyPlan:
    query = _plan_query().where(
        NutritionWeeklyPlan.id == plan_id,
        NutritionWeeklyPlan.user_id == user_id,
    )
    if lock:
        query = query.with_for_update()
    plan = db.scalar(query)
    if plan is None:
        raise NutritionPlanStartNotFoundError
    return plan


def _ensure_selected_member_plan(plan: NutritionWeeklyPlan) -> None:
    generation = plan.generation
    if generation is None:
        raise NutritionPlanStartConflictError(
            "NUTRITION_PLAN_NOT_SELECTED",
            "این برنامه غذایی برای شروع انتخاب نشده است.",
        )
    if generation.plan_role == NutritionPlanRole.IDEAL_REFERENCE.value:
        raise NutritionPlanStartConflictError(
            "NUTRITION_REFERENCE_PLAN_NOT_STARTABLE",
            "برنامه مقایسه‌ای قابل شروع نیست.",
        )
    if generation.bundle is not None and generation.bundle.selected_plan_id != plan.id:
        raise NutritionPlanStartConflictError(
            "NUTRITION_PLAN_NOT_SELECTED",
            "ابتدا همین برنامه غذایی را انتخاب کنید.",
        )
    if not plan.is_user_visible:
        raise NutritionPlanStartConflictError(
            "NUTRITION_PLAN_NOT_SELECTED",
            "این برنامه غذایی برای شروع انتخاب نشده است.",
        )


def _ensure_startable_lifecycle(plan: NutritionWeeklyPlan, requested_start: date) -> bool:
    if plan.lifecycle_status is NutritionPlanLifecycleStatus.ACTIVE:
        if plan.start_date != requested_start:
            raise NutritionPlanStartConflictError(
                "NUTRITION_PLAN_ALREADY_STARTED",
                "این برنامه غذایی قبلاً با تاریخ دیگری شروع شده است.",
            )
        return False

    if plan.review is not None and plan.review.status is not NutritionPlanReviewStatus.APPROVED:
        raise NutritionPlanStartConflictError(
            "NUTRITION_PLAN_NOT_READY",
            "این برنامه غذایی هنوز تأیید نشده است.",
        )

    if plan.lifecycle_status is NutritionPlanLifecycleStatus.PHYSICIAN_APPROVED:
        plan.lifecycle_status = NutritionPlanLifecycleStatus.READY_TO_START
    elif plan.lifecycle_status is not NutritionPlanLifecycleStatus.READY_TO_START:
        raise NutritionPlanStartConflictError(
            "NUTRITION_PLAN_NOT_READY",
            "این برنامه غذایی هنوز آماده شروع نیست.",
        )
    return True


def _archive_other_active_plans(db: Session, *, user_id: UUID, plan_id: UUID) -> None:
    db.execute(
        update(NutritionWeeklyPlan)
        .where(
            NutritionWeeklyPlan.user_id == user_id,
            NutritionWeeklyPlan.id != plan_id,
            NutritionWeeklyPlan.lifecycle_status == NutritionPlanLifecycleStatus.ACTIVE,
        )
        .values(lifecycle_status=NutritionPlanLifecycleStatus.ARCHIVED)
    )
    db.flush()


def _persist_timezone(db: Session, *, user_id: UUID, timezone_name: str) -> None:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id).with_for_update())
    if profile is not None:
        profile.timezone = timezone_name


def _reload_plan(db: Session, *, user_id: UUID, plan_id: UUID) -> NutritionWeeklyPlan:
    plan = db.scalar(
        _plan_query().where(
            NutritionWeeklyPlan.id == plan_id,
            NutritionWeeklyPlan.user_id == user_id,
        )
    )
    if plan is None:
        raise NutritionPlanStartNotFoundError
    return plan


def start_nutrition_plan(
    db: Session,
    *,
    user_id: UUID,
    plan_id: UUID,
    start_date: date,
    timezone_name: str,
) -> WeeklyPlanResponse:
    timezone_name = validate_timezone_name(timezone_name)
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise NutritionPlanStartNotFoundError
    plan = _load_owned_plan(db, user_id=user_id, plan_id=plan_id, lock=True)
    _ensure_selected_member_plan(plan)
    should_start = _ensure_startable_lifecycle(plan, start_date)

    if should_start:
        _archive_other_active_plans(db, user_id=user_id, plan_id=plan.id)
        plan.start_date = start_date
        plan.started_at = datetime.now(UTC)
        plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
        for day in plan.days:
            day.plan_date = start_date + timedelta(days=day.day_index)
        _persist_timezone(db, user_id=user_id, timezone_name=timezone_name)

    db.commit()
    return weekly_plan_response(_reload_plan(db, user_id=user_id, plan_id=plan.id))
