from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.body_analysis.enums import SpecialistRole
from app.entitlements.enums import EntitlementCode
from app.entitlements.service import consume_quota
from app.notifications.content import build_notification_payload
from app.notifications.outbox import enqueue_notification_event
from app.notifications.recipients import specialist_user_ids
from app.nutrition.catalogue_constraints import constraints_for_items
from app.nutrition.clinical_service import ClinicalError, require_physician
from app.nutrition.enums import (
    NutritionMealFeedbackType,
    NutritionPlanBudgetStatus,
    NutritionPlanGenerationOutcome,
    NutritionPlanLifecycleStatus,
    NutritionPlanReviewStatus,
    NutritionPlanRole,
    SafetyOutcome,
)
from app.nutrition.food_constraints import evaluate_food_constraints
from app.nutrition.medical_context import (
    current_medical_safety_decision,
    medical_context_is_blocked,
    plan_uses_current_medical_context,
)
from app.nutrition.models import (
    NutritionCatalogueFood,
    NutritionCatalogueMealItem,
    NutritionFoodItem,
    NutritionMealFeedback,
    NutritionPlanBundle,
    NutritionPlanGeneration,
    NutritionPlanPhysicianReview,
    NutritionReviewAuditEvent,
    NutritionSafetyDecision,
    NutritionWeeklyPlan,
    NutritionWeeklyPlanDay,
    NutritionWeeklyPlanFood,
    NutritionWeeklyPlanMeal,
)
from app.nutrition.plan_nutrients import recalculated_nutrient as _recalculated_nutrient
from app.nutrition.plan_service import weekly_plan_response
from app.nutrition.plan_validation import NUTRIENT_CODES, validate_plan_totals
from app.nutrition.planner_engine import PlannerInput
from app.nutrition.planner_policy import DEFAULT_POLICY, PLANNER_POLICY_VERSION
from app.nutrition.schemas import WeeklyPlanResponse
from app.profile.review_summary import build_review_profile_summary


class PlanEditError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


def _plan_requires_physician_review(
    db: Session,
    plan: NutritionWeeklyPlan,
    *,
    physician_id: UUID | None = None,
    physician_review_allowed: bool = False,
) -> bool:
    if physician_id is not None or physician_review_allowed or plan.review is not None:
        return True
    if plan.lifecycle_status in {
        NutritionPlanLifecycleStatus.PENDING_PHYSICIAN_REVIEW,
        NutritionPlanLifecycleStatus.PHYSICIAN_REVIEW_IN_PROGRESS,
        NutritionPlanLifecycleStatus.AWAITING_LAB_INFORMATION,
        NutritionPlanLifecycleStatus.CHANGES_REQUESTED,
        NutritionPlanLifecycleStatus.PHYSICIAN_APPROVED,
        NutritionPlanLifecycleStatus.REJECTED,
    }:
        return True
    safety = db.get(NutritionSafetyDecision, plan.safety_decision_id)
    return safety is not None and safety.outcome is not SafetyOutcome.STANDARD_AUTOMATIC


def _query() -> Select[tuple[NutritionWeeklyPlan]]:
    return select(NutritionWeeklyPlan).options(
        selectinload(NutritionWeeklyPlan.generation),
        selectinload(NutritionWeeklyPlan.review),
        selectinload(NutritionWeeklyPlan.nutrients),
        selectinload(NutritionWeeklyPlan.days)
        .selectinload(NutritionWeeklyPlanDay.meals)
        .selectinload(NutritionWeeklyPlanMeal.foods),
    )


def owned_plan(
    db: Session, user_id: UUID, plan_id: UUID, *, lock: bool = False
) -> NutritionWeeklyPlan:
    query = _query().where(
        NutritionWeeklyPlan.id == plan_id, NutritionWeeklyPlan.user_id == user_id
    )
    if lock:
        query = query.with_for_update()
    plan = db.scalar(query)
    if plan is None:
        raise PlanEditError("NUTRITION_PLAN_NOT_FOUND")
    return plan


def shopping_list(db: Session, user_id: UUID, plan_id: UUID) -> dict[str, object]:
    plan = owned_plan(db, user_id, plan_id)
    items: dict[UUID, dict[str, Any]] = {}
    for day in plan.days:
        for meal in day.meals:
            for food in meal.foods:
                if food.item_kind == "prepared_recipe" and food.recipe_snapshot is not None:
                    raw_ingredients = food.recipe_snapshot.get("ingredients", [])
                    if isinstance(raw_ingredients, list):
                        for ingredient in raw_ingredients:
                            if isinstance(ingredient, dict):
                                _add_shopping_snapshot_item(items, ingredient)
                    continue
                if food.food_id is None:
                    continue
                item = items.setdefault(
                    food.food_id,
                    {
                        "food_id": food.food_id,
                        "slug": food.food_slug,
                        "name_fa": food.food_name_fa,
                        "name_en": food.food_name_en,
                        "required_quantity": Decimal(),
                        "canonical_unit": "g",
                        "cost_irr": 0,
                        "nutrients": defaultdict(Decimal),
                        "price_snapshot": food.price_snapshot,
                    },
                )
                item["required_quantity"] += food.grams
                item["cost_irr"] += food.cost_irr
                nutrients = item["nutrients"]
                for code, value in food.nutrient_snapshot.items():
                    nutrients[code] += Decimal(str(value))
    serialized = []
    for item in sorted(items.values(), key=lambda row: str(row["slug"])):
        item["required_quantity"] = float(item["required_quantity"])
        item["nutrients"] = {key: float(value) for key, value in item["nutrients"].items()}
        serialized.append(item)
    return {
        "plan_id": plan.id,
        "plan_revision": plan.revision,
        "approval_status": plan.review.status.value if plan.review else "missing",
        "warning_codes": []
        if plan.lifecycle_status == NutritionPlanLifecycleStatus.ACTIVE
        else ["PLAN_NOT_ACTIVE"],
        "items": serialized,
        "total_cost_irr": sum(int(item["cost_irr"]) for item in serialized),
    }


def _add_shopping_snapshot_item(
    items: dict[UUID, dict[str, Any]], ingredient: dict[str, object]
) -> None:
    try:
        food_id = UUID(str(ingredient["food_id"]))
        grams = Decimal(str(ingredient["grams"]))
        cost = int(Decimal(str(ingredient["cost_irr"])))
    except (KeyError, TypeError, ValueError):
        return
    item = items.setdefault(
        food_id,
        {
            "food_id": food_id,
            "slug": str(ingredient.get("slug", "")),
            "name_fa": str(ingredient.get("name_fa", "")),
            "name_en": str(ingredient.get("name_en", "")),
            "required_quantity": Decimal(),
            "canonical_unit": "g",
            "cost_irr": 0,
            "nutrients": defaultdict(Decimal),
            "price_snapshot": {"reference_id": ingredient.get("price_reference_id")},
        },
    )
    item["required_quantity"] += grams
    item["cost_irr"] += cost
    nutrients = ingredient.get("nutrients", {})
    if isinstance(nutrients, dict):
        for code, value in nutrients.items():
            item["nutrients"][str(code)] += Decimal(str(value))


def set_meal_lock(
    db: Session, user_id: UUID, plan_id: UUID, meal_id: UUID, locked: bool
) -> dict[str, object]:
    plan = owned_plan(db, user_id, plan_id, lock=True)
    meal = next((meal for day in plan.days for meal in day.meals if meal.id == meal_id), None)
    if meal is None:
        raise PlanEditError("MEAL_NOT_FOUND")
    meal.is_locked = locked
    db.commit()
    return {
        "plan_id": plan.id,
        "plan_revision": plan.revision,
        "meal_id": meal.id,
        "is_locked": locked,
        "change_kind": "plan_control_metadata",
    }


def save_feedback(
    db: Session,
    user_id: UUID,
    plan_id: UUID,
    meal_id: UUID,
    kind: NutritionMealFeedbackType,
    notes: str | None,
) -> dict[str, object]:
    plan = owned_plan(db, user_id, plan_id)
    if not any(meal.id == meal_id for day in plan.days for meal in day.meals):
        raise PlanEditError("MEAL_NOT_FOUND")
    row = db.scalar(
        select(NutritionMealFeedback).where(
            NutritionMealFeedback.user_id == user_id, NutritionMealFeedback.meal_id == meal_id
        )
    )
    if row is None:
        row = NutritionMealFeedback(
            user_id=user_id, meal_id=meal_id, feedback_type=kind, notes=notes
        )
        db.add(row)
    else:
        row.feedback_type = kind
        row.notes = notes
    db.commit()
    return {"meal_id": meal_id, "feedback_type": kind.value, "change_kind": "plan_control_metadata"}


def meal_feedback(db: Session, user_id: UUID, plan_id: UUID) -> dict[str, object]:
    plan = owned_plan(db, user_id, plan_id)
    meal_ids = [meal.id for day in plan.days for meal in day.meals]
    rows = db.scalars(
        select(NutritionMealFeedback).where(
            NutritionMealFeedback.user_id == user_id,
            NutritionMealFeedback.meal_id.in_(meal_ids),
        )
    ).all()
    return {"feedback": {str(row.meal_id): row.feedback_type.value for row in rows}}


def meal_replacement_options(
    db: Session, user_id: UUID, plan_id: UUID, meal_id: UUID
) -> dict[str, object]:
    plan = owned_plan(db, user_id, plan_id)
    target = next((meal for day in plan.days for meal in day.meals if meal.id == meal_id), None)
    if target is None:
        raise PlanEditError("MEAL_NOT_FOUND")
    if target.is_locked:
        raise PlanEditError("MEAL_LOCKED")
    options = [
        meal
        for day in plan.days
        for meal in day.meals
        if meal.id != target.id and meal.slot_role == target.slot_role and not meal.is_locked
    ]
    return {
        "target_meal_id": target.id,
        "options": [
            {
                "id": meal.id,
                "name_fa": meal.catalogue_meal.name_fa if meal.catalogue_meal else "وعده غذایی",
                "name_en": meal.catalogue_meal.name_en if meal.catalogue_meal else "Meal",
                "meal_code": meal.catalogue_meal.code if meal.catalogue_meal else "",
                "image_url": meal.catalogue_meal.image_path if meal.catalogue_meal else None,
                "slot_role": meal.slot_role.value,
                "nutrient_totals": _float_map(meal.nutrient_totals),
                "cost_irr": meal.cost_irr,
                "is_locked": meal.is_locked,
            }
            for meal in options
        ],
    }


def food_replacement_options(
    db: Session, user_id: UUID, plan_id: UUID, meal_id: UUID, food_id: UUID
) -> dict[str, object]:
    plan = owned_plan(db, user_id, plan_id)
    target_meal = next(
        (meal for day in plan.days for meal in day.meals if meal.id == meal_id), None
    )
    if target_meal is None:
        raise PlanEditError("MEAL_NOT_FOUND")
    if target_meal.is_locked:
        raise PlanEditError("MEAL_LOCKED")
    target = next((food for food in target_meal.foods if food.food_id == food_id), None)
    if target is None:
        raise PlanEditError("FOOD_REPLACEMENT_NOT_FOUND")
    assert target.food_id is not None
    source_by_food_id: dict[UUID, NutritionWeeklyPlanFood] = {}
    for day in plan.days:
        for meal in day.meals:
            if meal.is_locked:
                continue
            for food in meal.foods:
                if food.food_id is not None and food.food_id != target.food_id:
                    source_by_food_id.setdefault(food.food_id, food)
    catalogue_foods = {
        food.id: food
        for food in db.scalars(
            select(NutritionCatalogueFood).where(NutritionCatalogueFood.id.in_(source_by_food_id))
        )
    }
    options = []
    for source_food_id, source in sorted(source_by_food_id.items(), key=lambda item: str(item[0])):
        try:
            scaled = _replacement_food(db, target, source)
            _validate_edited_days(db, plan, _replacement_days(plan, target, scaled))
        except PlanEditError:
            continue
        catalogue_food = catalogue_foods.get(source_food_id)
        options.append(
            {
                "food_id": source_food_id,
                "slug": source.food_slug,
                "name_fa": source.food_name_fa,
                "name_en": source.food_name_en,
                "image_url": catalogue_food.image_path if catalogue_food else None,
                "grams": float(scaled.grams),
                "cost_irr": scaled.cost_irr,
                "nutrients": _float_map(scaled.nutrient_snapshot),
            }
        )
    return {"target_meal_id": target_meal.id, "target_food_id": target.food_id, "options": options}


def _removed_days(plan: NutritionWeeklyPlan, meal_id: UUID) -> list[NutritionWeeklyPlanDay]:
    days: list[NutritionWeeklyPlanDay] = []
    for day in plan.days:
        meals = [_copy_meal(meal) for meal in day.meals if meal.id != meal_id]
        days.append(
            NutritionWeeklyPlanDay(
                day_index=day.day_index,
                plan_date=day.plan_date,
                cost_irr=sum(meal.cost_irr for meal in meals),
                nutrient_totals=_sum_maps([meal.nutrient_totals for meal in meals]),
                meals=meals,
            )
        )
    return days


def preview_remove_meal(
    db: Session,
    user_id: UUID,
    plan_id: UUID,
    meal_id: UUID,
    *,
    physician_review_allowed: bool = False,
) -> dict[str, object]:
    plan = owned_plan(db, user_id, plan_id)
    meal = next((meal for day in plan.days for meal in day.meals if meal.id == meal_id), None)
    if meal is None:
        raise PlanEditError("MEAL_NOT_FOUND")
    if meal.is_locked:
        raise PlanEditError("MEAL_LOCKED")
    _validate_edited_days(db, plan, _removed_days(plan, meal_id))
    return {
        "plan_id": plan.id,
        "expected_plan_revision_id": plan.id,
        "expected_revision": plan.revision,
        "operation": "remove_meal",
        "meal_id": meal.id,
        "daily_delta": {key: -float(str(value)) for key, value in meal.nutrient_totals.items()},
        "weekly_cost_delta_irr": -meal.cost_irr,
        "new_warning_codes": ["MEAL_REMOVAL_MAY_REDUCE_ADEQUACY"],
        "requires_physician_review": _plan_requires_physician_review(
            db, plan, physician_review_allowed=physician_review_allowed
        ),
        "change_kind": "plan_defining",
    }


def _copy_food(food: NutritionWeeklyPlanFood) -> NutritionWeeklyPlanFood:
    return NutritionWeeklyPlanFood(
        food_id=food.food_id,
        item_kind=food.item_kind,
        recipe_snapshot=food.recipe_snapshot,
        quantity_snapshot=dict(food.quantity_snapshot or {}),
        food_slug=food.food_slug,
        food_name_fa=food.food_name_fa,
        food_name_en=food.food_name_en,
        grams=food.grams,
        cost_irr=food.cost_irr,
        nutrient_snapshot=dict(food.nutrient_snapshot),
        price_snapshot=dict(food.price_snapshot),
    )


def _sum_maps(maps: list[dict[str, object]]) -> dict[str, object]:
    totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    for values in maps:
        for key, value in values.items():
            totals[key] += Decimal(str(value))
    return {key: str(value) for key, value in totals.items()}


def _copy_meal(
    meal: NutritionWeeklyPlanMeal, *, slot_index: int | None = None
) -> NutritionWeeklyPlanMeal:
    return NutritionWeeklyPlanMeal(
        catalogue_meal_id=meal.catalogue_meal_id,
        catalogue_meal_category=meal.catalogue_meal_category,
        slot_role=meal.slot_role,
        slot_index=meal.slot_index if slot_index is None else slot_index,
        target_distribution=dict(meal.target_distribution),
        nutrient_totals=dict(meal.nutrient_totals),
        cost_irr=meal.cost_irr,
        is_locked=meal.is_locked,
        foods=[_copy_food(food) for food in meal.foods],
    )


def _decimal_map(snapshot: dict[str, object], key: str) -> dict[str, Decimal]:
    raw = snapshot.get(key, {})
    return (
        {str(code): Decimal(str(value)) for code, value in raw.items()}
        if isinstance(raw, dict)
        else {}
    )


def _stored_grams(value: Decimal) -> Decimal:
    # NutritionWeeklyPlanFood.grams is PostgreSQL NUMERIC(20, 8).
    return value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def _validate_edited_days(
    db: Session,
    plan: NutritionWeeklyPlan,
    days: list[NutritionWeeklyPlanDay],
) -> None:
    snapshot = plan.input_snapshot
    targets = _decimal_map(snapshot, "daily_targets")
    if "goal_calories" not in targets:
        raise PlanEditError("PLAN_EDIT_NUTRITION_CONSTRAINT_VIOLATION")
    raw_maintenance = snapshot.get("maintenance_calories")
    inputs = PlannerInput(
        daily_targets=targets,
        daily_minimums=_decimal_map(snapshot, "daily_minimums"),
        daily_maximums=_decimal_map(snapshot, "daily_maximums"),
        micronutrient_targets=_decimal_map(snapshot, "micronutrient_targets"),
        micronutrient_upper_limits=_decimal_map(snapshot, "micronutrient_upper_limits"),
        main_meals_per_day=int(str(snapshot.get("main_meals_per_day", 3))),
        snacks_per_day=int(str(snapshot.get("snacks_per_day", 0))),
        weekly_budget_irr=plan.weekly_budget_irr,
        budget_mode=str(snapshot.get("budget_mode", "strict")),
        maximum_meal_repetition_per_week=int(
            str(snapshot.get("maximum_meal_repetition_per_week", 7))
        ),
        maintenance_calories=Decimal(str(raw_maintenance)) if raw_maintenance is not None else None,
    )
    daily_totals: list[dict[str, Decimal]] = []
    known_energy = {code: Decimal() for code in inputs.micronutrient_targets}
    total_energy = Decimal()
    items = db.scalars(
        select(NutritionFoodItem).where(NutritionFoodItem.user_id == plan.user_id)
    ).all()
    constraints = constraints_for_items(db, items)
    disliked_ids = {item.catalogue_food_id for item in items if item.kind.value == "disliked"}
    for day in days:
        # Recompute from copied foods, so stale aggregate columns cannot bypass admission.
        totals = {
            code: Decimal(str(value))
            for code, value in _sum_maps(
                [food.nutrient_snapshot for meal in day.meals for food in meal.foods]
            ).items()
        }
        for meal in day.meals:
            if meal.slot_role.value == "free_meal":
                for code in ("goal_calories", "protein", "carbohydrate", "total_fat"):
                    allowance = Decimal(str(meal.target_distribution.get(code, 0)))
                    nutrient_code = NUTRIENT_CODES[code]
                    totals[nutrient_code] = totals.get(nutrient_code, Decimal()) + allowance
                total_energy += Decimal(str(meal.target_distribution.get("goal_calories", 0)))
            for food in meal.foods:
                energy = Decimal(str(food.nutrient_snapshot.get("energy_kcal", 0)))
                total_energy += energy
                for code in known_energy:
                    if code in food.nutrient_snapshot:
                        known_energy[code] += energy
                ingredient_ids = [food.food_id] if food.food_id is not None else []
                if food.recipe_snapshot:
                    selected = food.recipe_snapshot.get("selected_ingredient_grams", {})
                    if isinstance(selected, dict):
                        ingredient_ids.extend(UUID(str(value)) for value in selected)
                for ingredient_id in ingredient_ids:
                    catalogue = db.get(NutritionCatalogueFood, ingredient_id)
                    if catalogue is None or ingredient_id in disliked_ids:
                        raise PlanEditError("PLAN_EDIT_NUTRITION_CONSTRAINT_VIOLATION")
                    decision = evaluate_food_constraints(
                        constraints=constraints,
                        food_id=str(ingredient_id),
                        food_slug=catalogue.slug,
                        food_name_fa=catalogue.name_fa,
                        food_allergen_tags=tuple(catalogue.allergen_tags),
                        allergen_metadata_verified=catalogue.allergen_metadata_verified,
                    )
                    if not decision.allowed:
                        raise PlanEditError("PLAN_EDIT_NUTRITION_CONSTRAINT_VIOLATION")
                metadata = food.quantity_snapshot or {}
                if isinstance(metadata, dict) and metadata:
                    if (
                        not _stored_grams(Decimal(str(metadata["min_grams"])))
                        <= _stored_grams(food.grams)
                        <= _stored_grams(Decimal(str(metadata["max_grams"])))
                    ):
                        raise PlanEditError("FOOD_PORTION_OUTSIDE_BOUNDS")
        day.nutrient_totals = {code: str(value) for code, value in totals.items()}
        daily_totals.append(totals)
    completeness = {
        code: value / total_energy if total_energy else Decimal()
        for code, value in known_energy.items()
    }
    reasons = validate_plan_totals(
        inputs,
        daily_totals,
        DEFAULT_POLICY,
        template_ids=[
            str(meal.catalogue_meal_id)
            for day in days
            for meal in day.meals
            if meal.catalogue_meal_id
        ],
        data_completeness=completeness,
    )
    # A known reference gap can remain in a clinical draft; it cannot become an
    # automatically approved plan. Energy, portions, allergens and ULs stay hard.
    if plan.review is not None:
        reasons = tuple(
            code for code in reasons if code != "MICRONUTRIENT_ADEQUACY_REVIEW_REQUIRED"
        )
    cost = sum(day.cost_irr for day in days)
    cap = Decimal(plan.weekly_budget_irr) * (
        Decimal("1.15") if snapshot.get("budget_mode") == "flexible" else Decimal("1")
    )
    if reasons or (snapshot.get("optimization_mode") != "ideal_reference" and cost > cap):
        raise PlanEditError("PLAN_EDIT_NUTRITION_CONSTRAINT_VIOLATION")


def _replacement_food(
    db: Session,
    target: NutritionWeeklyPlanFood,
    source: NutritionWeeklyPlanFood,
) -> NutritionWeeklyPlanFood:
    def context(food: NutritionWeeklyPlanFood) -> tuple[str | None, Decimal, Decimal]:
        raw = food.quantity_snapshot or None
        if isinstance(raw, dict):
            role = raw.get("functional_role")
            return (
                role if isinstance(role, str) else None,
                Decimal(str(raw["min_grams"])),
                Decimal(str(raw["max_grams"])),
            )
        # Historical plans have no bounds snapshot. Resolve the original slot,
        # rather than assigning a role from a food's display name.
        meal = db.get(NutritionWeeklyPlanMeal, food.meal_id)
        item = db.scalar(
            select(NutritionCatalogueMealItem).where(
                NutritionCatalogueMealItem.meal_id == (meal.catalogue_meal_id if meal else None),
                NutritionCatalogueMealItem.food_id == food.food_id,
            )
        )
        if item is None:
            raise PlanEditError("FOOD_REPLACEMENT_INCOMPATIBLE")
        scale = food.grams / item.reference_grams
        return (
            item.functional_role.value if item.functional_role else None,
            item.min_grams * scale,
            min(item.max_grams * scale, DEFAULT_POLICY.maximum_main_food_portion_g),
        )

    target_role, _, _ = context(target)
    source_role, minimum, maximum = context(source)
    minimum, maximum = _stored_grams(minimum), _stored_grams(maximum)
    if target_role is None or source_role != target_role:
        raise PlanEditError("FOOD_REPLACEMENT_INCOMPATIBLE")
    target_kcal = Decimal(str(target.nutrient_snapshot.get("energy_kcal", 0)))
    source_kcal = Decimal(str(source.nutrient_snapshot.get("energy_kcal", 0)))
    if target_kcal <= 0 or source_kcal <= 0:
        raise PlanEditError("FOOD_REPLACEMENT_INCOMPATIBLE")
    requested_grams = _stored_grams(target_kcal * source.grams / source_kcal)
    if not minimum <= requested_grams <= maximum:
        raise PlanEditError("FOOD_PORTION_OUTSIDE_BOUNDS")
    grams = min(max(requested_grams.quantize(Decimal("1")), minimum), maximum)
    return _scaled_food(source, grams)


def _replacement_days(
    plan: NutritionWeeklyPlan,
    target: NutritionWeeklyPlanFood,
    replacement: NutritionWeeklyPlanFood,
) -> list[NutritionWeeklyPlanDay]:
    def transform(meal: NutritionWeeklyPlanMeal) -> NutritionWeeklyPlanMeal:
        copied = _copy_meal(meal)
        copied.foods = [
            _copy_food(replacement if food.id == target.id else food) for food in meal.foods
        ]
        copied.nutrient_totals = _sum_maps([food.nutrient_snapshot for food in copied.foods])
        copied.cost_irr = sum(food.cost_irr for food in copied.foods)
        return copied

    return [_copy_day(day, transform) for day in plan.days]


def _create_revision(
    db: Session,
    plan: NutritionWeeklyPlan,
    user_id: UUID,
    days: list[NutritionWeeklyPlanDay],
    operation: str,
    *,
    physician_id: UUID | None = None,
    physician_review_allowed: bool = False,
) -> WeeklyPlanResponse:
    _validate_edited_days(db, plan, days)
    latest = (
        db.scalar(
            select(func.max(NutritionWeeklyPlan.revision)).where(
                NutritionWeeklyPlan.user_id == user_id
            )
        )
        or 0
    )
    generation = db.get(NutritionPlanGeneration, plan.generation_id)
    if generation is None:
        raise PlanEditError("PLAN_GENERATION_NOT_FOUND")
    selected_bundle_ids = db.scalars(
        select(NutritionPlanBundle.id).where(
            NutritionPlanBundle.user_id == user_id,
            NutritionPlanBundle.selected_plan_id == plan.id,
        )
    ).all()
    review_required = _plan_requires_physician_review(
        db,
        plan,
        physician_id=physician_id,
        physician_review_allowed=physician_review_allowed,
    )
    member_review_required = physician_id is None and review_required
    revision = latest + 1
    new_plan_id = uuid4()
    if member_review_required:
        consume_quota(
            db,
            user_id,
            EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
            f"nutrition-plan:{new_plan_id}:revision:{revision}",
        )
    copied_generation = NutritionPlanGeneration(
        user_id=user_id,
        estimate_id=generation.estimate_id,
        safety_decision_id=generation.safety_decision_id,
        outcome=NutritionPlanGenerationOutcome.SUCCESS,
        reason_codes=[],
        warning_codes=["PHYSICIAN_PLAN_EDIT" if physician_id else "USER_PLAN_EDIT"],
        input_signature=generation.input_signature,
        input_snapshot=dict(generation.input_snapshot),
        diagnostic_snapshot={"source_plan_id": str(plan.id), "operation": operation},
        planner_policy_version=PLANNER_POLICY_VERSION,
        planner_version=generation.planner_version,
    )
    db.add(copied_generation)
    db.flush()
    new_plan = NutritionWeeklyPlan(
        id=new_plan_id,
        user_id=user_id,
        generation_id=copied_generation.id,
        estimate_id=plan.estimate_id,
        safety_decision_id=plan.safety_decision_id,
        revision=revision,
        supersedes_plan_id=plan.id,
        lineage_id=plan.lineage_id,
        lifecycle_status=(
            NutritionPlanLifecycleStatus.PENDING_PHYSICIAN_REVIEW
            if review_required
            else NutritionPlanLifecycleStatus.READY_TO_START
        ),
        is_user_visible=True,
        start_date=plan.start_date,
        planner_policy_version=PLANNER_POLICY_VERSION,
        planner_version=plan.planner_version,
        scientific_policy_version=plan.scientific_policy_version,
        formula_version=plan.formula_version,
        food_data_manifest=dict(plan.food_data_manifest),
        input_snapshot=dict(plan.input_snapshot),
        price_snapshot=dict(plan.price_snapshot),
        repair_snapshot=list(plan.repair_snapshot),
        warning_codes=list(
            set(plan.warning_codes + ["PHYSICIAN_PLAN_EDIT" if physician_id else "USER_PLAN_EDIT"])
        ),
        explanation_codes=list(plan.explanation_codes),
        weekly_cost_irr=sum(day.cost_irr for day in days),
        weekly_budget_irr=plan.weekly_budget_irr,
        budget_status=_budget_status(
            sum(day.cost_irr for day in days),
            plan.weekly_budget_irr,
            str(plan.input_snapshot.get("budget_mode", "strict")),
        ),
        days=days,
        nutrients=[
            _recalculated_nutrient(row, days, plan.input_snapshot) for row in plan.nutrients
        ],
        review=(
            NutritionPlanPhysicianReview(
                status=NutritionPlanReviewStatus.IN_REVIEW
                if physician_id
                else NutritionPlanReviewStatus.PENDING,
                expected_plan_revision=revision,
                physician_user_id=physician_id,
                assigned_at=datetime.now(UTC) if physician_id else None,
                review_started_at=datetime.now(UTC) if physician_id else None,
                structured_change_summary=[
                    {"operation": operation, "source_plan_id": str(plan.id)}
                ],
            )
            if review_required
            else None
        ),
    )
    db.add(new_plan)
    db.flush()
    if plan.review and plan.review.status in {
        NutritionPlanReviewStatus.PENDING,
        NutritionPlanReviewStatus.IN_REVIEW,
        NutritionPlanReviewStatus.AWAITING_LAB_INFORMATION,
        NutritionPlanReviewStatus.CHANGES_REQUESTED,
    }:
        plan.review.status = NutritionPlanReviewStatus.INVALIDATED_BY_REVISION
        plan.review.invalidated_at = datetime.now(UTC)
        plan.review.invalidation_reason = "PLAN_DEFINING_REVISION"
        plan.lifecycle_status = NutritionPlanLifecycleStatus.ARCHIVED
    if selected_bundle_ids:
        db.execute(
            update(NutritionPlanBundle)
            .where(
                NutritionPlanBundle.id.in_(selected_bundle_ids),
                NutritionPlanBundle.user_id == user_id,
                NutritionPlanBundle.selected_plan_id == plan.id,
            )
            .values(selected_plan_id=new_plan.id)
        )
    if review_required and physician_id is None:
        review = new_plan.review
        if review is None:
            raise PlanEditError("NUTRITION_REVIEW_NOT_CREATED")
        payload = build_notification_payload(
            "nutrition_review_required",
            data={"review_id": review.id, "plan_id": new_plan.id},
        )
        for reviewer_id in specialist_user_ids(
            db,
            (SpecialistRole.PHYSICIAN, SpecialistRole.DOCTOR),
        ):
            enqueue_notification_event(
                db,
                user_id=reviewer_id,
                event_type="nutrition_review_required",
                category="required_reviews",
                deduplication_key=f"nutrition-review:{review.id}:required",
                payload=payload,
            )
    db.commit()
    db.refresh(new_plan)
    revised_plan = owned_plan(db, user_id, new_plan.id)
    return weekly_plan_response(
        revised_plan,
        db=db,
        profile_summary=(
            build_review_profile_summary(db, user_id) if physician_id is not None else None
        ),
    )


def _budget_status(cost: int, budget: int, mode: str) -> NutritionPlanBudgetStatus:
    if cost <= budget:
        return NutritionPlanBudgetStatus.WITHIN_BUDGET
    if mode == "flexible" and cost <= round(budget * 1.15):
        return NutritionPlanBudgetStatus.FLEXIBLE_OVERAGE
    return NutritionPlanBudgetStatus.OVER_BUDGET


def confirm_remove_meal(
    db: Session,
    user_id: UUID,
    plan_id: UUID,
    expected_plan_revision_id: UUID,
    meal_id: UUID,
    *,
    physician_id: UUID | None = None,
    physician_review_allowed: bool = False,
) -> WeeklyPlanResponse:
    plan = owned_plan(db, user_id, plan_id, lock=True)
    if plan.id != expected_plan_revision_id:
        raise PlanEditError("STALE_PLAN_REVISION")
    if (
        physician_id is None
        and plan.review
        and plan.review.status == NutritionPlanReviewStatus.IN_REVIEW
    ):
        raise PlanEditError("PLAN_REVIEW_IN_PROGRESS")
    if not any(meal.id == meal_id for day in plan.days for meal in day.meals):
        raise PlanEditError("MEAL_NOT_FOUND")
    meal = next(meal for day in plan.days for meal in day.meals if meal.id == meal_id)
    if meal.is_locked:
        raise PlanEditError("MEAL_LOCKED")
    days = _removed_days(plan, meal_id)
    return _create_revision(
        db,
        plan,
        user_id,
        days,
        "remove_meal",
        physician_id=physician_id,
        physician_review_allowed=physician_review_allowed,
    )


def preview_replace_meal(
    db: Session,
    user_id: UUID,
    plan_id: UUID,
    meal_id: UUID,
    replacement_meal_id: UUID,
    *,
    physician_review_allowed: bool = False,
) -> dict[str, object]:
    plan = owned_plan(db, user_id, plan_id)
    meals = {meal.id: meal for day in plan.days for meal in day.meals}
    target, replacement = meals.get(meal_id), meals.get(replacement_meal_id)
    if target is None or replacement is None:
        raise PlanEditError("MEAL_NOT_FOUND")
    if target.is_locked or replacement.is_locked:
        raise PlanEditError("MEAL_LOCKED")
    if target.slot_role != replacement.slot_role or target.id == replacement.id:
        raise PlanEditError("INCOMPATIBLE_MEAL_REPLACEMENT")
    days = [
        _copy_day(
            day,
            lambda meal: (
                _copy_meal(replacement, slot_index=target.slot_index)
                if meal.id == target.id
                else _copy_meal(meal)
            ),
        )
        for day in plan.days
    ]
    _validate_edited_days(db, plan, days)
    return {
        "plan_id": plan.id,
        "expected_plan_revision_id": plan.id,
        "meal_id": target.id,
        "replacement_meal_id": replacement.id,
        "daily_delta": _delta(target.nutrient_totals, replacement.nutrient_totals),
        "weekly_cost_delta_irr": replacement.cost_irr - target.cost_irr,
        "requires_physician_review": _plan_requires_physician_review(
            db, plan, physician_review_allowed=physician_review_allowed
        ),
        "change_kind": "plan_defining",
    }


def confirm_replace_meal(
    db: Session,
    user_id: UUID,
    plan_id: UUID,
    expected_plan_revision_id: UUID,
    meal_id: UUID,
    replacement_meal_id: UUID,
    *,
    physician_review_allowed: bool = False,
) -> WeeklyPlanResponse:
    plan = owned_plan(db, user_id, plan_id, lock=True)
    _assert_editable(plan, expected_plan_revision_id)
    meals = {meal.id: meal for day in plan.days for meal in day.meals}
    target, replacement = meals.get(meal_id), meals.get(replacement_meal_id)
    if target is None or replacement is None:
        raise PlanEditError("MEAL_NOT_FOUND")
    if target.slot_role != replacement.slot_role or target.id == replacement.id:
        raise PlanEditError("INCOMPATIBLE_MEAL_REPLACEMENT")
    if target.is_locked or replacement.is_locked:
        raise PlanEditError("MEAL_LOCKED")
    days = [
        _copy_day(
            day,
            lambda meal: (
                _copy_meal(replacement, slot_index=target.slot_index)
                if meal.id == target.id
                else _copy_meal(meal)
            ),
        )
        for day in plan.days
    ]
    return _create_revision(
        db,
        plan,
        user_id,
        days,
        "replace_meal",
        physician_review_allowed=physician_review_allowed,
    )


def preview_replace_food(
    db: Session,
    user_id: UUID,
    plan_id: UUID,
    meal_id: UUID,
    food_id: UUID,
    replacement_food_id: UUID,
    *,
    physician_review_allowed: bool = False,
) -> dict[str, object]:
    plan = owned_plan(db, user_id, plan_id)
    meal = next((meal for day in plan.days for meal in day.meals if meal.id == meal_id), None)
    if meal is None:
        raise PlanEditError("MEAL_NOT_FOUND")
    if meal.is_locked:
        raise PlanEditError("MEAL_LOCKED")
    target = next((food for food in meal.foods if food.food_id == food_id), None)
    replacement = next(
        (
            food
            for day in plan.days
            for candidate in day.meals
            for food in candidate.foods
            if food.food_id == replacement_food_id
        ),
        None,
    )
    if target is None or replacement is None or target.food_id == replacement.food_id:
        raise PlanEditError("FOOD_REPLACEMENT_NOT_FOUND")
    scaled = _replacement_food(db, target, replacement)
    _validate_edited_days(db, plan, _replacement_days(plan, target, scaled))
    return {
        "plan_id": plan.id,
        "expected_plan_revision_id": plan.id,
        "meal_id": meal.id,
        "food_id": target.food_id,
        "replacement_food_id": replacement.food_id,
        "meal_delta": _delta(target.nutrient_snapshot, scaled.nutrient_snapshot),
        "cost_delta_irr": scaled.cost_irr - target.cost_irr,
        "requires_physician_review": _plan_requires_physician_review(
            db, plan, physician_review_allowed=physician_review_allowed
        ),
        "change_kind": "plan_defining",
    }


def confirm_replace_food(
    db: Session,
    user_id: UUID,
    plan_id: UUID,
    expected_plan_revision_id: UUID,
    meal_id: UUID,
    food_id: UUID,
    replacement_food_id: UUID,
    *,
    physician_id: UUID | None = None,
    physician_review_allowed: bool = False,
) -> WeeklyPlanResponse:
    plan = owned_plan(db, user_id, plan_id, lock=True)
    if physician_id is None:
        _assert_editable(plan, expected_plan_revision_id)
    elif plan.id != expected_plan_revision_id:
        raise PlanEditError("STALE_PLAN_REVISION")
    elif (
        plan.review is None
        or plan.review.physician_user_id != physician_id
        or plan.review.status != NutritionPlanReviewStatus.IN_REVIEW
    ):
        raise PlanEditError("REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN")
    target_meal = next(
        (meal for day in plan.days for meal in day.meals if meal.id == meal_id), None
    )
    replacement = next(
        (
            food
            for day in plan.days
            for meal in day.meals
            for food in meal.foods
            if food.food_id == replacement_food_id
        ),
        None,
    )
    if target_meal is None or replacement is None:
        raise PlanEditError("FOOD_REPLACEMENT_NOT_FOUND")
    if target_meal.is_locked:
        raise PlanEditError("MEAL_LOCKED")
    if replacement is not None:
        source_meal = next(
            (meal for day in plan.days for meal in day.meals if replacement in meal.foods),
            None,
        )
        if source_meal is not None and source_meal.is_locked:
            raise PlanEditError("MEAL_LOCKED")
    target = next((food for food in target_meal.foods if food.food_id == food_id), None)
    if target is None or target.food_id == replacement.food_id:
        raise PlanEditError("FOOD_REPLACEMENT_NOT_FOUND")

    def transform(meal: NutritionWeeklyPlanMeal) -> NutritionWeeklyPlanMeal:
        if meal.id != target_meal.id:
            return _copy_meal(meal)
        foods = [
            _replacement_food(db, target, replacement)
            if food.food_id == target.food_id
            else _copy_food(food)
            for food in meal.foods
        ]
        return NutritionWeeklyPlanMeal(
            catalogue_meal_id=meal.catalogue_meal_id,
            catalogue_meal_category=meal.catalogue_meal_category,
            slot_role=meal.slot_role,
            slot_index=meal.slot_index,
            target_distribution=dict(meal.target_distribution),
            nutrient_totals=_sum_maps([food.nutrient_snapshot for food in foods]),
            cost_irr=sum(food.cost_irr for food in foods),
            is_locked=False,
            foods=foods,
        )

    days = [_copy_day(day, transform) for day in plan.days]
    return _create_revision(
        db,
        plan,
        user_id,
        days,
        "replace_food",
        physician_id=physician_id,
        physician_review_allowed=physician_review_allowed,
    )


def partial_regenerate(
    db: Session,
    user_id: UUID,
    plan_id: UUID,
    expected_plan_revision_id: UUID,
    day_indexes: list[int],
    *,
    physician_review_allowed: bool = False,
) -> WeeklyPlanResponse:
    plan = owned_plan(db, user_id, plan_id, lock=True)
    _assert_editable(plan, expected_plan_revision_id)
    selected = set(day_indexes)
    if not selected or not selected.issubset(set(range(7))):
        raise PlanEditError("INVALID_DAY_SELECTION")
    source_by_key = {
        (day.day_index, meal.slot_role, meal.slot_index): meal
        for day in plan.days
        for meal in day.meals
    }

    def transform_for(day_index: int, meal: NutritionWeeklyPlanMeal) -> NutritionWeeklyPlanMeal:
        if day_index not in selected or meal.is_locked:
            return _copy_meal(meal)
        for offset in range(1, 7):
            candidate = source_by_key.get(
                ((day_index + offset) % 7, meal.slot_role, meal.slot_index)
            )
            if candidate is not None and candidate.id != meal.id:
                return _copy_meal(candidate, slot_index=meal.slot_index)
        return _copy_meal(meal)

    days = [
        _copy_day(day, lambda meal, index=day.day_index: transform_for(index, meal))
        for day in plan.days
    ]
    return _create_revision(
        db,
        plan,
        user_id,
        days,
        "partial_regeneration",
        physician_review_allowed=physician_review_allowed,
    )


def _assert_editable(plan: NutritionWeeklyPlan, expected: UUID) -> None:
    if plan.id != expected:
        raise PlanEditError("STALE_PLAN_REVISION")
    if plan.generation and plan.generation.plan_role == NutritionPlanRole.IDEAL_REFERENCE.value:
        if not (plan.generation.bundle and plan.generation.bundle.selected_plan_id == plan.id):
            raise PlanEditError("IDEAL_REFERENCE_PLAN_CANNOT_BE_EDITED")
    if plan.review and plan.review.status == NutritionPlanReviewStatus.IN_REVIEW:
        raise PlanEditError("PLAN_REVIEW_IN_PROGRESS")


def _copy_day(day: NutritionWeeklyPlanDay, transform: Any) -> NutritionWeeklyPlanDay:
    meals = [transform(meal) for meal in day.meals]
    return NutritionWeeklyPlanDay(
        day_index=day.day_index,
        plan_date=day.plan_date,
        cost_irr=sum(meal.cost_irr for meal in meals),
        nutrient_totals=_sum_maps([meal.nutrient_totals for meal in meals]),
        meals=meals,
    )


def _delta(before: dict[str, object], after: dict[str, object]) -> dict[str, float]:
    keys = set(before) | set(after)
    return {
        key: float(Decimal(str(after.get(key, 0))) - Decimal(str(before.get(key, 0))))
        for key in keys
    }


def _float_map(values: dict[str, object]) -> dict[str, float]:
    return {key: float(str(value)) for key, value in values.items()}


def _scaled_food(food: NutritionWeeklyPlanFood, grams: Decimal) -> NutritionWeeklyPlanFood:
    ratio = grams / food.grams
    return NutritionWeeklyPlanFood(
        food_id=food.food_id,
        item_kind=food.item_kind,
        recipe_snapshot=food.recipe_snapshot,
        quantity_snapshot=dict(food.quantity_snapshot or {}),
        food_slug=food.food_slug,
        food_name_fa=food.food_name_fa,
        food_name_en=food.food_name_en,
        grams=grams,
        cost_irr=round(food.cost_irr * float(ratio)),
        nutrient_snapshot={
            key: str(Decimal(str(value)) * ratio) for key, value in food.nutrient_snapshot.items()
        },
        price_snapshot=dict(food.price_snapshot),
    )


def physician_remove_meal(
    db: Session,
    physician_id: UUID,
    plan_id: UUID,
    expected_plan_revision_id: UUID,
    meal_id: UUID,
) -> WeeklyPlanResponse:
    try:
        require_physician(db, physician_id)
    except ClinicalError as error:
        raise PlanEditError("PHYSICIAN_ROLE_REQUIRED") from error
    plan = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan_id))
    if plan is None:
        raise PlanEditError("NUTRITION_PLAN_NOT_FOUND")
    review = db.scalar(
        select(NutritionPlanPhysicianReview).where(NutritionPlanPhysicianReview.plan_id == plan_id)
    )
    if review is None or review.physician_user_id != physician_id:
        raise PlanEditError("REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN")
    if review.status != NutritionPlanReviewStatus.IN_REVIEW:
        raise PlanEditError("REVIEW_NOT_IN_PROGRESS")
    return confirm_remove_meal(
        db,
        plan.user_id,
        plan_id,
        expected_plan_revision_id,
        meal_id,
        physician_id=physician_id,
    )


def physician_adjust_food_quantity(
    db: Session,
    physician_id: UUID,
    plan_id: UUID,
    expected_plan_revision_id: UUID,
    meal_id: UUID,
    food_id: UUID,
    grams: Decimal,
) -> WeeklyPlanResponse:
    try:
        require_physician(db, physician_id)
    except ClinicalError as error:
        raise PlanEditError("PHYSICIAN_ROLE_REQUIRED") from error
    plan = db.scalar(_query().where(NutritionWeeklyPlan.id == plan_id).with_for_update())
    if plan is None:
        raise PlanEditError("NUTRITION_PLAN_NOT_FOUND")
    if plan.id != expected_plan_revision_id:
        raise PlanEditError("STALE_PLAN_REVISION")
    if (
        plan.review is None
        or plan.review.physician_user_id != physician_id
        or plan.review.status != NutritionPlanReviewStatus.IN_REVIEW
    ):
        raise PlanEditError("REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN")
    target_meal = next(
        (meal for day in plan.days for meal in day.meals if meal.id == meal_id),
        None,
    )
    if target_meal is None:
        raise PlanEditError("MEAL_NOT_FOUND")
    target_food = next((food for food in target_meal.foods if food.food_id == food_id), None)
    if target_food is None:
        raise PlanEditError("FOOD_REPLACEMENT_NOT_FOUND")

    def transform(meal: NutritionWeeklyPlanMeal) -> NutritionWeeklyPlanMeal:
        if meal.id != target_meal.id:
            return _copy_meal(meal)
        foods = [
            _scaled_food(food, grams) if food.food_id == target_food.food_id else _copy_food(food)
            for food in meal.foods
        ]
        return NutritionWeeklyPlanMeal(
            catalogue_meal_id=meal.catalogue_meal_id,
            catalogue_meal_category=meal.catalogue_meal_category,
            slot_role=meal.slot_role,
            slot_index=meal.slot_index,
            target_distribution=dict(meal.target_distribution),
            nutrient_totals=_sum_maps([food.nutrient_snapshot for food in foods]),
            cost_irr=sum(food.cost_irr for food in foods),
            is_locked=meal.is_locked,
            foods=foods,
        )

    days = [_copy_day(day, transform) for day in plan.days]
    return _create_revision(
        db,
        plan,
        plan.user_id,
        days,
        "adjust_food_quantity",
        physician_id=physician_id,
    )


def physician_replace_food(
    db: Session,
    physician_id: UUID,
    plan_id: UUID,
    expected_plan_revision_id: UUID,
    meal_id: UUID,
    food_id: UUID,
    replacement_food_id: UUID,
) -> WeeklyPlanResponse:
    try:
        require_physician(db, physician_id)
    except ClinicalError as error:
        raise PlanEditError("PHYSICIAN_ROLE_REQUIRED") from error
    user_id = db.scalar(
        select(NutritionWeeklyPlan.user_id).where(NutritionWeeklyPlan.id == plan_id)
    )
    if user_id is None:
        raise PlanEditError("NUTRITION_PLAN_NOT_FOUND")
    return confirm_replace_food(
        db,
        user_id,
        plan_id,
        expected_plan_revision_id,
        meal_id,
        food_id,
        replacement_food_id,
        physician_id=physician_id,
    )


def physician_plan(db: Session, physician_id: UUID, plan_id: UUID) -> WeeklyPlanResponse:
    try:
        require_physician(db, physician_id)
    except ClinicalError as error:
        raise PlanEditError("PHYSICIAN_ROLE_REQUIRED") from error
    plan = db.scalar(_query().where(NutritionWeeklyPlan.id == plan_id))
    if plan is None or plan.review is None:
        raise PlanEditError("NUTRITION_PLAN_NOT_FOUND")
    if plan.review.physician_user_id != physician_id:
        raise PlanEditError("REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN")
    return _physician_plan_response(db, plan)


def physician_action(
    db: Session,
    physician_id: UUID,
    plan_id: UUID,
    expected_plan_revision_id: UUID,
    action: str,
    notes: str | None,
    internal_notes: str | None = None,
) -> WeeklyPlanResponse:
    try:
        require_physician(db, physician_id)
    except ClinicalError as error:
        raise PlanEditError("PHYSICIAN_ROLE_REQUIRED") from error
    plan = db.scalar(_query().where(NutritionWeeklyPlan.id == plan_id).with_for_update())
    if plan is None:
        raise PlanEditError("NUTRITION_PLAN_NOT_FOUND")
    if (
        plan.id != expected_plan_revision_id
        or not plan.review
        or plan.review.expected_plan_revision != plan.revision
    ):
        raise PlanEditError("STALE_PLAN_REVISION")
    now = datetime.now(UTC)
    if plan.review.physician_user_id not in {None, physician_id}:
        raise PlanEditError("REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN")
    if action != "start_review" and plan.review.physician_user_id is None:
        raise PlanEditError("REVIEW_NOT_CLAIMED")
    if action != "start_review" and plan.review.physician_user_id != physician_id:
        raise PlanEditError("REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN")
    if action == "approve":
        if plan.review.status != NutritionPlanReviewStatus.IN_REVIEW:
            raise PlanEditError("REVIEW_NOT_IN_PROGRESS")
        decision = current_medical_safety_decision(db, plan.user_id, lock_profile=True)
        if not plan_uses_current_medical_context(db, plan, decision):
            raise PlanEditError("NUTRITION_PLAN_MEDICAL_CONTEXT_CHANGED")
        if decision is not None and medical_context_is_blocked(decision):
            raise PlanEditError("NUTRITION_PLAN_SAFETY_BLOCKED")
    normalized_notes = notes.strip() if notes else None
    normalized_internal_notes = internal_notes.strip() if internal_notes else None
    if action in {"request_changes", "reject"} and not normalized_notes:
        raise PlanEditError("REVIEW_NOTES_REQUIRED")
    plan.review.user_visible_notes = normalized_notes
    if internal_notes is not None:
        plan.review.internal_notes = normalized_internal_notes
    if action == "start_review":
        if plan.review.status not in {
            NutritionPlanReviewStatus.PENDING,
            NutritionPlanReviewStatus.CHANGES_REQUESTED,
        }:
            raise PlanEditError("INVALID_REVIEW_TRANSITION")
        plan.review.physician_user_id = physician_id
        plan.review.assigned_at = plan.review.assigned_at or now
        plan.review.status = NutritionPlanReviewStatus.IN_REVIEW
        plan.lifecycle_status = NutritionPlanLifecycleStatus.PHYSICIAN_REVIEW_IN_PROGRESS
        plan.review.review_started_at = now
    elif action == "approve":
        if plan.review.status != NutritionPlanReviewStatus.IN_REVIEW:
            raise PlanEditError("REVIEW_NOT_IN_PROGRESS")
        if (
            any(
                nutrient.status in {"below_minimum", "above_applicable_limit"}
                for nutrient in plan.nutrients
            )
            or plan.budget_status == NutritionPlanBudgetStatus.OVER_BUDGET
        ):
            raise PlanEditError("PLAN_HARD_INVARIANTS_FAILED")
        plan.review.status = NutritionPlanReviewStatus.APPROVED
        plan.review.reviewed_at = now
        plan.lifecycle_status = NutritionPlanLifecycleStatus.READY_TO_START
    elif action == "request_changes":
        if plan.review.status not in {
            NutritionPlanReviewStatus.IN_REVIEW,
            NutritionPlanReviewStatus.AWAITING_LAB_INFORMATION,
        }:
            raise PlanEditError("REVIEW_NOT_IN_PROGRESS")
        plan.review.status = NutritionPlanReviewStatus.CHANGES_REQUESTED
        plan.lifecycle_status = NutritionPlanLifecycleStatus.CHANGES_REQUESTED
    elif action == "reject":
        if plan.review.status not in {
            NutritionPlanReviewStatus.IN_REVIEW,
            NutritionPlanReviewStatus.AWAITING_LAB_INFORMATION,
        }:
            raise PlanEditError("REVIEW_NOT_IN_PROGRESS")
        plan.review.status = NutritionPlanReviewStatus.REJECTED
        plan.review.reviewed_at = now
        plan.lifecycle_status = NutritionPlanLifecycleStatus.REJECTED
    else:
        raise PlanEditError("INVALID_REVIEW_ACTION")
    decision_event_types = {
        "approve": "physician_plan_approved",
        "request_changes": "physician_changes_requested",
        "reject": "physician_plan_rejected",
    }
    decision_event_type = decision_event_types.get(action)
    if decision_event_type is not None:
        enqueue_notification_event(
            db,
            user_id=plan.user_id,
            event_type=decision_event_type,
            category="physician_decisions",
            deduplication_key=f"nutrition-plan:{plan.id}:physician:{action}:{plan.revision}",
            payload=build_notification_payload(
                decision_event_type,
                data={"plan_id": plan.id, "action": action},
            ),
        )
    db.add(
        NutritionReviewAuditEvent(
            review_id=plan.review.id,
            actor_user_id=physician_id,
            action=action,
            metadata_snapshot={"plan_id": str(plan.id), "revision": plan.revision},
        )
    )
    db.commit()
    return _physician_plan_response(db, owned_plan(db, plan.user_id, plan.id))


def _physician_plan_response(
    db: Session,
    plan: NutritionWeeklyPlan,
) -> WeeklyPlanResponse:
    return weekly_plan_response(
        plan,
        db=db,
        profile_summary=build_review_profile_summary(db, plan.user_id),
    )
