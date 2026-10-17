"""Hash mutable generation sources without retaining a new sensitive snapshot."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import cast
from uuid import UUID

from sqlalchemy import Table, select
from sqlalchemy.orm import Session

from app.nutrition import models
from app.profile.models import BodyMeasurement, UserProfile

# Generated plans themselves must never invalidate a retry. Only source inputs do.
_USER_SOURCES = (
    UserProfile,
    models.NutritionProfile,
    models.NutritionStructuredExercise,
    models.NutritionFoodItem,
    models.NutritionMealFeedback,
    models.NutritionConsumptionEntry,
    BodyMeasurement,
)
_CATALOGUE_SOURCES = (
    models.NutritionCatalogueFood,
    models.NutritionCatalogueFoodRole,
    models.NutritionFoodComposition,
    models.NutritionCatalogueMeal,
    models.NutritionCatalogueMealItem,
    models.NutritionPreparedRecipeRevision,
    models.NutritionPreparedRecipeIngredient,
    models.NutritionProgram,
    models.NutritionProgramDay,
    models.NutritionProgramSlot,
    models.NutritionFoodPriceReference,
    models.NutritionFoodPriceOverride,
)
_EXCLUDED = {
    "created_at",
    "updated_at",
    "display_name",
    "profile_photo_key",
    "note",
    "notes",
    "internal_notes",
}


def generation_source_fingerprint(
    db: Session, user_id: UUID, *, include_catalogue: bool = True
) -> str:
    material: dict[str, object] = {}
    # Select columns rather than ORM objects so cached identity-map state cannot
    # hide an input update committed while construction was running.
    sources = (*_USER_SOURCES, *_CATALOGUE_SOURCES) if include_catalogue else _USER_SOURCES
    for model in sources:
        table = cast(Table, model.__table__)
        columns = [column for column in table.columns if column.name not in _EXCLUDED]
        query = select(*columns).order_by(*table.primary_key.columns)
        if model in _USER_SOURCES:
            query = query.where(table.c.user_id == user_id)
        material[table.name] = [dict(row) for row in db.execute(query).mappings()]
    material["safety_decision"] = str(
        db.scalar(
            select(models.NutritionSafetyDecision.id)
            .where(models.NutritionSafetyDecision.user_id == user_id)
            .order_by(models.NutritionSafetyDecision.created_at.desc())
            .limit(1)
        )
    )
    return sha256(json.dumps(material, sort_keys=True, default=str).encode()).hexdigest()
