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
                NutritionPlanGeneration.plan_role
                != NutritionPlanRole.IDEAL_REFERENCE.value,
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
