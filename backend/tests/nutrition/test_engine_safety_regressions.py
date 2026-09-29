from decimal import Decimal

from app.nutrition.food_constraints import evaluate_food_constraints, normalize_food_constraints
from app.nutrition.models import NutritionWeeklyPlanDay, NutritionWeeklyPlanNutrient
from app.nutrition.plan_editing import _recalculated_nutrient
from app.nutrition.weight_rate_policy import resolve_weight_rate


def test_canonical_milk_allergy_also_excludes_yogurt() -> None:
    constraints = normalize_food_constraints(
        [{"kind": "allergy", "catalogue_food_id": "milk-id", "term": "شیر"}]
    )
    decision = evaluate_food_constraints(
        constraints=constraints,
        food_id="yogurt-id",
        food_slug="plain-yogurt",
        food_allergen_tags=("milk",),
        allergen_metadata_verified=True,
    )
    assert not decision.allowed


def test_allergy_cannot_admit_food_with_unknown_allergens() -> None:
    decision = evaluate_food_constraints(
        constraints=normalize_food_constraints(allergies=("gluten",)),
        food_slug="sangak",
        food_name_fa="نان سنگک",
        allergen_metadata_verified=False,
    )
    assert not decision.allowed
    assert "ALLERGEN_METADATA_UNVERIFIED" in decision.hard_reason_codes


def test_canonical_allergy_uses_catalogue_allergen_tags_with_qualified_name() -> None:
    constraints = normalize_food_constraints(
        [
            {
                "kind": "allergy",
                "catalogue_food_id": "cheese-id",
                "term": "پنیر کم چرب",
                "allergen_tags": ["milk"],
            }
        ]
    )
    decision = evaluate_food_constraints(
        constraints=constraints,
        food_id="yogurt-id",
        food_slug="plain-yogurt",
        food_allergen_tags=("milk",),
        allergen_metadata_verified=True,
    )
    assert not decision.allowed


def test_override_keeps_goal_specific_surplus_safety_limit() -> None:
    result = resolve_weight_rate(
        goal="gain_weight",
        body_weight_kg=Decimal("85"),
        tdee_kcal=Decimal("2294"),
        requested_kg_per_week=Decimal("2"),
        training_experience="beginner",
        rate_mode="user_override",
    )
    assert result.calorie_delta_kcal_per_day <= Decimal("459")
    assert result.was_clamped


def test_edit_recalculates_fat_from_daily_total_fat() -> None:
    row = NutritionWeeklyPlanNutrient(
        nutrient_code="total_fat",
        unit="g",
        reference_kind="preferred",
        preferred_value=Decimal("60"),
        planned_value=Decimal("60"),
        data_confidence="high",
    )
    days = [
        NutritionWeeklyPlanDay(day_index=i, nutrient_totals={"total_fat_g": "60"}) for i in range(7)
    ]
    revised = _recalculated_nutrient(row, days, {"daily_minimums": {"total_fat": "40"}})
    assert revised.planned_value == Decimal("60")
    assert revised.status == "within_target"
