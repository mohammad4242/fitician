"""Resolve persisted dietary declarations against authoritative catalogue metadata."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.nutrition.enums import FoodItemKind
from app.nutrition.food_constraints import NormalizedFoodConstraint, normalize_food_constraints
from app.nutrition.models import NutritionCatalogueFood, NutritionCatalogueMeal, NutritionFoodItem


def constraints_for_items(
    db: Session,
    items: Sequence[NutritionFoodItem],
) -> tuple[NormalizedFoodConstraint, ...]:
    raw: list[dict[str, object]] = []
    for item in items:
        value: dict[str, object] = {
            "kind": item.kind.value,
            "term": item.name,
            "catalogue_food_id": item.catalogue_food_id,
            "catalogue_meal_id": item.catalogue_meal_id,
        }
        if item.kind in {FoodItemKind.ALLERGY, FoodItemKind.INTOLERANCE}:
            food = (
                db.get(NutritionCatalogueFood, item.catalogue_food_id)
                if item.catalogue_food_id
                else None
            )
            if food is not None:
                value["allergen_tags"] = (
                    list(food.allergen_tags) if food.allergen_metadata_verified else []
                )
            elif item.catalogue_meal_id:
                meal = db.get(NutritionCatalogueMeal, item.catalogue_meal_id)
                if meal is not None:
                    ingredient_foods = [ingredient.food for ingredient in meal.items]
                    if meal.prepared_recipe is not None:
                        for revision in meal.prepared_recipe.revisions:
                            if revision.verification_status.value == "verified":
                                ingredient_foods.extend(
                                    ingredient.food for ingredient in revision.ingredients
                                )
                    value["allergen_tags"] = sorted(
                        {tag for food in ingredient_foods for tag in food.allergen_tags}
                        if all(food.allergen_metadata_verified for food in ingredient_foods)
                        else set()
                    )
        raw.append(value)
    return normalize_food_constraints(raw)
