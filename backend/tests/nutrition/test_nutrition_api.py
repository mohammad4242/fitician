from datetime import date
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.nutrition.models import (
    MedicalConditionPolicy,
    NutritionCatalogueFood,
    NutritionCatalogueMeal,
    NutritionFoodItem,
    NutritionMedicalCondition,
    NutritionMedication,
    NutritionProfile,
    NutritionSafetyDecision,
)
from app.profile.models import BodyMeasurement, UserProfile

ORIGIN = {"Origin": "http://localhost:5173"}


def register(client: TestClient, email: str) -> UUID:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": "long password"},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def select_nutrition_mode(client: TestClient) -> None:
    response = client.post(
        "/api/v1/profile/mode",
        headers=ORIGIN,
        json={"product_mode": "nutrition"},
    )
    assert response.status_code == 201


def adult_birth_date() -> str:
    today = date.today()
    return date(today.year - 25, today.month, min(today.day, 28)).isoformat()


def shared_payload(*, birth_date: str | None = None) -> dict[str, object]:
    return {
        "display_name": "  سارا  ",
        "birth_date": birth_date or adult_birth_date(),
        "sex": "female",
        "height_cm": 165,
        "current_weight_kg": 62.5,
        "fitness_goal": "maintain_weight",
    }


def standard_safety_payload() -> dict[str, object]:
    return {
        "conditions": [],
        "medications": [],
        "dangerous_food_reaction_history": False,
        "pregnant": False,
        "breastfeeding": False,
        "eating_disorder_diagnosed": False,
        "eating_disorder_active_symptoms": False,
        "emergency_or_danger_symptoms": False,
        "physician_dietary_restrictions": None,
        "other_relevant_condition": None,
    }


def nutrition_payload() -> dict[str, object]:
    return {
        "daily_activity_level": "moderate",
        "individual_monthly_food_budget_irr": 13_000_000,
        "budget_style": "strict",
        "meals_per_day": 3,
        "snacks_per_day": 1,
        "preferred_plan_start_day": "saturday",
        "plan_style": "balanced",
        "cooking_skill": "basic",
        "maximum_cooking_time_minutes": 45,
        "cooking_frequency_per_week": 4,
        "meal_preparation_preference": "mixed",
        "refrigerator_access": True,
        "freezer_access": True,
        "cooking_equipment": ["stove", "refrigerator"],
        "supplied_meals_per_week": 2,
        "supplied_meal_source": "محل کار",
        "foods_available_at_home": ["برنج", "عدس"],
        "favourite_foods": [],
        "disliked_foods": [],
        "never_suggest_foods": ["دل و جگر"],
        "refused_foods": ["سیرابی"],
        "allergies": [],
        "intolerances": [],
        "dietary_pattern": "omnivore",
        "religious_cultural_exclusions": ["الکل"],
        "preferred_variety": "medium",
        "maximum_meal_repetition_per_week": 2,
        "accepts_leftovers": True,
        "accepts_batch_cooking": True,
        "work_shift_context": "روزکار",
        "daily_check_in_enabled": True,
        "preferred_check_in_time": "21:30:00",
    }


def create_shared_and_safety(client: TestClient, email: str = "nutrition@example.com") -> UUID:
    user_id = register(client, email)
    select_nutrition_mode(client)
    shared = client.put("/api/v1/profile/shared", headers=ORIGIN, json=shared_payload())
    assert shared.status_code == 200
    safety = client.put(
        "/api/v1/nutrition/safety",
        headers=ORIGIN,
        json=standard_safety_payload(),
    )
    assert safety.status_code == 200
    return user_id


def test_under_18_shared_profile_is_rejected_with_stable_domain_error(
    client: TestClient,
    db: Session,
) -> None:
    user_id = register(client, "minor@example.com")
    select_nutrition_mode(client)
    today = date.today()
    minor_birth_date = date(today.year - 17, today.month, min(today.day, 28)).isoformat()

    response = client.put(
        "/api/v1/profile/shared",
        headers=ORIGIN,
        json=shared_payload(birth_date=minor_birth_date),
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "AGE_NOT_SUPPORTED"
    assert detail["message"] == "فیتیشن در حال حاضر برای افراد ۱۸ سال و بالاتر ارائه می‌شود."
    assert detail["retryable"] is False
    assert detail["meta"] == {}
    assert detail["request_id"]
    profile = db.get(UserProfile, user_id)
    assert profile is not None
    assert profile.birth_date is None
    assert db.scalar(select(BodyMeasurement).where(BodyMeasurement.user_id == user_id)) is None


def test_shared_profile_updates_the_single_source_of_truth(client: TestClient, db: Session) -> None:
    user_id = register(client, "shared@example.com")
    select_nutrition_mode(client)

    response = client.put(
        "/api/v1/profile/shared",
        headers=ORIGIN,
        json=shared_payload(),
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "سارا"
    assert response.json()["current_weight_kg"] == 62.5
    profile = db.get(UserProfile, user_id)
    assert profile is not None
    assert profile.display_name == "سارا"
    assert db.scalar(select(BodyMeasurement).where(BodyMeasurement.user_id == user_id)) is not None


@pytest.mark.parametrize(
    ("patch", "outcome", "can_continue"),
    [
        ({}, "standard_automatic", True),
        (
            {"conditions": [{"code": "controlled_hypertension", "details": "کنترل شده"}]},
            "automatic_draft_requires_physician_review",
            True,
        ),
        (
            {"conditions": [{"code": "kidney_disease", "details": None}]},
            "physician_manual_plan_required",
            False,
        ),
        (
            {"emergency_or_danger_symptoms": True},
            "unsupported_or_hard_blocked",
            False,
        ),
    ],
)
def test_early_safety_screen_returns_structured_versioned_outcomes(
    client: TestClient,
    patch: dict[str, object],
    outcome: str,
    can_continue: bool,
) -> None:
    register(client, f"{outcome}@example.com")
    select_nutrition_mode(client)
    assert (
        client.put("/api/v1/profile/shared", headers=ORIGIN, json=shared_payload()).status_code
        == 200
    )

    response = client.put(
        "/api/v1/nutrition/safety",
        headers=ORIGIN,
        json={**standard_safety_payload(), **patch},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["outcome"] == outcome
    assert result["policy_version"] == "medical-condition-v1"
    assert result["reason_codes"]
    assert result["can_continue_onboarding"] is can_continue
    assert result["requires_physician_review"] is (outcome != "standard_automatic")


def test_public_safety_preview_is_deterministic_and_does_not_persist(
    client: TestClient,
    db: Session,
) -> None:
    response = client.post(
        "/api/v1/nutrition/safety/evaluate",
        json={
            **standard_safety_payload(),
            "conditions": [{"code": "kidney_disease", "details": None}],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "physician_manual_plan_required",
        "policy_version": "medical-condition-v1",
        "reason_codes": ["kidney_disease"],
        "requires_physician_review": True,
        "can_continue_onboarding": False,
        "message": "برای حفظ ایمنی، برنامه غذایی باید توسط پزشک فیتیشن تنظیم شود.",
    }
    assert db.scalar(select(NutritionSafetyDecision)) is None


def test_safety_screen_normalizes_conditions_and_medications(
    client: TestClient,
    db: Session,
) -> None:
    user_id = register(client, "medical@example.com")
    select_nutrition_mode(client)
    assert (
        client.put("/api/v1/profile/shared", headers=ORIGIN, json=shared_payload()).status_code
        == 200
    )
    payload = {
        **standard_safety_payload(),
        "conditions": [{"code": "lipid_disorder", "details": "  تحت کنترل  "}],
        "medications": [{"name": "  داروی نمونه  ", "dosage": "روزانه", "notes": None}],
    }

    response = client.put("/api/v1/nutrition/safety", headers=ORIGIN, json=payload)

    assert response.status_code == 200
    conditions = db.scalars(
        select(NutritionMedicalCondition).where(NutritionMedicalCondition.user_id == user_id)
    ).all()
    medications = db.scalars(
        select(NutritionMedication).where(NutritionMedication.user_id == user_id)
    ).all()
    assert [(item.code.value, item.details) for item in conditions] == [
        ("lipid_disorder", "تحت کنترل")
    ]
    assert [(item.name, item.dosage) for item in medications] == [("داروی نمونه", "روزانه")]


def test_safety_reassessment_keeps_append_only_decisions(client: TestClient, db: Session) -> None:
    user_id = register(client, "safety-history@example.com")
    select_nutrition_mode(client)
    assert (
        client.put("/api/v1/profile/shared", headers=ORIGIN, json=shared_payload()).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/nutrition/safety", headers=ORIGIN, json=standard_safety_payload()
        ).status_code
        == 200
    )
    changed = client.put(
        "/api/v1/nutrition/safety",
        headers=ORIGIN,
        json={
            **standard_safety_payload(),
            "conditions": [{"code": "lipid_disorder", "details": None}],
        },
    )

    assert changed.status_code == 200
    assert changed.json()["outcome"] == "automatic_draft_requires_physician_review"
    decisions = db.scalars(
        select(NutritionSafetyDecision).where(NutritionSafetyDecision.user_id == user_id)
    ).all()
    assert len(decisions) == 2
    assert db.get(MedicalConditionPolicy, "medical-condition-v1") is not None


def test_nutrition_profile_persists_budget_and_normalized_food_constraints(
    client: TestClient,
    db: Session,
) -> None:
    user_id = create_shared_and_safety(client)

    response = client.put(
        "/api/v1/nutrition/profile",
        headers=ORIGIN,
        json=_canonical_profile_payload(db),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "IRR"
    assert body["daily_activity_level"] == "moderate"
    assert body["individual_monthly_food_budget_irr"] == 13_000_000
    assert body["weekly_budget_irr"] == 3_000_000
    assert body["allergies"] == []
    assert db.get(NutritionProfile, user_id) is not None
    items = db.scalars(select(NutritionFoodItem).where(NutritionFoodItem.user_id == user_id)).all()
    assert {item.kind.value for item in items} >= {"favourite", "disliked"}

    saved = client.get("/api/v1/nutrition/profile")
    assert saved.status_code == 200
    assert saved.json() == body
    status_response = client.get("/api/v1/profile/status")
    assert status_response.json()["completion_state"] == "nutrition_draft_ready"


def _canonical_preference_target_rows(
    db: Session,
) -> tuple[NutritionCatalogueFood, NutritionCatalogueMeal]:
    food = NutritionCatalogueFood(
        id=UUID(int=1001),
        slug="canonical-chicken",
        name_fa="مرغ canonical",
        name_en="Canonical chicken",
        verification_status="verified",
        source_name="test",
        source_reference="test://catalogue",
        category="protein",
        measurement_basis="raw",
        canonical_quantity=100,
        canonical_unit="g",
        edible_portion=1,
        data_version="test-v1",
        dietary_patterns=["omnivore"],
        allergen_tags=[],
        allergen_metadata_verified=False,
    )
    meal = NutritionCatalogueMeal(
        id=UUID(int=1002),
        code="CANONICAL-MEAL",
        name_fa="عدسی canonical",
        name_en="Canonical lentil meal",
        category="lunch",
        verification_status="verified",
    )
    db.add_all([food, meal])
    db.flush()
    return food, meal


def _canonical_profile_payload(
    db: Session,
    *,
    favourite: list[dict[str, str]] | None = None,
    disliked: list[dict[str, str]] | None = None,
    allergies: list[dict[str, object]] | None = None,
    intolerances: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    food = (
        db.query(NutritionCatalogueFood)
        .filter(NutritionCatalogueFood.slug == "canonical-chicken")
        .one_or_none()
    )
    meal = (
        db.query(NutritionCatalogueMeal)
        .filter(NutritionCatalogueMeal.code == "CANONICAL-MEAL")
        .one_or_none()
    )
    if food is None or meal is None:
        food, meal = _canonical_preference_target_rows(db)
    payload = nutrition_payload()
    payload.update(
        {
            "favourite_foods": [],
            "disliked_foods": [],
            "allergies": [],
            "intolerances": [],
            "favourite_catalogue_items": favourite
            if favourite is not None
            else [{"target_type": "food", "target_id": str(food.id)}],
            "disliked_catalogue_items": disliked
            if disliked is not None
            else [{"target_type": "meal", "target_id": str(meal.id)}],
            "allergy_catalogue_items": allergies or [],
            "intolerance_catalogue_items": intolerances or [],
        }
    )
    return payload


def test_canonical_food_and_meal_preferences_are_persisted_and_projected(
    client: TestClient,
    db: Session,
) -> None:
    user_id = create_shared_and_safety(client, "canonical-preferences@example.com")
    payload = _canonical_profile_payload(db)

    response = client.put("/api/v1/nutrition/profile", headers=ORIGIN, json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["favourite_catalogue_items"][0]["target_type"] == "food"
    assert body["favourite_catalogue_items"][0]["name_fa"] == "مرغ canonical"
    assert body["disliked_catalogue_items"][0]["target_type"] == "meal"
    assert body["disliked_catalogue_items"][0]["name_fa"] == "عدسی canonical"
    rows = db.query(NutritionFoodItem).filter(NutritionFoodItem.user_id == user_id).all()
    canonical_rows = [
        row
        for row in rows
        if row.catalogue_food_id is not None or row.catalogue_meal_id is not None
    ]
    assert len(canonical_rows) == 2
    assert all(
        (row.catalogue_food_id is None) != (row.catalogue_meal_id is None)
        for row in canonical_rows
    )


@pytest.mark.parametrize(
    ("target", "code"),
    [
        (
            {"target_type": "food", "target_id": "00000000-0000-0000-0000-000000009999"},
            "NUTRITION_CATALOGUE_TARGET_NOT_FOUND",
        ),
        (
            {"target_type": "food", "target_id": str(UUID(int=1002))},
            "NUTRITION_CATALOGUE_TARGET_TYPE_MISMATCH",
        ),
    ],
)
def test_canonical_preference_targets_are_database_validated(
    client: TestClient,
    db: Session,
    target: dict[str, str],
    code: str,
) -> None:
    create_shared_and_safety(client, f"invalid-target-{code}@example.com")
    payload = _canonical_profile_payload(db, favourite=[target])

    response = client.put("/api/v1/nutrition/profile", headers=ORIGIN, json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == code


def test_arbitrary_legacy_preference_text_is_rejected(client: TestClient, db: Session) -> None:
    create_shared_and_safety(client, "arbitrary-preference@example.com")
    payload = _canonical_profile_payload(db)
    payload.update(
        {
            "favourite_catalogue_items": [],
            "disliked_catalogue_items": [],
            "favourite_foods": ["پیتزای مخصوص محمد"],
        }
    )

    response = client.put("/api/v1/nutrition/profile", headers=ORIGIN, json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NUTRITION_CATALOGUE_TARGET_NOT_FOUND"


def test_invalid_catalogue_update_does_not_replace_existing_preferences(
    client: TestClient, db: Session
) -> None:
    create_shared_and_safety(client, "invalid-preference-update@example.com")
    payload = _canonical_profile_payload(db)
    saved = client.put("/api/v1/nutrition/profile", headers=ORIGIN, json=payload)
    assert saved.status_code == 200
    original_target_id = saved.json()["favourite_catalogue_items"][0]["target_id"]

    payload["favourite_catalogue_items"] = [
        {"target_type": "food", "target_id": "00000000-0000-0000-0000-000000009999"}
    ]
    rejected = client.put("/api/v1/nutrition/profile", headers=ORIGIN, json=payload)

    assert rejected.status_code == 422
    current = client.get("/api/v1/nutrition/profile", headers=ORIGIN)
    assert current.status_code == 200
    assert current.json()["favourite_catalogue_items"][0]["target_id"] == original_target_id


def test_duplicate_and_cross_kind_canonical_targets_are_rejected(
    client: TestClient,
    db: Session,
) -> None:
    create_shared_and_safety(client, "conflicting-preferences@example.com")
    _canonical_preference_target_rows(db)
    food = (
        db.query(NutritionCatalogueFood)
        .filter(NutritionCatalogueFood.slug == "canonical-chicken")
        .one()
    )
    payload = _canonical_profile_payload(
        db,
        favourite=[{"target_type": "food", "target_id": str(food.id)}],
        disliked=[{"target_type": "food", "target_id": str(food.id)}],
    )

    response = client.put("/api/v1/nutrition/profile", headers=ORIGIN, json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NUTRITION_PREFERENCE_CONFLICT"


def test_nutrition_profile_requires_completed_standard_or_reviewable_safety(
    client: TestClient,
) -> None:
    register(client, "unsafe-order@example.com")
    select_nutrition_mode(client)
    assert (
        client.put("/api/v1/profile/shared", headers=ORIGIN, json=shared_payload()).status_code
        == 200
    )

    missing = client.put("/api/v1/nutrition/profile", headers=ORIGIN, json=nutrition_payload())

    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "SAFETY_SCREEN_REQUIRED"


def test_current_safety_and_review_requirement_are_available_without_recalculation(
    client: TestClient,
    db: Session,
) -> None:
    user_id = register(client, "review-status@example.com")
    select_nutrition_mode(client)
    assert (
        client.put("/api/v1/profile/shared", headers=ORIGIN, json=shared_payload()).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/nutrition/safety",
            headers=ORIGIN,
            json={
                **standard_safety_payload(),
                "conditions": [{"code": "controlled_hypertension", "details": None}],
            },
        ).status_code
        == 200
    )

    safety = client.get("/api/v1/nutrition/safety")
    review = client.get("/api/v1/nutrition/review-requirement")

    assert safety.status_code == 200
    assert safety.json()["outcome"] == "automatic_draft_requires_physician_review"
    assert review.status_code == 200
    assert review.json() == {
        "required": True,
        "mode": "automatic_draft_review",
        "status": "not_requested",
        "safety_decision_id": safety.json()["id"],
    }
    assert (
        db.scalar(select(NutritionSafetyDecision).where(NutritionSafetyDecision.user_id == user_id))
        is not None
    )
    assert client.get("/api/v1/profile/status").json()["completion_state"] == (
        "medical_review_information_incomplete"
    )
    assert (
        client.put(
            "/api/v1/nutrition/profile", headers=ORIGIN, json=nutrition_payload()
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/profile/status").json()["completion_state"]
        == "nutrition_pending_review"
    )


def test_nutrition_mutations_require_authentication_and_trusted_origin(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/nutrition/profile").status_code == 401
    register(client, "origin@example.com")
    select_nutrition_mode(client)
    assert client.put("/api/v1/profile/shared", json=shared_payload()).status_code == 403
    assert client.put("/api/v1/nutrition/safety", json=standard_safety_payload()).status_code == 403


def test_nutrition_profile_draft_cannot_use_training_capabilities(client: TestClient) -> None:
    register(client, "nutrition-capability@example.com")
    select_nutrition_mode(client)

    exercises = client.get("/api/v1/exercises")
    workout = client.get("/api/v1/workout-plans/active")

    assert exercises.status_code == 403
    assert workout.status_code == 403


def test_target_weight_change_rate_flow(client: TestClient) -> None:
    register(client, "rate-flow@example.com")
    select_nutrition_mode(client)
    shared = shared_payload()
    shared["fitness_goal"] = "lose_weight"
    client.put("/api/v1/profile/shared", headers=ORIGIN, json=shared)
    client.put("/api/v1/nutrition/safety", headers=ORIGIN, json=standard_safety_payload())

    nut_payload = nutrition_payload()
    nut_payload["target_weight_change_kg_per_week"] = 0.5
    res = client.put("/api/v1/nutrition/profile", headers=ORIGIN, json=nut_payload)
    assert res.status_code == 200
    data = res.json()
    assert float(data["target_weight_change_kg_per_week"]) == 0.5

    client.put(
        "/api/v1/nutrition/structured-exercise",
        headers=ORIGIN,
        json={"trains": False},
    )

    # Generate estimate and verify rate snapshot
    est_res = client.post("/api/v1/nutrition/estimates", headers=ORIGIN)
    assert est_res.status_code == 201
    est_data = est_res.json()
    assert "input_snapshot" in est_data
    assert est_data["input_snapshot"]["requested_weight_change_kg_per_week"] == "0.5"
    assert est_data["input_snapshot"]["applied_weight_change_kg_per_week"] is not None


def test_target_weight_rate_user_override_flow(client: TestClient) -> None:
    register(client, "override-flow@example.com")
    select_nutrition_mode(client)
    shared = shared_payload()
    shared["fitness_goal"] = "lose_weight"
    client.put("/api/v1/profile/shared", headers=ORIGIN, json=shared)
    client.put("/api/v1/nutrition/safety", headers=ORIGIN, json=standard_safety_payload())

    nut_payload = nutrition_payload()
    nut_payload["target_weight_change_kg_per_week"] = 1.8
    nut_payload["weight_rate_mode"] = "user_override"
    res = client.put("/api/v1/nutrition/profile", headers=ORIGIN, json=nut_payload)
    assert res.status_code == 200
    data = res.json()
    assert float(data["target_weight_change_kg_per_week"]) == 1.8
    assert data["weight_rate_mode"] == "user_override"

    client.put(
        "/api/v1/nutrition/structured-exercise",
        headers=ORIGIN,
        json={"trains": False},
    )

    est_res = client.post("/api/v1/nutrition/estimates", headers=ORIGIN)
    assert est_res.status_code == 201
    est_data = est_res.json()
    assert est_data["input_snapshot"]["weight_rate_mode"] == "user_override"
    assert est_data["input_snapshot"]["requested_weight_change_kg_per_week"] == "1.8"
    assert est_data["input_snapshot"]["applied_weight_change_kg_per_week"] == "1.8"
