"""Operational plan history; allowlisted projections of the existing domain serializers."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import case, exists, func, select
from sqlalchemy.orm import Session, aliased, load_only, selectinload

from app.access_management.insights_schemas import (
    NutritionDetail,
    NutritionHistoryItem,
    Page,
    SafeExercise,
    SafeFood,
    SafeMeal,
    SafeNutritionDay,
    SafeWorkoutDay,
    WorkoutDetail,
    WorkoutHistoryItem,
)
from app.access_management.service import user_or_raise
from app.nutrition.exceptions import NutritionPlanStartConflictError
from app.nutrition.models import (
    NutritionPlanBundle,
    NutritionPlanGeneration,
    NutritionPlanPhysicianReview,
    NutritionWeeklyPlan,
)
from app.nutrition.plan_service import WeeklyPlanNotFoundError, weekly_plan_by_id
from app.workout_reviews.enums import WorkoutReviewStatus
from app.workout_reviews.models import WorkoutPlanReview
from app.workouts.models import WorkoutDay, WorkoutPlan
from app.workouts.repository import get_plan_for_user
from app.workouts.router import to_plan_response
from app.workouts.service import WorkoutGenerationService


def workout_history_item(plan: WorkoutPlan, days: int, review: str | None) -> WorkoutHistoryItem:
    return WorkoutHistoryItem(
        id=plan.id,
        created_at=plan.created_at,
        activated_at=plan.activated_at,
        status=plan.status.value,
        primary_goal=plan.primary_goal,
        secondary_goal=plan.secondary_goal,
        duration_weeks=WorkoutGenerationService.plan_duration_weeks(plan),
        training_days=days,
        review_status=review or "none",
    )


def workout_plans(
    db: Session, user_id: UUID, *, limit: int, offset: int
) -> Page[WorkoutHistoryItem]:
    user_or_raise(db, user_id)
    conditions = (WorkoutPlan.user_id == user_id, WorkoutPlan.deleted_at.is_(None))
    total = int(db.scalar(select(func.count()).select_from(WorkoutPlan).where(*conditions)) or 0)
    day_count = (
        select(func.count(WorkoutDay.id))
        .where(WorkoutDay.workout_plan_id == WorkoutPlan.id)
        .correlate(WorkoutPlan)
        .scalar_subquery()
    )
    approval = aliased(WorkoutPlanReview)
    review_status = case(
        (approval.status == WorkoutReviewStatus.APPROVED, approval.status),
        else_=WorkoutPlanReview.status,
    )
    statement = (
        select(WorkoutPlan, day_count, review_status)
        .outerjoin(WorkoutPlanReview, WorkoutPlanReview.source_plan_id == WorkoutPlan.id)
        .outerjoin(approval, approval.approved_plan_id == WorkoutPlan.id)
        .where(*conditions)
        .options(
            load_only(
                WorkoutPlan.id,
                WorkoutPlan.created_at,
                WorkoutPlan.activated_at,
                WorkoutPlan.status,
                WorkoutPlan.primary_goal,
                WorkoutPlan.secondary_goal,
                WorkoutPlan.profile_snapshot,
            )
        )
        .order_by(WorkoutPlan.created_at.desc(), WorkoutPlan.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return Page(
        items=[
            workout_history_item(plan, days, review) for plan, days, review in db.execute(statement)
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


def workout_detail(db: Session, user_id: UUID, plan_id: UUID) -> WorkoutDetail:
    user_or_raise(db, user_id)
    plan = get_plan_for_user(db, plan_id=plan_id, user_id=user_id)
    if plan is None:
        raise HTTPException(404, detail={"code": "WORKOUT_PLAN_NOT_FOUND"})
    response = to_plan_response(plan, db=db)
    summary = workout_history_item(plan, len(response.days), response.coach_review.state)
    # Keep prescriptions/names only. Never return free-text notes or body-analysis provenance.
    return WorkoutDetail(
        **summary.model_dump(),
        days=[
            SafeWorkoutDay(
                day_number=day.day_number,
                title_en=day.title_en,
                title_fa=day.title_fa,
                estimated_duration_minutes=day.estimated_duration_minutes,
                exercises=[
                    SafeExercise(
                        name_en=item.exercise.name_en,
                        name_fa=item.exercise.name_fa,
                        sets=item.sets,
                        reps_min=item.reps_min,
                        reps_max=item.reps_max,
                        duration_min_seconds=item.duration_min_seconds,
                        duration_max_seconds=item.duration_max_seconds,
                        rest_seconds=item.rest_seconds,
                    )
                    for item in day.exercises
                ],
            )
            for day in response.days
        ],
    )


def nutrition_history_item(plan: NutritionWeeklyPlan, selected: bool) -> NutritionHistoryItem:
    return NutritionHistoryItem(
        id=plan.id,
        revision=plan.revision,
        lifecycle_status=plan.lifecycle_status.value,
        review_status=plan.review.status.value if plan.review else "missing",
        created_at=plan.created_at,
        start_date=plan.start_date,
        started_at=plan.started_at,
        budget_status=plan.budget_status.value,
        selected=selected,
        is_user_visible=plan.is_user_visible,
        plan_role=plan.generation.plan_role,
    )


def nutrition_plans(
    db: Session, user_id: UUID, *, limit: int, offset: int
) -> Page[NutritionHistoryItem]:
    user_or_raise(db, user_id)
    total = int(
        db.scalar(
            select(func.count())
            .select_from(NutritionWeeklyPlan)
            .where(NutritionWeeklyPlan.user_id == user_id)
        )
        or 0
    )
    selected = exists(
        select(NutritionPlanBundle.id).where(
            NutritionPlanBundle.user_id == user_id,
            NutritionPlanBundle.selected_plan_id == NutritionWeeklyPlan.id,
        )
    )
    rows = db.execute(
        select(NutritionWeeklyPlan, selected)
        .where(NutritionWeeklyPlan.user_id == user_id)
        .options(
            load_only(
                NutritionWeeklyPlan.id,
                NutritionWeeklyPlan.revision,
                NutritionWeeklyPlan.lifecycle_status,
                NutritionWeeklyPlan.created_at,
                NutritionWeeklyPlan.start_date,
                NutritionWeeklyPlan.started_at,
                NutritionWeeklyPlan.budget_status,
                NutritionWeeklyPlan.is_user_visible,
            ),
            selectinload(NutritionWeeklyPlan.review).load_only(NutritionPlanPhysicianReview.status),
            selectinload(NutritionWeeklyPlan.generation).load_only(
                NutritionPlanGeneration.plan_role
            ),
        )
        .order_by(NutritionWeeklyPlan.created_at.desc(), NutritionWeeklyPlan.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return Page(
        items=[nutrition_history_item(plan, chosen) for plan, chosen in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


def nutrition_detail(db: Session, user_id: UUID, plan_id: UUID) -> NutritionDetail:
    user_or_raise(db, user_id)
    # Existing member read restrictions still apply; Admin does not gain clinical permission.
    try:
        response = weekly_plan_by_id(db, user_id, plan_id)
    except WeeklyPlanNotFoundError:
        raise HTTPException(404, detail={"code": "NUTRITION_PLAN_NOT_FOUND"}) from None
    except NutritionPlanStartConflictError:
        raise HTTPException(409, detail={"code": "NUTRITION_PLAN_READ_RESTRICTED"}) from None
    plan = db.scalar(
        select(NutritionWeeklyPlan).where(
            NutritionWeeklyPlan.id == plan_id, NutritionWeeklyPlan.user_id == user_id
        )
    )
    if plan is None:
        raise HTTPException(404, detail={"code": "NUTRITION_PLAN_NOT_FOUND"})
    selected = bool(
        db.scalar(
            select(NutritionPlanBundle.id)
            .where(
                NutritionPlanBundle.user_id == user_id,
                NutritionPlanBundle.selected_plan_id == plan_id,
            )
            .limit(1)
        )
    )
    summary = nutrition_history_item(plan, selected)
    return NutritionDetail(
        **summary.model_dump(),
        days=[
            SafeNutritionDay(
                day_index=day.day_index,
                plan_date=day.plan_date,
                meals=[
                    SafeMeal(
                        slot=meal.slot_role,
                        foods=[
                            SafeFood(
                                name_fa=food.name_fa,
                                name_en=food.name_en,
                                grams=food.grams,
                            )
                            for food in meal.foods
                        ],
                    )
                    for meal in day.meals
                ],
            )
            for day in response.days
        ],
    )
