from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.nutrition.enums import (
    EstimateConfidence,
    MealSlotRole,
    NutritionConsumptionSource,
    NutritionPlanLifecycleStatus,
    NutritionPlanReviewStatus,
)
from app.nutrition.models import (
    NutritionCatalogueFood,
    NutritionConsumptionEntry,
    NutritionWeeklyPlan,
    NutritionWeeklyPlanMeal,
)
from app.user_activity.models import UserActivityEvent
from tests.nutrition.test_weekly_plan_api import (
    ORIGIN,
    _register_and_estimate,
    _seed_foods_and_prices,
)


def _setup(client: TestClient, db: Session) -> tuple[dict[str, object], NutritionCatalogueFood]:
    _register_and_estimate(client, db, "tracking-member@example.com")
    _seed_foods_and_prices(db)
    plan = client.post("/api/v1/nutrition/plans", headers=ORIGIN).json()["plan"]
    food = db.scalar(select(NutritionCatalogueFood).order_by(NutritionCatalogueFood.slug))
    assert food is not None
    return plan, food


def test_pending_plan_is_not_a_quick_check_in_baseline(client: TestClient, db: Session) -> None:
    plan, food = _setup(client, db)
    entry_date = plan["start_date"]

    blocked = client.put(
        "/api/v1/nutrition/tracking/check-in",
        headers=ORIGIN,
        json={"entry_date": entry_date, "status": "on_plan"},
    )
    manual = client.post(
        "/api/v1/nutrition/tracking/entries/catalogue",
        headers=ORIGIN,
        json={"entry_date": entry_date, "food_id": str(food.id), "grams": 125},
    )

    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "ACTIVE_PLAN_REQUIRED"
    assert manual.status_code == 201
    assert manual.json()["source"] == "catalogue_manual"
    assert manual.json()["user_confirmed"] is True


def test_on_plan_confirmation_prefills_and_pins_exact_active_revision(
    client: TestClient, db: Session
) -> None:
    plan_json, _food = _setup(client, db)
    plan = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan_json["id"]))
    assert plan is not None and plan.review is not None
    plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    plan.review.status = NutritionPlanReviewStatus.APPROVED
    db.flush()

    response = client.put(
        "/api/v1/nutrition/tracking/check-in",
        headers=ORIGIN,
        json={"entry_date": plan.start_date.isoformat(), "status": "on_plan"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["check_in_status"] == "on_plan"
    assert body["plan_revision_id"] == str(plan.id)
    assert body["data_status"] == "sufficient"
    assert body["entries"]
    assert all(entry["source"] == "planned_confirmed" for entry in body["entries"])
    assert all(entry["plan_revision_id"] == str(plan.id) for entry in body["entries"])
    event = db.scalar(
        select(UserActivityEvent).where(
            UserActivityEvent.user_id == plan.user_id,
            UserActivityEvent.event_type == "nutrition.daily_checkin",
        )
    )
    assert event is not None
    assert event.resource_id
    assert event.safe_metadata == {"date": plan.start_date.isoformat()}


@pytest.mark.parametrize("status", ["on_plan", "mostly_on_plan"])
def test_check_in_with_free_meal_prefills_only_normal_meals(
    client: TestClient, db: Session, status: str
) -> None:
    plan_json, _food = _setup(client, db)
    plan = db.get(NutritionWeeklyPlan, plan_json["id"])
    assert plan is not None and plan.review is not None
    plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    plan.review.status = NutritionPlanReviewStatus.APPROVED
    day = plan.days[0]
    free_meal = NutritionWeeklyPlanMeal(
        day_id=day.id,
        catalogue_meal_id=None,
        catalogue_meal_category="lunch",
        slot_role=MealSlotRole.FREE_MEAL,
        slot_index=0,
        target_distribution={},
        nutrient_totals={},
        cost_irr=0,
    )
    db.add(free_meal)
    db.commit()
    normal_meal_ids = {
        meal.id for meal in day.meals if meal.slot_role is not MealSlotRole.FREE_MEAL
    }

    response = client.put(
        "/api/v1/nutrition/tracking/check-in",
        headers=ORIGIN,
        json={"entry_date": day.plan_date.isoformat(), "status": status},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["check_in_status"] == status
    assert body["plan_revision_id"] == str(plan.id)
    entries = db.scalars(
        select(NutritionConsumptionEntry).where(
            NutritionConsumptionEntry.user_id == plan.user_id,
            NutritionConsumptionEntry.entry_date == day.plan_date,
        )
    ).all()
    planned_entries = [
        entry for entry in entries if entry.source is NutritionConsumptionSource.PLANNED_CONFIRMED
    ]
    assert {entry.planned_meal_id for entry in planned_entries} == normal_meal_ids
    assert all(entry.planned_meal_id != free_meal.id for entry in planned_entries)
    assert all(entry.quantity_grams is None or entry.quantity_grams > 0 for entry in entries)


def test_quick_approximation_is_explicitly_low_confidence_and_deletable(
    client: TestClient, db: Session
) -> None:
    _setup(client, db)
    created = client.post(
        "/api/v1/nutrition/tracking/entries/quick",
        headers=ORIGIN,
        json={
            "entry_date": date.today().isoformat(),
            "display_name": "یک وعده متوسط",
            "calories": 550,
            "protein_g": 25,
        },
    )
    assert created.status_code == 201
    assert created.json()["confidence"] == "low"
    assert created.json()["warning_codes"] == ["APPROXIMATE_INTAKE"]

    deleted = client.delete(
        f"/api/v1/nutrition/tracking/entries/{created.json()['id']}", headers=ORIGIN
    )
    summary = client.get(f"/api/v1/nutrition/tracking/days/{date.today().isoformat()}")
    assert deleted.status_code == 204
    assert summary.json()["data_status"] == "insufficient_data"


def test_free_meal_macros_update_actual_totals_without_changing_plan_targets(
    client: TestClient,
    db: Session,
) -> None:
    plan_json, _food = _setup(client, db)
    plan = db.get(NutritionWeeklyPlan, plan_json["id"])
    assert plan is not None and plan.review is not None
    plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    plan.review.status = NutritionPlanReviewStatus.APPROVED
    day = plan.days[0]
    planned_targets = dict(day.nutrient_totals)
    free_meal = NutritionWeeklyPlanMeal(
        day_id=day.id,
        catalogue_meal_id=None,
        catalogue_meal_category="lunch",
        slot_role=MealSlotRole.FREE_MEAL,
        slot_index=0,
        target_distribution={},
        nutrient_totals={},
        cost_irr=0,
    )
    db.add(free_meal)
    db.commit()

    payload = {
        "entry_date": day.plan_date.isoformat(),
        "calories": 720,
        "protein_g": 38,
        "carbohydrate_g": 82,
        "fat_g": 24,
    }
    first = client.put(
        f"/api/v1/nutrition/tracking/free-meals/{free_meal.id}",
        headers=ORIGIN,
        json=payload,
    )
    second = client.put(
        f"/api/v1/nutrition/tracking/free-meals/{free_meal.id}",
        headers=ORIGIN,
        json={**payload, "calories": 700},
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert second.json()["actual_totals"] == {
        "energy_kcal": 700,
        "protein_g": 38,
        "carbohydrate_g": 82,
        "total_fat_g": 24,
    }
    assert len(second.json()["entries"]) == 1
    assert second.json()["entries"][0]["source"] == "free_meal"
    db.refresh(day)
    assert day.nutrient_totals == planned_targets


def test_free_meal_recurs_on_day_8_and_rejects_wrong_meal(client: TestClient, db: Session) -> None:
    plan_json, _food = _setup(client, db)
    plan = db.get(NutritionWeeklyPlan, plan_json["id"])
    assert plan is not None and plan.review is not None
    plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    plan.review.status = NutritionPlanReviewStatus.APPROVED
    day = plan.days[0]
    free_meal = NutritionWeeklyPlanMeal(
        day_id=day.id,
        catalogue_meal_id=None,
        catalogue_meal_category="lunch",
        slot_role=MealSlotRole.FREE_MEAL,
        slot_index=0,
        target_distribution={},
        nutrient_totals={},
        cost_irr=0,
    )
    db.add(free_meal)
    db.commit()

    payload = {
        "calories": 700,
        "protein_g": 30,
        "carbohydrate_g": 80,
        "fat_g": 25,
    }
    responses = [
        client.put(
            f"/api/v1/nutrition/tracking/free-meals/{free_meal.id}",
            headers=ORIGIN,
            json={
                **payload,
                "entry_date": (plan.start_date + timedelta(days=offset)).isoformat(),
            },
        )
        for offset in (7, 14)
    ]
    non_free_meal = next(meal for meal in day.meals if meal.slot_role is not MealSlotRole.FREE_MEAL)
    wrong = client.put(
        f"/api/v1/nutrition/tracking/free-meals/{non_free_meal.id}",
        headers=ORIGIN,
        json={**payload, "entry_date": (plan.start_date + timedelta(days=7)).isoformat()},
    )

    assert [response.status_code for response in responses] == [200, 200]
    assert wrong.status_code == 404
    assert wrong.json()["detail"]["code"] == "ACTIVE_FREE_MEAL_NOT_FOUND"


def test_member_can_edit_own_catalogue_entry_and_read_recent_foods(
    client: TestClient,
    db: Session,
) -> None:
    _plan, food = _setup(client, db)
    created = client.post(
        "/api/v1/nutrition/tracking/entries/catalogue",
        headers=ORIGIN,
        json={
            "entry_date": date.today().isoformat(),
            "food_id": str(food.id),
            "grams": 100,
        },
    )
    original_energy = created.json()["nutrients"]["energy_kcal"]

    edited = client.put(
        f"/api/v1/nutrition/tracking/entries/{created.json()['id']}",
        headers=ORIGIN,
        json={"grams": 200, "note": "مقدار واقعی"},
    )
    recent = client.get("/api/v1/nutrition/tracking/recent-foods")

    assert edited.status_code == 200, edited.text
    assert edited.json()["quantity_grams"] == 200
    assert edited.json()["nutrients"]["energy_kcal"] == original_energy * 2
    assert edited.json()["note"] == "مقدار واقعی"
    assert recent.status_code == 200
    assert recent.json()[0]["food_id"] == str(food.id)
    assert recent.json()[0]["last_quantity_grams"] == 200


def test_member_edit_scales_confirmed_photo_estimate_without_catalogue_food(
    client: TestClient,
    db: Session,
) -> None:
    plan_json, _food = _setup(client, db)
    plan = db.get(NutritionWeeklyPlan, plan_json["id"])
    assert plan is not None
    entry = NutritionConsumptionEntry(
        user_id=plan.user_id,
        entry_date=date.today(),
        display_name="غذای ثبت‌شده از عکس",
        quantity_grams=Decimal("80"),
        source=NutritionConsumptionSource.PHOTO_ESTIMATED_CONFIRMED,
        confidence=EstimateConfidence.MEDIUM,
        user_confirmed=True,
        nutrients={
            "energy_kcal": "160",
            "protein_g": "12",
            "carbohydrate_g": "20",
            "total_fat_g": "4",
        },
        warning_codes=["PHOTO_ESTIMATE_APPROXIMATE"],
    )
    db.add(entry)
    db.commit()

    edited = client.put(
        f"/api/v1/nutrition/tracking/entries/{entry.id}",
        headers=ORIGIN,
        json={"grams": 120},
    )
    summary = client.get(f"/api/v1/nutrition/tracking/days/{date.today().isoformat()}")

    assert edited.status_code == 200, edited.text
    assert edited.json()["quantity_grams"] == 120
    assert edited.json()["source"] == NutritionConsumptionSource.PHOTO_ESTIMATED_EDITED.value
    assert edited.json()["nutrients"] == {
        "energy_kcal": 240,
        "protein_g": 18,
        "carbohydrate_g": 30,
        "total_fat_g": 6,
    }
    assert edited.json()["warning_codes"] == ["PHOTO_ESTIMATE_APPROXIMATE"]
    assert summary.status_code == 200
    assert summary.json()["actual_totals"]["energy_kcal"] == 240


def test_member_edit_preserves_photo_warning_for_catalogue_backed_estimate(
    client: TestClient,
    db: Session,
) -> None:
    plan_json, food = _setup(client, db)
    plan = db.get(NutritionWeeklyPlan, plan_json["id"])
    assert plan is not None
    entry = NutritionConsumptionEntry(
        user_id=plan.user_id,
        entry_date=date.today(),
        food_id=food.id,
        display_name=food.name_fa,
        quantity_grams=Decimal("80"),
        source=NutritionConsumptionSource.PHOTO_ESTIMATED_CONFIRMED,
        confidence=EstimateConfidence.MEDIUM,
        user_confirmed=True,
        nutrients={"energy_kcal": "160"},
        warning_codes=["PHOTO_ESTIMATE_APPROXIMATE"],
    )
    db.add(entry)
    db.commit()

    edited = client.put(
        f"/api/v1/nutrition/tracking/entries/{entry.id}",
        headers=ORIGIN,
        json={"grams": 120},
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["source"] == NutritionConsumptionSource.PHOTO_ESTIMATED_EDITED.value
    assert "PHOTO_ESTIMATE_APPROXIMATE" in edited.json()["warning_codes"]


def test_member_can_adjust_and_skip_planned_meal_on_active_revision(
    client: TestClient,
    db: Session,
) -> None:
    plan_json, _food = _setup(client, db)
    plan = db.get(NutritionWeeklyPlan, plan_json["id"])
    assert plan is not None and plan.review is not None
    plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    plan.review.status = NutritionPlanReviewStatus.APPROVED
    db.flush()
    meal = plan_json["days"][0]["meals"][0]
    payload = {
        "entry_date": plan.start_date.isoformat(),
        "status": "adjusted",
        "portion_ratio": 0.5,
    }

    adjusted = client.put(
        f"/api/v1/nutrition/tracking/planned-meals/{meal['id']}",
        headers=ORIGIN,
        json=payload,
    )
    skipped = client.put(
        f"/api/v1/nutrition/tracking/planned-meals/{meal['id']}",
        headers=ORIGIN,
        json={**payload, "status": "skipped", "portion_ratio": None},
    )

    assert adjusted.status_code == 200, adjusted.text
    adjusted_entry = next(
        item for item in adjusted.json()["entries"] if item["planned_meal_id"] == meal["id"]
    )
    assert adjusted_entry["source"] == "planned_adjusted"
    assert (
        adjusted_entry["nutrients"]["energy_kcal"] == meal["nutrient_totals"]["energy_kcal"] * 0.5
    )
    assert skipped.status_code == 200
    assert all(item["planned_meal_id"] != meal["id"] for item in skipped.json()["entries"])


def test_off_plan_check_in_keeps_edited_meal_when_changed_to_on_plan(
    client: TestClient, db: Session
) -> None:
    plan_json, _food = _setup(client, db)
    plan = db.get(NutritionWeeklyPlan, plan_json["id"])
    assert plan is not None and plan.review is not None
    plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    plan.review.status = NutritionPlanReviewStatus.APPROVED
    db.commit()
    entry_date = plan.start_date.isoformat()
    meals = plan_json["days"][0]["meals"]
    edited_meal_id = meals[0]["id"]

    first = client.put(
        "/api/v1/nutrition/tracking/check-in",
        headers=ORIGIN,
        json={"entry_date": entry_date, "status": "off_plan"},
    )
    assert first.status_code == 200, first.text
    edited = client.put(
        f"/api/v1/nutrition/tracking/planned-meals/{edited_meal_id}",
        headers=ORIGIN,
        json={"entry_date": entry_date, "status": "adjusted", "portion_ratio": 0.5},
    )
    assert edited.status_code == 200, edited.text
    original_entry = next(
        item for item in edited.json()["entries"] if item["planned_meal_id"] == edited_meal_id
    )
    assert original_entry["source"] == "planned_adjusted"

    changed = client.put(
        "/api/v1/nutrition/tracking/check-in",
        headers=ORIGIN,
        json={"entry_date": entry_date, "status": "on_plan"},
    )
    assert changed.status_code == 200, changed.text
    body = changed.json()
    entries_by_meal = {item["planned_meal_id"]: item for item in body["entries"]}
    assert body["plan_revision_id"] == str(plan.id)
    assert entries_by_meal[edited_meal_id] == original_entry
    assert all(meal["id"] in entries_by_meal for meal in meals)
