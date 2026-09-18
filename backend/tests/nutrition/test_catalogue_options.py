from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.nutrition.enums import FoodMeasurementBasis, FoodVerificationStatus, MealCategory
from app.nutrition.models import (
    NutritionCatalogueFood,
    NutritionCatalogueFoodAlias,
    NutritionCatalogueMeal,
)


def _food(
    *,
    identifier: int,
    slug: str,
    name_fa: str,
    name_en: str,
    status: FoodVerificationStatus = FoodVerificationStatus.VERIFIED,
) -> NutritionCatalogueFood:
    return NutritionCatalogueFood(
        id=UUID(int=identifier),
        slug=slug,
        name_fa=name_fa,
        name_en=name_en,
        verification_status=status,
        source_name="test",
        source_reference="test://catalogue",
        category="test",
        measurement_basis=FoodMeasurementBasis.RAW,
        canonical_quantity=100,
        canonical_unit="g",
        edible_portion=1,
        data_version="test-v1",
        dietary_patterns=["omnivore"],
        allergen_tags=[],
        allergen_metadata_verified=False,
    )


@pytest.fixture
def seeded_catalogue_options(db: Session) -> dict[str, UUID]:
    verified_food = _food(
        identifier=1,
        slug="chicken",
        name_fa="مرغ",
        name_en="Chicken",
    )
    alias_food = _food(
        identifier=2,
        slug="grilled-chicken",
        name_fa="مرغ گریل‌شده",
        name_en="Grilled chicken",
    )
    draft_food = _food(
        identifier=3,
        slug="draft-chicken",
        name_fa="مرغ پیش‌نویس",
        name_en="Draft chicken",
        status=FoodVerificationStatus.DRAFT,
    )
    retired_food = _food(
        identifier=4,
        slug="retired-chicken",
        name_fa="مرغ بازنشسته",
        name_en="Retired chicken",
        status=FoodVerificationStatus.RETIRED,
    )
    verified_meal = NutritionCatalogueMeal(
        id=UUID(int=11),
        code="LU-CHICKEN",
        name_fa="برنج و مرغ",
        name_en="Chicken and rice",
        category=MealCategory.LUNCH,
        verification_status=FoodVerificationStatus.VERIFIED,
    )
    draft_meal = NutritionCatalogueMeal(
        id=UUID(int=12),
        code="LU-DRAFT",
        name_fa="وعده مرغ پیش‌نویس",
        name_en="Draft chicken meal",
        category=MealCategory.LUNCH,
        verification_status=FoodVerificationStatus.DRAFT,
    )
    retired_meal = NutritionCatalogueMeal(
        id=UUID(int=13),
        code="LU-RETIRED",
        name_fa="وعده مرغ بازنشسته",
        name_en="Retired chicken meal",
        category=MealCategory.LUNCH,
        verification_status=FoodVerificationStatus.RETIRED,
    )
    db.add_all(
        [
            verified_food,
            alias_food,
            draft_food,
            retired_food,
            verified_meal,
            draft_meal,
            retired_meal,
            NutritionCatalogueFoodAlias(
                food_id=alias_food.id,
                alias="جوجه",
                normalized_alias="جوجه",
                language="fa",
            ),
        ]
    )
    db.flush()
    return {
        "verified_food": verified_food.id,
        "alias_food": alias_food.id,
        "draft_food": draft_food.id,
        "retired_food": retired_food.id,
        "verified_meal": verified_meal.id,
        "draft_meal": draft_meal.id,
        "retired_meal": retired_meal.id,
    }


def test_catalogue_options_searches_verified_food_names_aliases_and_meals(
    client: TestClient,
    seeded_catalogue_options: dict[str, UUID],
) -> None:
    alias_response = client.get("/api/v1/nutrition/catalogue-options?q=جوجه")
    assert alias_response.status_code == 200
    assert alias_response.json()["items"][0] == {
        "target_type": "food",
        "target_id": str(seeded_catalogue_options["alias_food"]),
        "name_fa": "مرغ گریل‌شده",
        "name_en": "Grilled chicken",
        "category": "test",
        "image_url": None,
    }

    meal_response = client.get("/api/v1/nutrition/catalogue-options?q=Chicken%20and%20rice")
    assert meal_response.status_code == 200
    assert meal_response.json()["items"][0]["target_type"] == "meal"
    assert meal_response.json()["items"][0]["target_id"] == str(
        seeded_catalogue_options["verified_meal"]
    )


def test_catalogue_options_excludes_draft_and_retired_rows_and_honors_limit(
    client: TestClient,
    seeded_catalogue_options: dict[str, UUID],
) -> None:
    response = client.get("/api/v1/nutrition/catalogue-options?q=مرغ&limit=2")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    returned_ids = {item["target_id"] for item in items}
    assert str(seeded_catalogue_options["draft_food"]) not in returned_ids
    assert str(seeded_catalogue_options["retired_food"]) not in returned_ids
    assert str(seeded_catalogue_options["draft_meal"]) not in returned_ids
    assert str(seeded_catalogue_options["retired_meal"]) not in returned_ids
    assert all(set(item) == {
        "target_type",
        "target_id",
        "name_fa",
        "name_en",
        "category",
        "image_url",
    } for item in items)


def test_catalogue_options_prefix_ordering_is_stable(
    client: TestClient,
    seeded_catalogue_options: dict[str, UUID],
    db: Session,
) -> None:
    db.add(
        _food(
            identifier=20,
            slug="rice-with-chicken",
            name_fa="غذا با مرغ",
            name_en="Meal with chicken",
        )
    )
    db.flush()

    first = client.get("/api/v1/nutrition/catalogue-options?q=مرغ&limit=20")
    second = client.get("/api/v1/nutrition/catalogue-options?q=مرغ&limit=20")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["items"][0]["target_id"] == str(
        seeded_catalogue_options["verified_food"]
    )
