from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.nutrition.enums import NutritionPlanLifecycleStatus, NutritionPlanRole
from app.nutrition.models import (
    NutritionPlanBundle,
    NutritionPlanGeneration,
    NutritionWeeklyPlan,
    NutritionWeeklyPlanDay,
    NutritionWeeklyPlanMeal,
)


def nutrition_pattern_day_index(start_date: date, target_date: date) -> int:
    """Return the recurring weekly-template index for a calendar date."""
    return (target_date - start_date).days % 7


def nutrition_absolute_day_number(start_date: date, target_date: date) -> int:
    """Return the one-based absolute day number for a calendar date."""
    return (target_date - start_date).days + 1


def effective_nutrition_plan_for_date(
    db: Session, user_id: UUID, target_date: date
) -> NutritionWeeklyPlan | None:
    """Return the newest started plan effective on the requested local date."""
    return db.scalar(
        select(NutritionWeeklyPlan)
        .join(
            NutritionPlanGeneration,
            NutritionPlanGeneration.id == NutritionWeeklyPlan.generation_id,
        )
        .outerjoin(
            NutritionPlanBundle,
            NutritionPlanBundle.id == NutritionPlanGeneration.bundle_id,
        )
        .where(
            NutritionWeeklyPlan.user_id == user_id,
            NutritionWeeklyPlan.lifecycle_status == NutritionPlanLifecycleStatus.ACTIVE,
            NutritionWeeklyPlan.start_date <= target_date,
            or_(
                NutritionPlanGeneration.plan_role != NutritionPlanRole.IDEAL_REFERENCE.value,
                NutritionPlanBundle.selected_plan_id == NutritionWeeklyPlan.id,
            ),
        )
        .options(
            selectinload(NutritionWeeklyPlan.days)
            .selectinload(NutritionWeeklyPlanDay.meals)
            .selectinload(NutritionWeeklyPlanMeal.foods)
        )
        .order_by(
            NutritionWeeklyPlan.start_date.desc(),
            NutritionWeeklyPlan.revision.desc(),
            NutritionWeeklyPlan.created_at.desc(),
        )
        .limit(1)
    )


def archive_superseded_future_nutrition_successors(
    db: Session,
    user_id: UUID,
    *,
    local_date: date,
    keep_plan_id: UUID | None = None,
) -> None:
    """Archive active successors that can no longer be the member's next plan."""
    query = (
        select(NutritionWeeklyPlan)
        .where(
            NutritionWeeklyPlan.user_id == user_id,
            NutritionWeeklyPlan.lifecycle_status == NutritionPlanLifecycleStatus.ACTIVE,
            NutritionWeeklyPlan.start_date > local_date,
        )
        .with_for_update()
    )
    if keep_plan_id is not None:
        query = query.where(NutritionWeeklyPlan.id != keep_plan_id)

    for successor in db.scalars(query):
        successor.lifecycle_status = NutritionPlanLifecycleStatus.ARCHIVED
        successor.is_user_visible = False
