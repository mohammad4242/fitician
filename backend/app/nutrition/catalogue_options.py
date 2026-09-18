from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.nutrition.enums import FoodVerificationStatus
from app.nutrition.food_catalogue import normalize_food_alias
from app.nutrition.models import (
    NutritionCatalogueFood,
    NutritionCatalogueFoodAlias,
    NutritionCatalogueMeal,
)
from app.nutrition.schemas import (
    NutritionCatalogueOption,
    NutritionCatalogueOptionPageResponse,
)


@dataclass(frozen=True)
class _Option:
    target_type: str
    target_id: UUID
    name_fa: str
    name_en: str
    category: str | None
    image_url: str | None
    rank: int


def _normalized_column(column: Any) -> Any:
    return func.replace(func.replace(func.lower(column), "ي", "ی"), "ك", "ک")


def search_catalogue_options(
    db: Session,
    query: str,
    limit: int,
) -> NutritionCatalogueOptionPageResponse:
    normalized_query = normalize_food_alias(query)
    food_query = (
        select(NutritionCatalogueFood)
        .where(NutritionCatalogueFood.verification_status == FoodVerificationStatus.VERIFIED)
        .options(selectinload(NutritionCatalogueFood.aliases))
    )
    meal_query = (
        select(NutritionCatalogueMeal)
        .where(NutritionCatalogueMeal.verification_status == FoodVerificationStatus.VERIFIED)
    )
    if normalized_query:
        food_fields = (
            _normalized_column(NutritionCatalogueFood.name_fa),
            _normalized_column(NutritionCatalogueFood.name_en),
            _normalized_column(NutritionCatalogueFood.slug),
        )
        food_match = or_(
            *(field.contains(normalized_query, autoescape=True) for field in food_fields),
            NutritionCatalogueFood.aliases.any(
                NutritionCatalogueFoodAlias.normalized_alias.contains(
                    normalized_query, autoescape=True
                )
            ),
        )
        food_prefix = or_(
            *(field.startswith(normalized_query, autoescape=True) for field in food_fields),
            NutritionCatalogueFood.aliases.any(
                NutritionCatalogueFoodAlias.normalized_alias.startswith(
                    normalized_query, autoescape=True
                )
            ),
        )
        food_query = food_query.where(food_match).order_by(
            case((food_prefix, 0), else_=1),
            NutritionCatalogueFood.name_en,
            NutritionCatalogueFood.id,
        )
        meal_fields = (
            _normalized_column(NutritionCatalogueMeal.name_fa),
            _normalized_column(NutritionCatalogueMeal.name_en),
            _normalized_column(NutritionCatalogueMeal.code),
        )
        meal_match = or_(
            *(field.contains(normalized_query, autoescape=True) for field in meal_fields)
        )
        meal_prefix = or_(
            *(field.startswith(normalized_query, autoescape=True) for field in meal_fields)
        )
        meal_query = meal_query.where(meal_match).order_by(
            case((meal_prefix, 0), else_=1),
            NutritionCatalogueMeal.name_en,
            NutritionCatalogueMeal.id,
        )
    else:
        food_query = food_query.order_by(NutritionCatalogueFood.name_en, NutritionCatalogueFood.id)
        meal_query = meal_query.order_by(NutritionCatalogueMeal.name_en, NutritionCatalogueMeal.id)
    food_query = food_query.limit(limit)
    meal_query = meal_query.limit(limit)

    options = [
        _food_option(food, normalized_query)
        for food in db.scalars(food_query).unique().all()
    ]
    options.extend(
        _meal_option(meal, normalized_query)
        for meal in db.scalars(meal_query).all()
    )
    options.sort(
        key=lambda item: (
            item.rank,
            item.target_type,
            item.name_en.casefold(),
            str(item.target_id),
        )
    )
    return NutritionCatalogueOptionPageResponse(
        items=[
            NutritionCatalogueOption(
                target_type=item.target_type,
                target_id=item.target_id,
                name_fa=item.name_fa,
                name_en=item.name_en,
                category=item.category,
                image_url=item.image_url,
            )
            for item in options[:limit]
        ]
    )


def _food_option(food: NutritionCatalogueFood, query: str) -> _Option:
    values = (
        food.name_fa,
        food.name_en,
        food.slug,
        *(alias.normalized_alias for alias in food.aliases),
    )
    normalized_values = tuple(normalize_food_alias(value) for value in values)
    return _Option(
        target_type="food",
        target_id=food.id,
        name_fa=food.name_fa,
        name_en=food.name_en,
        category=food.category,
        image_url=food.image_path,
        rank=0 if query and any(value.startswith(query) for value in normalized_values) else 1,
    )


def _meal_option(meal: NutritionCatalogueMeal, query: str) -> _Option:
    values = tuple(normalize_food_alias(value) for value in (meal.name_fa, meal.name_en, meal.code))
    return _Option(
        target_type="meal",
        target_id=meal.id,
        name_fa=meal.name_fa,
        name_en=meal.name_en,
        category=meal.category.value,
        image_url=meal.image_path,
        rank=0 if query and any(value.startswith(query) for value in values) else 1,
    )
