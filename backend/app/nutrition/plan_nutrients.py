"""Recalculate derived plan metrics from immutable food and quantity snapshots."""

from decimal import Decimal

from app.nutrition.models import NutritionWeeklyPlanDay, NutritionWeeklyPlanNutrient


def recalculated_nutrient(
    row: NutritionWeeklyPlanNutrient,
    days: list[NutritionWeeklyPlanDay],
    input_snapshot: dict[str, object],
) -> NutritionWeeklyPlanNutrient:
    code_map = {
        "goal_calories": "energy_kcal",
        "protein": "protein_g",
        "carbohydrate": "carbohydrate_g",
        "total_fat": "total_fat_g",
        "fibre": "fibre_g",
    }
    code = code_map.get(row.nutrient_code, row.nutrient_code)
    daily_values: list[Decimal] = []
    for day in days:
        foods = [food for meal in day.meals for food in meal.foods]
        if day.meals:
            value = sum(
                (Decimal(str(food.nutrient_snapshot.get(code, 0))) for food in foods), Decimal()
            )
            if row.nutrient_code in {"goal_calories", "protein", "carbohydrate", "total_fat"}:
                value += sum(
                    (
                        Decimal(str(meal.target_distribution.get(row.nutrient_code, 0)))
                        for meal in day.meals
                        if meal.slot_role.value == "free_meal"
                    ),
                    Decimal(),
                )
        else:
            value = Decimal(str(day.nutrient_totals.get(code, 0)))
        daily_values.append(value)
    planned = sum(daily_values, Decimal()) / Decimal(len(days))
    preferred = row.preferred_value
    minimums = input_snapshot.get("daily_minimums", {})
    maximums = input_snapshot.get("daily_maximums", {})
    upper_limits = input_snapshot.get("micronutrient_upper_limits", {})
    minimum = (
        Decimal(str(minimums[row.nutrient_code]))
        if isinstance(minimums, dict) and row.nutrient_code in minimums
        else None
    )
    maximum_source = (
        maximums if isinstance(maximums, dict) and row.nutrient_code in maximums else upper_limits
    )
    maximum = (
        Decimal(str(maximum_source[row.nutrient_code]))
        if isinstance(maximum_source, dict) and row.nutrient_code in maximum_source
        else None
    )
    if maximum is not None and planned > maximum:
        status, reasons = "above_applicable_limit", ["ABOVE_APPLICABLE_LIMIT"]
    elif minimum is not None and planned < minimum:
        status, reasons = "below_minimum", ["BELOW_MINIMUM"]
    elif preferred is not None and planned < preferred:
        status, reasons = (
            ("below_preferred_but_acceptable" if minimum is not None else "below_reference_target"),
            ["DIETARY_REFERENCE_GAP"],
        )
    else:
        status, reasons = "within_target", []
    limit = maximum if maximum is not None else minimum
    return NutritionWeeklyPlanNutrient(
        nutrient_code=row.nutrient_code,
        unit=row.unit,
        reference_kind=row.reference_kind,
        preferred_value=preferred,
        minimum_or_maximum_value=limit,
        planned_value=planned,
        difference_from_preferred=planned - preferred if preferred is not None else None,
        difference_from_limit=planned - limit if limit is not None else None,
        status=status,
        reason_codes=reasons,
        data_confidence=(
            "medium"
            if row.nutrient_code in {"goal_calories", "protein", "carbohydrate", "total_fat"}
            and any(meal.slot_role.value == "free_meal" for day in days for meal in day.meals)
            else row.data_confidence
        ),
        explanation_codes=["DIETARY_REFERENCE_GAP"] if "DIETARY_REFERENCE_GAP" in reasons else [],
    )
