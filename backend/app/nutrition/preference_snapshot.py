"""Immutable, deterministic user preference data for nutrition planning."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select

from app.nutrition.enums import FoodItemKind
from app.nutrition.models import (
    NutritionConsumptionEntry,
    NutritionFoodItem,
    NutritionMealFeedback,
    NutritionWeeklyPlan,
    NutritionWeeklyPlanDay,
    NutritionWeeklyPlanMeal,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class PreferenceFeedback:
    meal_id: UUID
    feedback_type: str


@dataclass(frozen=True)
class PreferenceSnapshot:
    liked_food_ids: tuple[str, ...] = ()
    disliked_food_ids: tuple[str, ...] = ()
    liked_meal_ids: tuple[str, ...] = ()
    disliked_meal_ids: tuple[str, ...] = ()
    prefer_more_often_meal_ids: tuple[str, ...] = ()
    excluded_meal_ids: tuple[str, ...] = ()
    feedback_excluded_meal_ids: tuple[str, ...] = ()
    hard_excluded_food_ids: tuple[str, ...] = ()
    hard_excluded_meal_ids: tuple[str, ...] = ()
    allergy_food_ids: tuple[str, ...] = ()
    intolerance_food_ids: tuple[str, ...] = ()
    allergy_meal_ids: tuple[str, ...] = ()
    intolerance_meal_ids: tuple[str, ...] = ()
    historical_meal_adherence: tuple[tuple[str, Decimal], ...] = ()
    data_sufficient: bool = False


def preference_snapshot_signature(food_items: Iterable[NutritionFoodItem]) -> str:
    """Return a stable identity for profile preferences used by plan generation."""
    rows = [
        (
            item.kind.value,
            str(item.catalogue_food_id) if item.catalogue_food_id is not None else None,
            str(item.catalogue_meal_id) if item.catalogue_meal_id is not None else None,
            item.normalized_name,
            item.details,
        )
        for item in food_items
    ]
    rows.sort(key=lambda row: tuple("" if value is None else value for value in row))
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def build_preference_snapshot(
    *,
    liked_food_ids: Iterable[UUID | str] = (),
    disliked_food_ids: Iterable[UUID | str] = (),
    liked_meal_ids: Iterable[UUID | str] = (),
    disliked_meal_ids: Iterable[UUID | str] = (),
    feedback: Iterable[PreferenceFeedback] = (),
    prefer_more_often_meal_ids: Iterable[UUID | str] = (),
    feedback_excluded_meal_ids: Iterable[UUID | str] = (),
    hard_excluded_food_ids: Iterable[UUID | str] = (),
    hard_excluded_meal_ids: Iterable[UUID | str] = (),
    allergy_food_ids: Iterable[UUID | str] = (),
    intolerance_food_ids: Iterable[UUID | str] = (),
    allergy_meal_ids: Iterable[UUID | str] = (),
    intolerance_meal_ids: Iterable[UUID | str] = (),
    historical_meal_adherence: Iterable[tuple[UUID | str, Decimal]] = (),
    data_sufficient: bool | None = None,
) -> PreferenceSnapshot:
    feedback_rows = tuple(feedback)
    grouped: dict[str, list[str]] = {}
    for row in feedback_rows:
        grouped.setdefault(str(row.meal_id), []).append(row.feedback_type)

    def ids_for(kind: str) -> tuple[str, ...]:
        return tuple(sorted(meal_id for meal_id, kinds in grouped.items() if kind in kinds))

    liked_meals = _sorted_ids((*liked_meal_ids, *ids_for("liked")))
    disliked_meals = _sorted_ids((*disliked_meal_ids, *ids_for("disliked")))
    prefer_more_often = _sorted_ids(
        (*prefer_more_often_meal_ids, *ids_for("prefer_more_often"))
    )
    feedback_excluded = _sorted_ids(
        (*feedback_excluded_meal_ids, *ids_for("do_not_suggest_again"))
    )

    adherence = tuple(sorted((str(meal_id), score) for meal_id, score in historical_meal_adherence))
    return PreferenceSnapshot(
        liked_food_ids=_sorted_ids(liked_food_ids),
        disliked_food_ids=_sorted_ids(disliked_food_ids),
        liked_meal_ids=liked_meals,
        disliked_meal_ids=disliked_meals,
        prefer_more_often_meal_ids=prefer_more_often,
        excluded_meal_ids=feedback_excluded,
        feedback_excluded_meal_ids=feedback_excluded,
        hard_excluded_food_ids=_sorted_ids(hard_excluded_food_ids),
        hard_excluded_meal_ids=_sorted_ids(hard_excluded_meal_ids),
        allergy_food_ids=_sorted_ids(allergy_food_ids),
        intolerance_food_ids=_sorted_ids(intolerance_food_ids),
        allergy_meal_ids=_sorted_ids(allergy_meal_ids),
        intolerance_meal_ids=_sorted_ids(intolerance_meal_ids),
        historical_meal_adherence=adherence,
        data_sufficient=bool(adherence) if data_sufficient is None else data_sufficient,
    )


def load_preference_snapshot(
    db: Session,
    user_id: UUID,
    food_items: Iterable[NutritionFoodItem],
) -> PreferenceSnapshot:
    feedback = tuple(
        PreferenceFeedback(catalogue_meal_id, row.feedback_type.value)
        for row, catalogue_meal_id in db.execute(
            select(NutritionMealFeedback, NutritionWeeklyPlanMeal.catalogue_meal_id)
            .join(
                NutritionWeeklyPlanMeal,
                NutritionWeeklyPlanMeal.id == NutritionMealFeedback.meal_id,
            )
            .where(NutritionMealFeedback.user_id == user_id)
            .order_by(NutritionWeeklyPlanMeal.catalogue_meal_id)
        ).all()
        if catalogue_meal_id is not None
    )
    liked_food_ids = tuple(
        item.catalogue_food_id
        for item in food_items
        if item.catalogue_food_id is not None and item.kind is FoodItemKind.FAVOURITE
    )
    disliked_food_ids = tuple(
        item.catalogue_food_id
        for item in food_items
        if item.catalogue_food_id is not None and item.kind is FoodItemKind.DISLIKED
    )
    liked_meal_ids = tuple(
        item.catalogue_meal_id
        for item in food_items
        if item.catalogue_meal_id is not None and item.kind is FoodItemKind.FAVOURITE
    )
    disliked_meal_ids = tuple(
        item.catalogue_meal_id
        for item in food_items
        if item.catalogue_meal_id is not None and item.kind is FoodItemKind.DISLIKED
    )
    allergy_food_ids = tuple(
        item.catalogue_food_id
        for item in food_items
        if item.catalogue_food_id is not None and item.kind is FoodItemKind.ALLERGY
    )
    intolerance_food_ids = tuple(
        item.catalogue_food_id
        for item in food_items
        if item.catalogue_food_id is not None and item.kind is FoodItemKind.INTOLERANCE
    )
    allergy_meal_ids = tuple(
        item.catalogue_meal_id
        for item in food_items
        if item.catalogue_meal_id is not None and item.kind is FoodItemKind.ALLERGY
    )
    intolerance_meal_ids = tuple(
        item.catalogue_meal_id
        for item in food_items
        if item.catalogue_meal_id is not None and item.kind is FoodItemKind.INTOLERANCE
    )
    hard_excluded_food_ids = (*allergy_food_ids, *intolerance_food_ids)
    hard_excluded_meal_ids = (*allergy_meal_ids, *intolerance_meal_ids)
    planned = {
        str(meal_id): int(count)
        for meal_id, count in db.execute(
            select(NutritionWeeklyPlanMeal.catalogue_meal_id, func.count())
            .join(
                NutritionWeeklyPlanDay,
                NutritionWeeklyPlanDay.id == NutritionWeeklyPlanMeal.day_id,
            )
            .join(NutritionWeeklyPlan, NutritionWeeklyPlan.id == NutritionWeeklyPlanDay.plan_id)
            .where(
                NutritionWeeklyPlan.user_id == user_id,
                NutritionWeeklyPlanMeal.catalogue_meal_id.is_not(None),
            )
            .group_by(NutritionWeeklyPlanMeal.catalogue_meal_id)
        ).all()
        if meal_id is not None
    }
    consumed = {
        str(meal_id): int(count)
        for meal_id, count in db.execute(
            select(NutritionWeeklyPlanMeal.catalogue_meal_id, func.count())
            .join(
                NutritionConsumptionEntry,
                NutritionConsumptionEntry.planned_meal_id == NutritionWeeklyPlanMeal.id,
            )
            .where(
                NutritionConsumptionEntry.user_id == user_id,
                NutritionWeeklyPlanMeal.catalogue_meal_id.is_not(None),
            )
            .group_by(NutritionWeeklyPlanMeal.catalogue_meal_id)
        ).all()
        if meal_id is not None
    }
    historical = tuple(
        (
            meal_id,
            min(
                Decimal(consumed.get(meal_id, 0)) / Decimal(total),
                Decimal("1"),
            ),
        )
        for meal_id, total in planned.items()
        if total > 0
    )
    return build_preference_snapshot(
        liked_food_ids=liked_food_ids,
        disliked_food_ids=disliked_food_ids,
        liked_meal_ids=liked_meal_ids,
        disliked_meal_ids=disliked_meal_ids,
        feedback=feedback,
        hard_excluded_food_ids=hard_excluded_food_ids,
        hard_excluded_meal_ids=hard_excluded_meal_ids,
        allergy_food_ids=allergy_food_ids,
        intolerance_food_ids=intolerance_food_ids,
        allergy_meal_ids=allergy_meal_ids,
        intolerance_meal_ids=intolerance_meal_ids,
        historical_meal_adherence=historical,
        data_sufficient=sum(consumed.values()) >= 3,
    )


def _sorted_ids(values: Iterable[UUID | str]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values}))
