from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.nutrition.enums import SafetyOutcome
from app.nutrition.models import (
    NutritionEstimate,
    NutritionSafetyDecision,
    NutritionWeeklyPlan,
)
from app.profile.models import UserProfile


def current_medical_safety_decision(
    db: Session,
    user_id: UUID,
    *,
    lock_profile: bool = False,
) -> NutritionSafetyDecision | None:
    if lock_profile:
        db.scalar(select(UserProfile).where(UserProfile.user_id == user_id).with_for_update())
    return db.scalar(
        select(NutritionSafetyDecision)
        .where(NutritionSafetyDecision.user_id == user_id)
        .options(selectinload(NutritionSafetyDecision.reasons))
        .order_by(NutritionSafetyDecision.revision.desc())
        .limit(1)
    )


def plan_uses_current_medical_context(
    db: Session,
    plan: NutritionWeeklyPlan,
    decision: NutritionSafetyDecision | None,
) -> bool:
    generation = plan.generation
    if decision is None or generation is None:
        return False
    estimate_safety_id = db.scalar(
        select(NutritionEstimate.safety_decision_id).where(NutritionEstimate.id == plan.estimate_id)
    )
    return (
        plan.safety_decision_id == decision.id
        and generation.safety_decision_id == decision.id
        and generation.estimate_id == plan.estimate_id
        and estimate_safety_id == decision.id
    )


def medical_context_is_blocked(decision: NutritionSafetyDecision) -> bool:
    return decision.outcome is SafetyOutcome.UNSUPPORTED_OR_HARD_BLOCKED
