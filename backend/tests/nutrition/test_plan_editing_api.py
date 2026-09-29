from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.body_analysis.enums import SpecialistRole
from app.body_analysis.models import UserSpecialistRole
from app.entitlements.enums import AccessPackageCode, EntitlementCode, GrantSource
from app.entitlements.models import EntitlementUsageEvent, UserAccessGrant
from app.entitlements.service import grant_package
from app.notifications.models import NotificationOutboxEvent
from app.nutrition.candidate_selection import quality_for_result
from app.nutrition.enums import NutritionPlanLifecycleStatus, NutritionPlanReviewStatus
from app.nutrition.models import (
    NutritionCatalogueFood,
    NutritionMealFeedback,
    NutritionPlanBundle,
    NutritionPlanPhysicianReview,
    NutritionWeeklyPlan,
)
from app.nutrition.planner_engine import (
    GenerationOutcome,
    PlannedDay,
    PlannedMeal,
    PlannerResult,
)
from app.nutrition.preference_snapshot import load_preference_snapshot
from tests.nutrition.test_clinical_review_api import _login_physician
from tests.nutrition.test_weekly_plan_api import (
    ORIGIN,
    _register_and_estimate,
    _seed_foods_and_prices,
)


def _generated_plan(
    client: TestClient,
    db: Session,
    *,
    package: AccessPackageCode = AccessPackageCode.NUTRITION_PHYSICIAN,
) -> dict[str, object]:
    _register_and_estimate(
        client,
        db,
        "task7-member@example.com",
        meals=2,
        snacks=1,
        package=package,
    )
    _seed_foods_and_prices(db)
    response = client.post("/api/v1/nutrition/plans", headers=ORIGIN)
    assert response.status_code == 201
    return response.json()["plan"]


def _safe_replacement_id(plan, meal_id):
    target = next(meal for day in plan["days"] for meal in day["meals"] if meal["id"] == meal_id)
    return next(
        meal["id"]
        for day in plan["days"]
        for meal in day["meals"]
        if meal["id"] != meal_id
        and meal["catalogue_meal_id"] == target["catalogue_meal_id"]
        and meal["nutrient_totals"] == target["nutrient_totals"]
    )


def _equivalent_food_variant(client, db, plan):
    """Provide a distinct, composition-equivalent food for revision/entitlement tests."""
    stored = db.get(NutritionWeeklyPlan, UUID(plan["id"]))
    target_id = UUID(plan["days"][0]["meals"][0]["foods"][0]["food_id"])
    target_meal_id = UUID(plan["days"][0]["meals"][0]["id"])
    target = next(
        food
        for day in stored.days
        for meal in day.meals
        for food in meal.foods
        if meal.id == target_meal_id and food.food_id == target_id
    )
    catalogue = db.get(NutritionCatalogueFood, target_id)
    variant = NutritionCatalogueFood(
        slug="equivalent-revision-food",
        name_fa=target.food_name_fa,
        name_en="Equivalent food",
        verification_status=catalogue.verification_status,
        source_name=catalogue.source_name,
        source_reference=catalogue.source_reference,
        source_food_id="equivalent-test",
    )
    db.add(variant)
    db.flush()
    source = next(
        food
        for day in stored.days
        for meal in day.meals
        for food in meal.foods
        if meal.id != target_meal_id
        and food.food_id == target_id
        and food.grams == target.grams
        and food.nutrient_snapshot == target.nutrient_snapshot
    )
    source.food_id = variant.id
    source.food_slug = variant.slug
    db.commit()
    return client.get(f"/api/v1/nutrition/plans/{plan['id']}").json()


def _expire_physician_review_quota(db: Session, user_id: UUID) -> None:
    usage = db.scalars(
        select(EntitlementUsageEvent).where(
            EntitlementUsageEvent.user_id == user_id,
            EntitlementUsageEvent.entitlement_key == EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
        )
    ).all()
    assert usage
    for event in usage:
        event.occurred_at = datetime.now(UTC) - timedelta(days=29)
    db.commit()


def test_removing_a_main_meal_cannot_persist_an_inadequate_revision(client, db) -> None:
    plan = _generated_plan(client, db)
    meal = next(row for row in plan["days"][0]["meals"] if row["slot_role"] == "main_meal")
    before = db.scalar(select(func.count()).select_from(NutritionWeeklyPlan))
    response = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/remove-meal/confirm",
        headers=ORIGIN,
        json={"expected_plan_revision_id": plan["id"], "meal_id": meal["id"]},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PLAN_EDIT_NUTRITION_CONSTRAINT_VIOLATION"
    assert db.scalar(select(func.count()).select_from(NutritionWeeklyPlan)) == before


def test_oil_is_not_offered_as_a_chicken_replacement(client, db) -> None:
    plan = _generated_plan(client, db)
    meal, target = next(
        (meal, food)
        for day in plan["days"]
        for meal in day["meals"]
        for food in meal["foods"]
        if "chicken" in food["slug"]
    )
    response = client.get(
        f"/api/v1/nutrition/plans/{plan['id']}/food-replacement-options",
        params={"meal_id": meal["id"], "food_id": target["food_id"]},
    )
    assert response.status_code == 200
    assert all("oil" not in food["slug"] for food in response.json()["options"])


def test_shopping_list_uses_exact_quantities_and_snapshot_costs(
    client: TestClient, db: Session
) -> None:
    plan = _generated_plan(client, db)

    response = client.get(f"/api/v1/nutrition/plans/{plan['id']}/shopping-list")

    assert response.status_code == 200
    body = response.json()
    assert body["plan_revision"] == plan["revision"]
    assert body["warning_codes"] == ["PLAN_NOT_ACTIVE"]
    assert body["total_cost_irr"] == plan["weekly_cost_irr"]
    assert all(item["required_quantity"] > 0 for item in body["items"])
    assert all(item["canonical_unit"] == "g" for item in body["items"])
    assert all("package_count" not in item for item in body["items"])


def test_metadata_changes_do_not_invalidate_review(client: TestClient, db: Session) -> None:
    plan = _generated_plan(client, db)
    meal_id = plan["days"][0]["meals"][0]["id"]

    lock = client.put(
        f"/api/v1/nutrition/plans/{plan['id']}/meals/{meal_id}/lock",
        headers=ORIGIN,
        json={"is_locked": True},
    )
    feedback = client.put(
        f"/api/v1/nutrition/plans/{plan['id']}/meals/{meal_id}/feedback",
        headers=ORIGIN,
        json={"feedback_type": "liked"},
    )

    assert lock.status_code == 200
    assert lock.json()["change_kind"] == "plan_control_metadata"
    assert feedback.status_code == 200
    persisted = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"]))
    assert persisted is not None
    assert persisted.review is not None
    assert persisted.review.status == NutritionPlanReviewStatus.PENDING


def test_plan_metadata_mutations_require_management_entitlement(
    client: TestClient, db: Session
) -> None:
    plan = _generated_plan(client, db)
    persisted = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"]))
    assert persisted is not None
    for grant in db.scalars(
        select(UserAccessGrant).where(UserAccessGrant.user_id == persisted.user_id)
    ).all():
        grant.revoked_at = datetime.now(UTC)
    db.commit()
    meal_id = plan["days"][0]["meals"][0]["id"]

    lock = client.put(
        f"/api/v1/nutrition/plans/{plan['id']}/meals/{meal_id}/lock",
        headers=ORIGIN,
        json={"is_locked": True},
    )
    feedback = client.put(
        f"/api/v1/nutrition/plans/{plan['id']}/meals/{meal_id}/feedback",
        headers=ORIGIN,
        json={"feedback_type": "liked"},
    )

    assert lock.status_code == 403
    assert lock.json()["detail"]["code"] == "ENTITLEMENT_REQUIRED"
    assert feedback.status_code == 403
    assert feedback.json()["detail"]["code"] == "ENTITLEMENT_REQUIRED"


def test_feedback_read_is_persisted_and_changes_future_candidate_scoring(
    client: TestClient, db: Session
) -> None:
    plan = _generated_plan(client, db)
    meal = plan["days"][0]["meals"][0]

    saved = client.put(
        f"/api/v1/nutrition/plans/{plan['id']}/meals/{meal['id']}/feedback",
        headers=ORIGIN,
        json={"feedback_type": "liked"},
    )
    assert saved.status_code == 200
    assert saved.json()["feedback_type"] == "liked"

    persisted_plan = db.scalar(
        select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"])
    )
    assert persisted_plan is not None
    row = db.scalar(
        select(NutritionMealFeedback).where(NutritionMealFeedback.meal_id == meal["id"])
    )
    assert row is not None
    snapshot = load_preference_snapshot(db, persisted_plan.user_id, ())
    assert snapshot.liked_meal_ids == (meal["catalogue_meal_id"],)

    result = PlannerResult(
        outcome=GenerationOutcome.SUCCESS,
        reason_codes=("SAFE_FEASIBLE_DRAFT_GENERATED",),
        days=(
            PlannedDay(
                day_index=0,
                meals=(
                    PlannedMeal(
                        role="main",
                        slot_index=0,
                        template_id=meal["catalogue_meal_id"],
                        template_category="main",
                        foods=(),
                        cost_irr=1,
                        nutrients=(),
                    ),
                ),
                cost_irr=1,
                nutrients=(),
            ),
        ),
        weekly_cost_irr=1,
    )
    neutral = quality_for_result(result, weekly_budget_irr=1)
    liked = quality_for_result(result, weekly_budget_irr=1, preference_snapshot=snapshot)
    assert liked.preference_and_feedback_penalty < neutral.preference_and_feedback_penalty

    read = client.get(f"/api/v1/nutrition/plans/{plan['id']}/feedback")
    assert read.status_code == 200
    assert read.json()["feedback"][meal["id"]] == "liked"

    switched = client.put(
        f"/api/v1/nutrition/plans/{plan['id']}/meals/{meal['id']}/feedback",
        headers=ORIGIN,
        json={"feedback_type": "disliked"},
    )
    assert switched.status_code == 200
    assert switched.json()["feedback_type"] == "disliked"
    updated_row = db.scalar(
        select(NutritionMealFeedback).where(NutritionMealFeedback.meal_id == meal["id"])
    )
    assert updated_row is not None and updated_row.feedback_type.value == "disliked"


def test_replacement_options_are_explicit_and_exclude_locked_meals(
    client: TestClient, db: Session
) -> None:
    plan = _generated_plan(client, db)
    target = plan["days"][0]["meals"][0]
    response = client.get(
        f"/api/v1/nutrition/plans/{plan['id']}/meal-replacement-options",
        params={"meal_id": target["id"]},
    )
    assert response.status_code == 200
    options = response.json()["options"]
    assert options
    assert all(option["id"] != target["id"] for option in options)
    assert all(option["slot_role"] == target["slot_role"] for option in options)
    assert all(not option["is_locked"] for option in options)

    food = target["foods"][0]
    food_options = client.get(
        f"/api/v1/nutrition/plans/{plan['id']}/food-replacement-options",
        params={"meal_id": target["id"], "food_id": food["food_id"]},
    )
    assert food_options.status_code == 200
    assert all(option["food_id"] != food["food_id"] for option in food_options.json()["options"])


def test_plan_defining_edits_reject_locked_meals_and_in_review_plans(
    client: TestClient, db: Session
) -> None:
    plan = _generated_plan(client, db)
    meal = plan["days"][0]["meals"][0]
    locked = client.put(
        f"/api/v1/nutrition/plans/{plan['id']}/meals/{meal['id']}/lock",
        headers=ORIGIN,
        json={"is_locked": True},
    )
    assert locked.status_code == 200
    locked_preview = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/remove-meal/preview",
        params={"meal_id": meal["id"]},
    )
    assert locked_preview.status_code == 409
    assert locked_preview.json()["detail"]["code"] == "MEAL_LOCKED"

    persisted = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"]))
    assert persisted is not None and persisted.review is not None
    persisted.review.status = NutritionPlanReviewStatus.IN_REVIEW
    db.commit()
    blocked = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/remove-meal/confirm",
        headers=ORIGIN,
        json={"expected_plan_revision_id": plan["id"], "meal_id": meal["id"]},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "PLAN_REVIEW_IN_PROGRESS"


def test_plan_defining_edit_creates_immutable_revision_and_rejects_stale_confirmation(
    client: TestClient, db: Session
) -> None:
    plan = _generated_plan(client, db)
    source_plan = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"]))
    assert source_plan is not None
    bundle = NutritionPlanBundle(
        user_id=source_plan.user_id,
        selected_plan_id=source_plan.id,
        selected_plan_role="budget",
        selected_at=datetime.now(UTC),
    )
    db.add(bundle)
    db.commit()
    selected_at = bundle.selected_at
    _expire_physician_review_quota(db, source_plan.user_id)
    meal_id = plan["days"][0]["meals"][0]["id"]
    preview = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-meal/preview",
        json={
            "expected_plan_revision_id": plan["id"],
            "meal_id": meal_id,
            "replacement_meal_id": _safe_replacement_id(plan, meal_id),
        },
    )
    assert preview.status_code == 200
    assert preview.json()["change_kind"] == "plan_defining"
    assert preview.json()["requires_physician_review"] is True

    confirmed = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-meal/confirm",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "meal_id": meal_id,
            "replacement_meal_id": _safe_replacement_id(plan, meal_id),
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    revised = confirmed.json()
    assert revised["id"] != plan["id"]
    assert revised["revision"] == plan["revision"] + 1
    revised_plan = db.get(NutritionWeeklyPlan, UUID(revised["id"]))
    assert revised_plan is not None and revised_plan.generation is not None
    assert revised_plan.generation.bundle_id is None
    assert revised["review_status"] == "pending"
    assert revised["weekly_cost_irr"] == plan["weekly_cost_irr"]
    assert (
        revised["nutrients"]["goal_calories"]["planned"]
        == plan["nutrients"]["goal_calories"]["planned"]
    )

    old_review = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == plan["id"]
        )
    )
    assert old_review is not None
    assert old_review.status == NutritionPlanReviewStatus.INVALIDATED_BY_REVISION
    db.refresh(bundle)
    assert bundle.selected_plan_id == UUID(revised["id"])
    assert bundle.selected_plan_role == "budget"
    assert bundle.selected_at == selected_at
    latest = client.get("/api/v1/nutrition/plans/latest", headers=ORIGIN)
    assert latest.status_code == 200
    assert latest.json()["id"] == revised["id"]

    stale = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-meal/confirm",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": revised["id"],
            "meal_id": meal_id,
            "replacement_meal_id": _safe_replacement_id(plan, meal_id),
        },
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "STALE_PLAN_REVISION"


def test_review_required_edit_without_entitlement_is_atomic(
    client: TestClient, db: Session
) -> None:
    plan = _equivalent_food_variant(client, db, _generated_plan(client, db))
    source = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"]))
    assert source is not None
    assert source.review is not None
    assert source.review.status is NutritionPlanReviewStatus.PENDING
    assert source.lifecycle_status is NutritionPlanLifecycleStatus.PENDING_PHYSICIAN_REVIEW
    user_id = source.user_id
    grant_package(db, user_id, AccessPackageCode.NUTRITION, source=GrantSource.MANUAL)
    for grant in db.scalars(
        select(UserAccessGrant).where(
            UserAccessGrant.user_id == user_id,
            UserAccessGrant.package_code == AccessPackageCode.NUTRITION_PHYSICIAN,
            UserAccessGrant.revoked_at.is_(None),
        )
    ).all():
        grant.revoked_at = datetime.now(UTC)
    bundle = NutritionPlanBundle(
        user_id=user_id,
        selected_plan_id=source.id,
        selected_plan_role="budget",
        selected_at=datetime.now(UTC),
    )
    db.add(bundle)
    db.commit()

    meal = plan["days"][0]["meals"][0]
    same_role_replacement = next(
        candidate
        for day in plan["days"]
        for candidate in day["meals"]
        if candidate["id"] == _safe_replacement_id(plan, meal["id"])
    )
    target_food = meal["foods"][0]
    replacement_food = next(
        food
        for day in plan["days"]
        for candidate_meal in day["meals"]
        for food in candidate_meal["foods"]
        if food["slug"] == "equivalent-revision-food"
    )
    previews = (
        client.post(
            f"/api/v1/nutrition/plans/{plan['id']}/edits/remove-meal/preview",
            params={"meal_id": meal["id"], "replacement_meal_id": same_role_replacement["id"]},
        ),
        client.post(
            f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-meal/preview",
            json={
                "expected_plan_revision_id": plan["id"],
                "meal_id": meal["id"],
                "replacement_meal_id": same_role_replacement["id"],
            },
        ),
        client.post(
            f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-food/preview",
            json={
                "expected_plan_revision_id": plan["id"],
                "meal_id": meal["id"],
                "food_id": target_food["food_id"],
                "replacement_food_id": replacement_food["food_id"],
            },
        ),
    )
    assert previews[0].status_code == 409
    assert previews[0].json()["detail"]["code"] == "PLAN_EDIT_NUTRITION_CONSTRAINT_VIOLATION"
    assert all(response.status_code == 200 for response in previews[1:]), [
        response.json() for response in previews
    ]
    assert all(response.json()["requires_physician_review"] is True for response in previews[1:])

    plan_ids_before = set(
        db.scalars(select(NutritionWeeklyPlan.id).where(NutritionWeeklyPlan.user_id == user_id))
    )
    usage_ids_before = set(
        db.scalars(
            select(EntitlementUsageEvent.id).where(
                EntitlementUsageEvent.user_id == user_id,
                EntitlementUsageEvent.entitlement_key == EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
            )
        )
    )
    notification_count_before = db.scalar(
        select(func.count())
        .select_from(NotificationOutboxEvent)
        .where(NotificationOutboxEvent.event_type == "nutrition_review_required")
    )
    original_review_status = source.review.status
    original_lifecycle = source.lifecycle_status
    original_bundle_pointer = bundle.selected_plan_id
    original_bundle_role = bundle.selected_plan_role

    denied = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-meal/confirm",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "meal_id": meal["id"],
            "replacement_meal_id": same_role_replacement["id"],
        },
    )

    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "ENTITLEMENT_REQUIRED"
    db.expire_all()
    source = db.get(NutritionWeeklyPlan, UUID(plan["id"]))
    bundle = db.get(NutritionPlanBundle, bundle.id)
    assert source is not None and source.review is not None
    assert source.review.status is original_review_status
    assert source.lifecycle_status is original_lifecycle
    assert bundle is not None
    assert bundle.selected_plan_id == original_bundle_pointer
    assert bundle.selected_plan_role == original_bundle_role
    assert (
        set(
            db.scalars(select(NutritionWeeklyPlan.id).where(NutritionWeeklyPlan.user_id == user_id))
        )
        == plan_ids_before
    )
    assert (
        set(
            db.scalars(
                select(EntitlementUsageEvent.id).where(
                    EntitlementUsageEvent.user_id == user_id,
                    EntitlementUsageEvent.entitlement_key
                    == EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
                )
            )
        )
        == usage_ids_before
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(NotificationOutboxEvent)
            .where(NotificationOutboxEvent.event_type == "nutrition_review_required")
        )
        == notification_count_before
    )


def test_member_revision_consumes_physician_quota_and_partial_regeneration_is_blocked(
    client: TestClient,
    db: Session,
) -> None:
    plan = _generated_plan(client, db, package=AccessPackageCode.NUTRITION)
    source_plan = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"]))
    assert source_plan is not None and source_plan.review is None
    user_id = source_plan.user_id
    grant_package(
        db,
        user_id,
        AccessPackageCode.NUTRITION_PHYSICIAN,
        source=GrantSource.MANUAL,
    )
    physician = User(email="revision-quota-physician@example.com", password_hash="unused")
    db.add(physician)
    db.flush()
    db.add(UserSpecialistRole(user_id=physician.id, role=SpecialistRole.PHYSICIAN))
    db.commit()

    initial_plan_ids = set(
        db.scalars(
            select(NutritionWeeklyPlan.id).where(NutritionWeeklyPlan.user_id == user_id)
        ).all()
    )
    initial_reviews = db.scalars(
        select(NutritionPlanPhysicianReview)
        .join(NutritionWeeklyPlan, NutritionWeeklyPlan.id == NutritionPlanPhysicianReview.plan_id)
        .where(NutritionWeeklyPlan.user_id == user_id)
    ).all()
    assert initial_reviews == []
    assert (
        db.scalars(
            select(EntitlementUsageEvent).where(
                EntitlementUsageEvent.user_id == user_id,
                EntitlementUsageEvent.entitlement_key == EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
            )
        ).all()
        == []
    )

    meal_id = plan["days"][0]["meals"][0]["id"]
    first_revision = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-meal/confirm",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "meal_id": meal_id,
            "replacement_meal_id": _safe_replacement_id(plan, meal_id),
        },
    )
    assert first_revision.status_code == 200, first_revision.text
    revised = first_revision.json()
    revised_id = UUID(revised["id"])

    review = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == revised_id
        )
    )
    assert review is not None and review.status is NutritionPlanReviewStatus.PENDING
    usage = db.scalars(
        select(EntitlementUsageEvent).where(
            EntitlementUsageEvent.user_id == user_id,
            EntitlementUsageEvent.entitlement_key == EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
        )
    ).all()
    assert len(usage) == 1
    assert usage[0].resource_key == f"nutrition-plan:{revised_id}:revision:{revised['revision']}"
    assert (
        db.scalar(
            select(NotificationOutboxEvent).where(
                NotificationOutboxEvent.user_id == physician.id,
                NotificationOutboxEvent.event_type == "nutrition_review_required",
                NotificationOutboxEvent.deduplication_key
                == f"nutrition-review:{review.id}:required",
            )
        )
        is not None
    )
    first_revision_plan_ids = set(
        db.scalars(
            select(NutritionWeeklyPlan.id).where(NutritionWeeklyPlan.user_id == user_id)
        ).all()
    )
    assert first_revision_plan_ids == initial_plan_ids | {revised_id}

    exhausted = client.post(
        f"/api/v1/nutrition/plans/{revised_id}/edits/partial-regenerate",
        headers=ORIGIN,
        json={"expected_plan_revision_id": str(revised_id), "day_indexes": [0]},
    )

    assert exhausted.status_code == 429
    assert exhausted.json()["detail"]["code"] == "ENTITLEMENT_QUOTA_EXCEEDED"
    db.refresh(review)
    assert review.status is NutritionPlanReviewStatus.PENDING
    assert (
        set(
            db.scalars(
                select(NutritionWeeklyPlan.id).where(NutritionWeeklyPlan.user_id == user_id)
            ).all()
        )
        == first_revision_plan_ids
    )
    assert (
        len(
            db.scalars(
                select(NutritionPlanPhysicianReview)
                .join(
                    NutritionWeeklyPlan,
                    NutritionWeeklyPlan.id == NutritionPlanPhysicianReview.plan_id,
                )
                .where(NutritionWeeklyPlan.user_id == user_id)
            ).all()
        )
        == 1
    )
    assert (
        len(
            db.scalars(
                select(EntitlementUsageEvent).where(
                    EntitlementUsageEvent.user_id == user_id,
                    EntitlementUsageEvent.entitlement_key
                    == EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
                )
            ).all()
        )
        == 1
    )
    assert (
        len(
            db.scalars(
                select(NotificationOutboxEvent).where(
                    NotificationOutboxEvent.user_id == physician.id,
                    NotificationOutboxEvent.event_type == "nutrition_review_required",
                )
            ).all()
        )
        == 1
    )


def test_meal_replacement_preview_and_confirmation_create_revision(
    client: TestClient, db: Session
) -> None:
    plan = _generated_plan(client, db)
    source_plan = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"]))
    assert source_plan is not None
    _expire_physician_review_quota(db, source_plan.user_id)
    target = plan["days"][0]["meals"][0]
    replacement = next(
        meal
        for meal in plan["days"][1]["meals"]
        if meal["slot_role"] == target["slot_role"] and meal["id"] != target["id"]
    )
    payload = {
        "expected_plan_revision_id": plan["id"],
        "meal_id": target["id"],
        "replacement_meal_id": replacement["id"],
    }
    preview = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-meal/preview", json=payload
    )
    assert preview.status_code == 200
    assert preview.json()["change_kind"] == "plan_defining"
    confirmed = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-meal/confirm",
        headers=ORIGIN,
        json=payload,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["revision"] == plan["revision"] + 1
    assert confirmed.json()["physician_change_summary"][0]["operation"] == "replace_meal"


def test_food_replacement_and_partial_regeneration_preserve_immutable_history(
    client: TestClient, db: Session
) -> None:
    plan = _equivalent_food_variant(
        client, db, _generated_plan(client, db, package=AccessPackageCode.NUTRITION)
    )
    source = db.get(NutritionWeeklyPlan, UUID(plan["id"]))
    assert source is not None and source.review is None
    target_meal = plan["days"][0]["meals"][0]
    target_food = target_meal["foods"][0]
    replacement_food = next(
        food
        for day in plan["days"]
        for meal in day["meals"]
        for food in meal["foods"]
        if food["slug"] == "equivalent-revision-food"
    )
    payload = {
        "expected_plan_revision_id": plan["id"],
        "meal_id": target_meal["id"],
        "food_id": target_food["food_id"],
        "replacement_food_id": replacement_food["food_id"],
    }
    assert (
        client.post(
            f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-food/preview", json=payload
        ).status_code
        == 200
    )
    replaced = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/edits/replace-food/confirm",
        headers=ORIGIN,
        json=payload,
    )
    assert replaced.status_code == 200, replaced.text
    revision = replaced.json()
    assert revision["lifecycle_status"] == "ready_to_start"
    assert revision["review_status"] == "missing"
    regenerated = client.post(
        f"/api/v1/nutrition/plans/{revision['id']}/edits/partial-regenerate",
        headers=ORIGIN,
        json={"expected_plan_revision_id": revision["id"], "day_indexes": [0]},
    )
    assert regenerated.status_code == 200, regenerated.text
    assert regenerated.json()["revision"] == plan["revision"] + 2
    history = client.get("/api/v1/nutrition/plans/history").json()
    assert {item["id"] for item in history}.issuperset(
        {plan["id"], revision["id"], regenerated.json()["id"]}
    )


def test_physician_quantity_edit_rebinds_review_to_new_revision(
    client: TestClient,
    db: Session,
) -> None:
    plan = _generated_plan(client, db)
    physician = _login_physician(client, db, "quantity-physician@example.com")
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    assert (
        client.post(
            f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
            headers=ORIGIN,
        ).status_code
        == 200
    )
    persisted_plan = db.scalar(
        select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"])
    )
    assert persisted_plan is not None and persisted_plan.review is not None
    assigned_at = persisted_plan.review.assigned_at
    review_started_at = persisted_plan.review.review_started_at
    usage_before = db.scalars(
        select(EntitlementUsageEvent).where(
            EntitlementUsageEvent.user_id == persisted_plan.user_id,
            EntitlementUsageEvent.entitlement_key == EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
        )
    ).all()
    meal = plan["days"][0]["meals"][0]
    food = next(food for food in meal["foods"] if "rice" in food["slug"])
    stored_food = next(
        food_row
        for day in persisted_plan.days
        for meal_row in day.meals
        for food_row in meal_row.foods
        if str(food_row.food_id) == food["food_id"]
    )
    maximum = Decimal(str(stored_food.quantity_snapshot["max_grams"]))
    new_grams = stored_food.grams + 1 if stored_food.grams + 1 <= maximum else stored_food.grams - 1

    response = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/edits/food-quantity",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "meal_id": meal["id"],
            "food_id": food["food_id"],
            "grams": float(new_grams),
        },
    )

    assert response.status_code == 200, response.text
    revised = response.json()
    assert revised["id"] != plan["id"]
    assert revised["review_status"] == "in_review"
    assert revised["lifecycle_status"] == "pending_physician_review"
    new_review = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == revised["id"]
        )
    )
    assert new_review is not None and new_review.physician_user_id == physician.id
    assert new_review.assigned_at is not None
    assert new_review.review_started_at is not None
    assert assigned_at is not None and review_started_at is not None
    usage_after = db.scalars(
        select(EntitlementUsageEvent).where(
            EntitlementUsageEvent.user_id == persisted_plan.user_id,
            EntitlementUsageEvent.entitlement_key == EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
        )
    ).all()
    assert len(usage_after) == len(usage_before) == 1
