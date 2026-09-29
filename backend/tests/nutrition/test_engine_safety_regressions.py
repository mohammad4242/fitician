from decimal import Decimal

from app.nutrition.enums import NutritionOptimizationMode
from app.nutrition.food_constraints import evaluate_food_constraints, normalize_food_constraints
from app.nutrition.models import NutritionWeeklyPlanDay, NutritionWeeklyPlanNutrient
from app.nutrition.plan_editing import _recalculated_nutrient
from app.nutrition.planner_engine import (
    EligibleMealTemplate,
    GenerationOutcome,
    PlannedDay,
    PlannedFood,
    PlannedMeal,
    _evaluate_built_days,
    _materialize_scheduled_days,
    _validate_nutritional_feasibility,
)
from app.nutrition.planner_policy import DEFAULT_POLICY
from app.nutrition.weight_rate_policy import resolve_weight_rate
from tests.nutrition.test_planner_engine import _food, _input, _simple_template


def test_canonical_allergy_without_known_group_requires_review() -> None:
    constraints = normalize_food_constraints(
        [{"kind": "allergy", "catalogue_food_id": "source", "term": "ماست ساده"}]
    )
    decision = evaluate_food_constraints(
        constraints=constraints,
        food_id="other",
        food_slug="other-yogurt",
        food_allergen_tags=("milk",),
        allergen_metadata_verified=True,
    )
    assert not decision.allowed


def test_weight_rate_policy_invalidates_previous_unsafe_estimates() -> None:
    from app.nutrition.planner_policy import WEIGHT_RATE_POLICY_VERSION

    assert WEIGHT_RATE_POLICY_VERSION == "nutrition-weight-rate-v2"


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


def _fixed_days(*, low_protein_day: bool = False, calcium: str = "1000"):
    days = []
    for index in range(7):
        nutrients = tuple(
            sorted(
                {
                    "energy_kcal": Decimal("2000"),
                    "protein_g": Decimal("50" if low_protein_day and index == 0 else "100"),
                    "carbohydrate_g": Decimal("220"),
                    "total_fat_g": Decimal("60"),
                    "fibre_g": Decimal("25"),
                    "calcium_mg": Decimal(calcium),
                    "sodium_mg": Decimal("1000"),
                }.items()
            )
        )
        food = PlannedFood(
            None,
            "fixed",
            "fixed",
            "fixed",
            (),
            Decimal("100"),
            Decimal("100"),
            nutrients,
            "price",
            Decimal("100"),
            Decimal("100"),
            None,
        )
        meal = PlannedMeal(
            "main_meal", 0, "same-template", "lunch", (food,), Decimal("100"), nutrients
        )
        days.append(PlannedDay(index, (meal,), Decimal("100"), nutrients))
    return tuple(days)


def _evaluate(days, **changes):
    inputs = _input(
        optimization_mode=NutritionOptimizationMode.IDEAL_REFERENCE,
        maximum_meal_repetition_per_week=7,
        **changes,
    )
    return _evaluate_built_days(
        inputs, days, (), {}, DEFAULT_POLICY, substitution_actions=(), optimization_cache={}
    )


def test_twenty_percent_energy_drift_is_not_admitted() -> None:
    inputs = _input(daily_targets={"goal_calories": Decimal("1248")})
    reasons = _validate_nutritional_feasibility(
        inputs,
        {
            "energy_kcal": Decimal("1480"),
            "protein_g": Decimal("100"),
            "carbohydrate_g": Decimal("220"),
            "total_fat_g": Decimal("60"),
        },
        DEFAULT_POLICY,
    )
    assert "CALORIE_TARGET_OUTSIDE_TOLERANCE" in reasons


def test_daily_protein_shortfall_cannot_hide_in_weekly_average() -> None:
    result = _evaluate(_fixed_days(low_protein_day=True))
    assert result.outcome != GenerationOutcome.SUCCESS
    assert "DAILY_MACRONUTRIENT_FLOOR_NOT_MET" in result.reason_codes


def test_reliable_persistent_calcium_gap_requires_review() -> None:
    result = _evaluate(_fixed_days(calcium="531"))
    assert result.outcome != GenerationOutcome.SUCCESS
    assert "MICRONUTRIENT_ADEQUACY_REVIEW_REQUIRED" in result.reason_codes


def test_meal_repetition_cap_is_not_just_a_warning() -> None:
    inputs = _input(
        optimization_mode=NutritionOptimizationMode.IDEAL_REFERENCE,
        maximum_meal_repetition_per_week=2,
    )
    result = _evaluate_built_days(
        inputs,
        _fixed_days(),
        (),
        {},
        DEFAULT_POLICY,
        substitution_actions=(),
        optimization_cache={},
    )
    assert result.outcome != GenerationOutcome.SUCCESS
    assert "MEAL_REPETITION_LIMIT_EXCEEDED" in result.reason_codes


def test_free_meal_reserves_energy_instead_of_adding_a_second_lunch() -> None:
    food = _food("balanced", ("main_protein",), kcal="200", protein="20", carbs="20", fat="5")
    template = _simple_template("lunch", food.food_id)
    candidate = EligibleMealTemplate(template, ((template.items[0], food),))
    schedule = (
        ("main_meal", "lunch", "lunch"),
        ("free_meal", None, "lunch"),
        ("main_meal", "lunch", "lunch"),
    )
    days = _materialize_scheduled_days(
        _input(snacks_per_day=0, template_schedule=(schedule,)),
        (("lunch", None, "lunch"),),
        {"lunch": candidate},
        DEFAULT_POLICY,
        maximum_recipe_cost_irr=Decimal("10000000"),
        optimization_cache={},
    )
    assert dict(days[0].nutrients)["energy_kcal"] <= Decimal("1450")
    assert days[0].meals[1].foods == ()
    assert days[0].meals[1].nutrients == ()


def test_free_snack_reserves_snack_share_and_preserves_macro_distribution() -> None:
    food = _food("balanced", ("main_protein",), kcal="200", protein="20", carbs="20", fat="5")
    template = _simple_template("lunch", food.food_id)
    candidate = EligibleMealTemplate(template, ((template.items[0], food),))
    schedule = (
        ("main_meal", "lunch", "lunch"),
        ("main_meal", "lunch", "lunch"),
        ("free_meal", None, "snack"),
    )
    inputs = _input(snacks_per_day=1, template_schedule=(schedule,))
    days = _materialize_scheduled_days(
        inputs,
        (("lunch", "lunch", None),),
        {"lunch": candidate},
        DEFAULT_POLICY,
        maximum_recipe_cost_irr=Decimal("10000000"),
        optimization_cache={},
    )
    free = days[0].meals[2]
    assert free.reserved_energy_kcal == inputs.daily_targets["goal_calories"] * Decimal(".15")
    assert dict(free.reserved_macro_targets)["protein_g"] == inputs.daily_targets[
        "protein"
    ] * Decimal(".15")


def test_equivalent_replacement_rounding_keeps_fractional_portion_bounds() -> None:
    from app.nutrition.models import NutritionWeeklyPlanFood
    from app.nutrition.plan_editing import _replacement_food

    def food():
        return NutritionWeeklyPlanFood(
            grams=Decimal("100.5"),
            cost_irr=100,
            nutrient_snapshot={"energy_kcal": "201", "protein_g": "20"},
            price_snapshot={},
            quantity_snapshot={
                "functional_role": "protein",
                "min_grams": "100.5",
                "max_grams": "100.5",
            },
        )

    replacement = _replacement_food(None, food(), food())
    assert replacement.grams == Decimal("100.5")


def test_replacement_accepts_bounds_at_persisted_gram_precision() -> None:
    from app.nutrition.models import NutritionWeeklyPlanFood
    from app.nutrition.plan_editing import _replacement_food

    def food():
        return NutritionWeeklyPlanFood(
            grams=Decimal("100.50000000"),
            cost_irr=100,
            nutrient_snapshot={"energy_kcal": "201", "protein_g": "20"},
            price_snapshot={},
            quantity_snapshot={
                "functional_role": "protein",
                "min_grams": "100.500000004",
                "max_grams": "100.500000004",
            },
        )

    replacement = _replacement_food(None, food(), food())
    assert replacement.grams == Decimal("100.50000000")


def test_replacement_energy_ratio_uses_persisted_gram_precision() -> None:
    from app.nutrition.models import NutritionWeeklyPlanFood
    from app.nutrition.plan_editing import _replacement_food

    def food(energy: str):
        return NutritionWeeklyPlanFood(
            grams=Decimal("100.50000000"),
            cost_irr=100,
            nutrient_snapshot={"energy_kcal": energy, "protein_g": "20"},
            price_snapshot={},
            quantity_snapshot={
                "functional_role": "protein",
                "min_grams": "100.50000000",
                "max_grams": "100.50000000",
            },
        )

    replacement = _replacement_food(None, food("201.000000008"), food("201"))
    assert replacement.grams == Decimal("100.50000000")
