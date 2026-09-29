"""Shared, deterministic admission rules for generated and edited nutrition plans.

Energy reservations are planning allowances, never measured food composition.
Reference gaps indicate a need to review the diet, not a clinical diagnosis.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Protocol

from app.nutrition.planner_policy import PlannerPolicy

ZERO = Decimal("0")
NUTRIENT_CODES = {
    "goal_calories": "energy_kcal",
    "protein": "protein_g",
    "carbohydrate": "carbohydrate_g",
    "total_fat": "total_fat_g",
    "fibre": "fibre_g",
}


class NutritionContract(Protocol):
    @property
    def daily_targets(self) -> dict[str, Decimal]: ...

    @property
    def daily_minimums(self) -> dict[str, Decimal]: ...

    @property
    def daily_maximums(self) -> dict[str, Decimal]: ...

    @property
    def micronutrient_targets(self) -> dict[str, Decimal]: ...

    @property
    def micronutrient_upper_limits(self) -> dict[str, Decimal]: ...

    @property
    def maintenance_calories(self) -> Decimal | None: ...

    @property
    def maximum_meal_repetition_per_week(self) -> int: ...


def validate_nutrient_totals(
    inputs: NutritionContract,
    totals: Mapping[str, Decimal],
    policy: PlannerPolicy,
    *,
    daily: bool = False,
) -> tuple[str, ...]:
    reasons: list[str] = []
    goal = inputs.daily_targets.get("goal_calories", ZERO)
    tolerance = goal * (
        policy.daily_calorie_tolerance_ratio if daily else policy.calorie_tolerance_ratio
    )
    maintenance = inputs.maintenance_calories
    if not daily and maintenance is not None and maintenance != goal:
        tolerance = min(tolerance, abs(maintenance - goal) * policy.energy_delta_tolerance_ratio)
    if goal > ZERO and abs(totals.get("energy_kcal", ZERO) - goal) > tolerance:
        reasons.append("CALORIE_TARGET_OUTSIDE_TOLERANCE")
    if any(
        totals.get(NUTRIENT_CODES.get(code, code), ZERO) < minimum
        for code, minimum in inputs.daily_minimums.items()
        if code in {"protein", "carbohydrate", "total_fat"}
    ):
        reasons.append("MACRONUTRIENT_FLOOR_NOT_MET")
    if any(
        totals.get(NUTRIENT_CODES.get(code, code), ZERO)
        > maximum * (Decimal("1") + policy.macro_tolerance_ratio)
        for code, maximum in inputs.daily_maximums.items()
        if code in {"carbohydrate", "total_fat"}
    ):
        reasons.append("MACRONUTRIENT_MAXIMUM_EXCEEDED")
    if any(
        totals.get(code, ZERO) > maximum
        for code, maximum in inputs.micronutrient_upper_limits.items()
    ):
        reasons.append("NUTRIENT_UPPER_LIMIT_EXCEEDED")
    return tuple(reasons)


def validate_plan_totals(
    inputs: NutritionContract,
    daily_totals: Sequence[Mapping[str, Decimal]],
    policy: PlannerPolicy,
    *,
    template_ids: Sequence[str] = (),
    data_completeness: Mapping[str, Decimal] | None = None,
) -> tuple[str, ...]:
    if len(daily_totals) != 7:
        return ("INCOMPLETE_PLAN_WEEK",)
    codes = {code for day in daily_totals for code in day}
    average = {code: sum((day.get(code, ZERO) for day in daily_totals), ZERO) / 7 for code in codes}
    reasons = list(validate_nutrient_totals(inputs, average, policy))
    for day in daily_totals:
        reasons.extend(
            "DAILY_" + code for code in validate_nutrient_totals(inputs, day, policy, daily=True)
        )
    usage = Counter(template_ids)
    if any(count > inputs.maximum_meal_repetition_per_week for count in usage.values()):
        reasons.append("MEAL_REPETITION_LIMIT_EXCEEDED")
    # A substantial, reliably measured shortfall triggers review. This threshold
    # is an escalation policy, not an EAR, deficiency test, or minimum RDA.
    if data_completeness is not None and any(
        code != "sodium_mg"
        and data_completeness.get(code, ZERO) >= policy.micronutrient_data_completeness_threshold
        and average.get(code, ZERO) < target * policy.micronutrient_review_ratio
        for code, target in inputs.micronutrient_targets.items()
    ):
        reasons.append("MICRONUTRIENT_ADEQUACY_REVIEW_REQUIRED")
    return tuple(dict.fromkeys(reasons))
