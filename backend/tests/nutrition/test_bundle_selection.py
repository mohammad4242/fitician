from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.enums import AccessPackageCode
from app.entitlements.exceptions import EntitlementQuotaExceededError
from app.entitlements.models import EntitlementUsageEvent
from app.nutrition.enums import (
    NutritionPlanBudgetStatus,
    NutritionPlanLifecycleStatus,
    NutritionPlanRole,
)
from app.nutrition.exceptions import (
    PlanSelectionInvalidError,
    WeeklyPlanBundleNotFoundError,
)
from app.nutrition.models import (
    NutritionEstimate,
    NutritionPlanBundle,
    NutritionPlanGeneration,
    NutritionSafetyDecision,
    NutritionWeeklyPlan,
)
from app.nutrition.plan_editing import confirm_replace_meal
from app.nutrition.plan_service import (
    latest_plan_bundle,
    latest_weekly_plan,
    select_bundle_plan,
)
from app.nutrition.planner_policy import PLANNER_POLICY_VERSION, PLANNER_VERSION
from tests.nutrition.test_weekly_plan_api import (
    ORIGIN,
    _register_and_estimate,
    _seed_foods_and_prices,
)


def _seed_test_bundle(
    client: TestClient,
    db: Session,
    *,
    package: AccessPackageCode = AccessPackageCode.NUTRITION,
) -> tuple[User, NutritionPlanBundle, NutritionWeeklyPlan, NutritionWeeklyPlan]:
    email = f"bundle_test_{uuid4().hex[:8]}@example.com"
    _register_and_estimate(client, db, email, meals=3, snacks=1, package=package)
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    user_id = user.id
    safety = db.scalar(
        select(NutritionSafetyDecision)
        .where(NutritionSafetyDecision.user_id == user_id)
        .order_by(NutritionSafetyDecision.revision.desc())
    )
    assert safety is not None

    estimate = db.scalar(
        select(NutritionEstimate)
        .where(NutritionEstimate.user_id == user_id)
        .order_by(NutritionEstimate.revision.desc())
    )
    assert estimate is not None

    bundle = NutritionPlanBundle(
        user_id=user_id,
        estimate_id=estimate.id,
        comparison_snapshot={"meaningful_quality_improvement": True},
    )
    db.add(bundle)
    db.flush()

    budget_gen = NutritionPlanGeneration(
        user_id=user_id,
        safety_decision_id=safety.id,
        estimate_id=estimate.id,
        bundle_id=bundle.id,
        plan_role=NutritionPlanRole.BUDGET.value,
        outcome="success",
        reason_codes=[],
        warning_codes=[],
        input_signature="sig-budget",
        input_snapshot={},
        diagnostic_snapshot={},
        planner_policy_version=PLANNER_POLICY_VERSION,
        planner_version=PLANNER_VERSION,
    )
    db.add(budget_gen)
    db.flush()

    budget_plan = NutritionWeeklyPlan(
        user_id=user_id,
        generation_id=budget_gen.id,
        estimate_id=estimate.id,
        safety_decision_id=safety.id,
        revision=1,
        lifecycle_status=NutritionPlanLifecycleStatus.PENDING_PHYSICIAN_REVIEW,
        is_user_visible=True,
        start_date=date.today(),
        planner_policy_version=PLANNER_POLICY_VERSION,
        planner_version=PLANNER_VERSION,
        scientific_policy_version="sc-v1",
        formula_version="fm-v1",
        food_data_manifest={},
        input_snapshot={},
        price_snapshot={},
        repair_snapshot=[],
        warning_codes=[],
        explanation_codes=[],
        weekly_cost_irr=35_000_000,
        weekly_budget_irr=35_000_000,
        budget_status=NutritionPlanBudgetStatus.WITHIN_BUDGET,
    )
    db.add(budget_plan)

    ideal_gen = NutritionPlanGeneration(
        user_id=user_id,
        safety_decision_id=safety.id,
        estimate_id=estimate.id,
        bundle_id=bundle.id,
        plan_role=NutritionPlanRole.IDEAL_REFERENCE.value,
        outcome="success",
        reason_codes=[],
        warning_codes=[],
        input_signature="sig-ideal",
        input_snapshot={},
        diagnostic_snapshot={},
        planner_policy_version=PLANNER_POLICY_VERSION,
        planner_version=PLANNER_VERSION,
    )
    db.add(ideal_gen)
    db.flush()

    ideal_plan = NutritionWeeklyPlan(
        user_id=user_id,
        generation_id=ideal_gen.id,
        estimate_id=estimate.id,
        safety_decision_id=safety.id,
        revision=2,
        lifecycle_status=NutritionPlanLifecycleStatus.GENERATED,
        is_user_visible=True,
        start_date=date.today(),
        planner_policy_version=PLANNER_POLICY_VERSION,
        planner_version=PLANNER_VERSION,
        scientific_policy_version="sc-v1",
        formula_version="fm-v1",
        food_data_manifest={},
        input_snapshot={},
        price_snapshot={},
        repair_snapshot=[],
        warning_codes=[],
        explanation_codes=[],
        weekly_cost_irr=45_000_000,
        weekly_budget_irr=35_000_000,
        budget_status=NutritionPlanBudgetStatus.OVER_BUDGET,
    )
    db.add(ideal_plan)
    db.flush()

    bundle.selected_plan_id = budget_plan.id
    bundle.selected_plan_role = NutritionPlanRole.BUDGET.value
    bundle.selected_at = datetime.now(UTC)
    db.commit()

    return user, bundle, budget_plan, ideal_plan


def test_bundle_initial_state_defaults_to_budget(client: TestClient, db: Session) -> None:
    user, bundle, budget_plan, ideal_plan = _seed_test_bundle(client, db)

    assert bundle.selected_plan_id == budget_plan.id
    assert bundle.selected_plan_role == NutritionPlanRole.BUDGET.value
    assert bundle.selected_at is not None

    latest = latest_weekly_plan(db, user.id)
    assert latest.id == budget_plan.id
    assert latest.revision == 1


def test_select_bundle_plan_by_id(client: TestClient, db: Session) -> None:
    user, bundle, budget_plan, ideal_plan = _seed_test_bundle(client, db)

    response = select_bundle_plan(
        db,
        user_id=user.id,
        bundle_id=bundle.id,
        plan_id=ideal_plan.id,
    )
    assert response.selected_plan_id == ideal_plan.id
    assert response.selected_plan_role == NutritionPlanRole.IDEAL_REFERENCE.value

    refreshed_bundle = db.get(NutritionPlanBundle, bundle.id)
    assert refreshed_bundle is not None
    assert refreshed_bundle.selected_plan_id == ideal_plan.id
    assert refreshed_bundle.selected_plan_role == NutritionPlanRole.IDEAL_REFERENCE.value

    latest = latest_weekly_plan(db, user.id)
    assert latest.id == ideal_plan.id
    assert latest.revision == 2


def test_editing_selected_plan_tracks_revision_and_preserves_bundle_candidates(
    client: TestClient, db: Session
) -> None:
    _register_and_estimate(
        client,
        db,
        "valid-bundle-edit@example.com",
        meals=2,
        snacks=1,
        package=AccessPackageCode.NUTRITION,
    )
    _seed_foods_and_prices(db)
    response = client.post("/api/v1/nutrition/plans", headers=ORIGIN)
    assert response.status_code == 201, response.text
    body = response.json()
    budget_plan = db.get(NutritionWeeklyPlan, body["budget_plan"]["id"])
    ideal_plan = db.get(NutritionWeeklyPlan, body["ideal_plan"]["id"])
    user = db.get(User, budget_plan.user_id)
    bundle = db.get(NutritionPlanBundle, budget_plan.generation.bundle_id)
    bundle_id = bundle.id
    selected_role = bundle.selected_plan_role
    selected_at = bundle.selected_at
    comparison_snapshot = dict(bundle.comparison_snapshot or {})
    budget_plan.lifecycle_status = NutritionPlanLifecycleStatus.READY_TO_START
    meal = budget_plan.days[0].meals[0]
    replacement = next(
        candidate
        for day in budget_plan.days
        for candidate in day.meals
        if candidate.id != meal.id
        and candidate.catalogue_meal_id == meal.catalogue_meal_id
        and candidate.nutrient_totals == meal.nutrient_totals
    )
    revision = confirm_replace_meal(
        db, user.id, budget_plan.id, budget_plan.id, meal.id, replacement.id
    )

    db.refresh(bundle)
    assert revision.id != budget_plan.id
    revised_plan = db.get(NutritionWeeklyPlan, revision.id)
    assert revised_plan is not None
    revision_generation = db.get(NutritionPlanGeneration, revised_plan.generation_id)
    assert revision_generation is not None and revision_generation.bundle_id is None
    assert bundle.selected_plan_id == revision.id
    assert bundle.selected_plan_role == selected_role
    assert bundle.selected_at == selected_at
    assert bundle.comparison_snapshot == comparison_snapshot
    assert bundle.id == bundle_id
    assert latest_weekly_plan(db, user.id).id == revision.id

    latest_bundle = latest_plan_bundle(db, user.id)
    assert latest_bundle is not None
    assert latest_bundle.selected_plan_id == revision.id
    assert latest_bundle.selected_plan_role == selected_role
    assert latest_bundle.plan is not None and latest_bundle.plan.id == revision.id
    assert latest_bundle.budget_plan is not None and latest_bundle.budget_plan.id == budget_plan.id
    assert latest_bundle.ideal_plan is not None and latest_bundle.ideal_plan.id == ideal_plan.id


def test_select_bundle_plan_by_role(client: TestClient, db: Session) -> None:
    user, bundle, budget_plan, ideal_plan = _seed_test_bundle(client, db)

    res1 = select_bundle_plan(
        db,
        user_id=user.id,
        bundle_id=bundle.id,
        plan_role=NutritionPlanRole.IDEAL_REFERENCE.value,
    )
    assert res1.selected_plan_id == ideal_plan.id

    res2 = select_bundle_plan(
        db,
        user_id=user.id,
        bundle_id=bundle.id,
        plan_role=NutritionPlanRole.BUDGET.value,
    )
    assert res2.selected_plan_id == budget_plan.id
    assert res2.selected_plan_role == NutritionPlanRole.BUDGET.value

    latest = latest_weekly_plan(db, user.id)
    assert latest.id == budget_plan.id


def test_select_bundle_plan_scoping_and_authorization(client: TestClient, db: Session) -> None:
    user, bundle, budget_plan, ideal_plan = _seed_test_bundle(client, db)

    other_user_id = uuid4()
    with pytest.raises(WeeklyPlanBundleNotFoundError):
        select_bundle_plan(
            db,
            user_id=other_user_id,
            bundle_id=bundle.id,
            plan_id=ideal_plan.id,
        )

    with pytest.raises(PlanSelectionInvalidError):
        select_bundle_plan(
            db,
            user_id=user.id,
            bundle_id=bundle.id,
            plan_id=uuid4(),
        )

    with pytest.raises(PlanSelectionInvalidError):
        select_bundle_plan(
            db,
            user_id=user.id,
            bundle_id=bundle.id,
            plan_role="non_existent_role",
        )


def test_select_bundle_plan_api_endpoint(client: TestClient, db: Session) -> None:
    user, bundle, budget_plan, ideal_plan = _seed_test_bundle(client, db)
    origin = {"Origin": "http://localhost:5173"}

    # Select ideal_plan
    resp = client.post(
        f"/api/v1/nutrition/plan-bundles/{bundle.id}/select",
        json={"plan_id": str(ideal_plan.id)},
        headers=origin,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["selected_plan_id"] == str(ideal_plan.id)
    assert data["selected_plan_role"] == NutritionPlanRole.IDEAL_REFERENCE.value

    # Select budget_plan by role
    resp = client.post(
        f"/api/v1/nutrition/plan-bundles/{bundle.id}/select",
        json={"plan_role": NutritionPlanRole.BUDGET.value},
        headers=origin,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["selected_plan_id"] == str(budget_plan.id)
    assert data["selected_plan_role"] == NutritionPlanRole.BUDGET.value

    # Invalid bundle ID
    resp = client.post(
        f"/api/v1/nutrition/plan-bundles/{uuid4()}/select",
        json={"plan_id": str(ideal_plan.id)},
        headers=origin,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "PLAN_BUNDLE_NOT_FOUND"

    # Invalid plan ID
    resp = client.post(
        f"/api/v1/nutrition/plan-bundles/{bundle.id}/select",
        json={"plan_id": str(uuid4())},
        headers=origin,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "PLAN_SELECTION_INVALID"


def test_select_bundle_plan_archives_unselected_plan(client: TestClient, db: Session) -> None:
    user, bundle, budget_plan, ideal_plan = _seed_test_bundle(client, db)

    # Select ideal_plan
    select_bundle_plan(
        db,
        user_id=user.id,
        bundle_id=bundle.id,
        plan_id=ideal_plan.id,
    )

    db.refresh(ideal_plan)
    db.refresh(budget_plan)

    assert ideal_plan.is_user_visible is True
    assert ideal_plan.lifecycle_status == NutritionPlanLifecycleStatus.READY_TO_START

    # Budget plan should be archived and hidden from user
    assert budget_plan.is_user_visible is False
    assert budget_plan.lifecycle_status == NutritionPlanLifecycleStatus.ARCHIVED


def test_physician_review_is_created_only_for_selected_final_plan(
    client: TestClient, db: Session
) -> None:
    user, bundle, budget_plan, ideal_plan = _seed_test_bundle(
        client,
        db,
        package=AccessPackageCode.NUTRITION_PHYSICIAN,
    )

    selected = select_bundle_plan(
        db,
        user_id=user.id,
        bundle_id=bundle.id,
        plan_id=ideal_plan.id,
        physician_review_allowed=True,
    )

    assert selected.plan.physician_review_required is True
    db.refresh(ideal_plan)
    db.refresh(budget_plan)
    assert ideal_plan.lifecycle_status == NutritionPlanLifecycleStatus.PENDING_PHYSICIAN_REVIEW
    assert ideal_plan.review is not None
    assert budget_plan.lifecycle_status == NutritionPlanLifecycleStatus.ARCHIVED
    assert budget_plan.review is None
    assert (
        db.scalar(
            select(EntitlementUsageEvent).where(
                EntitlementUsageEvent.user_id == user.id,
                EntitlementUsageEvent.entitlement_key == "nutrition.physician_review",
            )
        )
        is not None
    )

    repeated = select_bundle_plan(
        db,
        user_id=user.id,
        bundle_id=bundle.id,
        plan_id=ideal_plan.id,
        physician_review_allowed=True,
    )
    assert repeated.selected_plan_id == ideal_plan.id

    with pytest.raises(EntitlementQuotaExceededError):
        select_bundle_plan(
            db,
            user_id=user.id,
            bundle_id=bundle.id,
            plan_id=budget_plan.id,
            physician_review_allowed=True,
        )
    db.refresh(bundle)
    db.refresh(budget_plan)
    assert bundle.selected_plan_id == ideal_plan.id
    assert budget_plan.lifecycle_status == NutritionPlanLifecycleStatus.ARCHIVED
    assert budget_plan.review is None
    assert (
        len(
            db.scalars(
                select(EntitlementUsageEvent).where(
                    EntitlementUsageEvent.user_id == user.id,
                    EntitlementUsageEvent.entitlement_key == "nutrition.physician_review",
                )
            ).all()
        )
        == 1
    )


def test_get_latest_plan_bundle_endpoint(client: TestClient, db: Session) -> None:
    user, bundle, budget_plan, ideal_plan = _seed_test_bundle(client, db)
    origin = {"Origin": "http://localhost:5173"}

    resp = client.get("/api/v1/nutrition/plan-bundles/latest", headers=origin)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data is not None
    assert data["bundle_id"] == str(bundle.id)
    assert data["budget_plan"] is not None
    assert data["budget_plan"]["id"] == str(budget_plan.id)
    assert data["budget_plan"]["plan_role"] == NutritionPlanRole.BUDGET.value
    assert data["ideal_plan"] is not None
    assert data["ideal_plan"]["id"] == str(ideal_plan.id)
    assert data["ideal_plan"]["plan_role"] == NutritionPlanRole.IDEAL_REFERENCE.value


def test_hard_blocked_member_cannot_read_latest_plan_bundle(
    client: TestClient, db: Session
) -> None:
    _user, _bundle, _budget_plan, _ideal_plan = _seed_test_bundle(client, db)
    origin = {"Origin": "http://localhost:5173"}

    blocked = client.put(
        "/api/v1/nutrition/safety",
        headers=origin,
        json={
            "conditions": [],
            "medications": [],
            "dangerous_food_reaction_history": False,
            "pregnant": False,
            "breastfeeding": False,
            "eating_disorder_diagnosed": False,
            "eating_disorder_active_symptoms": False,
            "emergency_or_danger_symptoms": True,
            "complex_medication_food_interaction": False,
            "physician_dietary_restrictions": None,
            "other_relevant_condition": None,
        },
    )
    assert blocked.status_code == 200, blocked.text

    response = client.get("/api/v1/nutrition/plan-bundles/latest", headers=origin)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NUTRITION_PLAN_SAFETY_BLOCKED"


def test_select_bundle_plan_by_frontend_payload_format(client: TestClient, db: Session) -> None:
    user, bundle, budget_plan, ideal_plan = _seed_test_bundle(client, db)
    origin = {"Origin": "http://localhost:5173"}

    # Frontend payload with selected_plan_role="ideal"
    resp = client.post(
        f"/api/v1/nutrition/plan-bundles/{bundle.id}/select",
        json={"selected_plan_role": "ideal"},
        headers=origin,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["selected_plan_id"] == str(ideal_plan.id)

    # Frontend payload with selected_plan_role="budget" and selected_plan_id
    resp = client.post(
        f"/api/v1/nutrition/plan-bundles/{bundle.id}/select",
        json={"selected_plan_id": str(budget_plan.id), "selected_plan_role": "budget"},
        headers=origin,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["selected_plan_id"] == str(budget_plan.id)
