from datetime import date, timedelta
from decimal import Decimal

from app.entitlements.enums import AccessPackageCode
from app.nutrition.enums import NutritionPlanLifecycleStatus
from app.nutrition.models import NutritionWeeklyPlan
from tests.nutrition.test_weekly_plan_api import (
    ORIGIN,
    _register_and_estimate,
    _seed_foods_and_prices,
)


def _plan(client, db):
    _register_and_estimate(
        client,
        db,
        "progress-review@example.com",
        goal="lose_weight",
        package=AccessPackageCode.NUTRITION,
    )
    from decimal import Decimal

    from sqlalchemy import select

    from app.nutrition.models import NutritionProfile
    from app.profile.models import UserProfile

    nutrition_profile = db.scalar(select(NutritionProfile))
    # History dates and noon weigh-ins use UTC; keep the user's review clock aligned.
    db.get(UserProfile, nutrition_profile.user_id).timezone = "UTC"
    nutrition_profile.target_weight_change_kg_per_week = Decimal(".3")
    db.commit()
    _seed_foods_and_prices(db)
    response = client.post("/api/v1/nutrition/plans", headers=ORIGIN)
    assert response.status_code == 201, response.text
    assert response.json()["plan"] is not None, response.text
    plan = db.get(NutritionWeeklyPlan, response.json()["plan"]["id"])
    if plan.review is not None:
        db.delete(plan.review)
        plan.review = None
    plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    plan.start_date = date.today() - timedelta(days=28)
    db.commit()
    return plan


def test_review_does_not_treat_missing_records_as_zero_intake(client, db):
    _plan(client, db)
    response = client.get("/api/v1/nutrition/progress-review")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "insufficient_data"
    assert response.json()["observed_kg_per_week"] is None
    assert response.json()["average_logged_kcal"] is None
    assert response.json()["can_confirm"] is False


def test_rapid_weight_loss_triggers_review_even_with_uncertain_intake(client, db):
    plan = _plan(client, db)
    _history(db, plan, confidence="medium", rate=-2)
    response = client.get("/api/v1/nutrition/progress-review")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "specialist_review"
    assert "RAPID_WEIGHT_LOSS_REQUIRES_REVIEW" in body["reason_codes"]
    assert body["can_confirm"] is False


def _history(db, plan, *, status="on_plan", confidence="high", rate=0):
    from datetime import UTC, datetime, time
    from decimal import Decimal

    from app.nutrition.models import NutritionConsumptionEntry, NutritionDailyCheckIn
    from app.profile.models import BodyMeasurement

    for day in range(28):
        recorded = plan.start_date + timedelta(days=day)
        planned_day = next(item for item in plan.days if item.day_index == day % 7)
        db.add(
            NutritionDailyCheckIn(
                user_id=plan.user_id, entry_date=recorded, status=status, plan_revision_id=plan.id
            )
        )
        db.add(
            NutritionConsumptionEntry(
                user_id=plan.user_id,
                entry_date=recorded,
                plan_revision_id=plan.id,
                display_name="Recorded day",
                source="planned_confirmed",
                confidence=confidence,
                user_confirmed=True,
                nutrients=planned_day.nutrient_totals,
                warning_codes=[],
            )
        )
    for day in [0, 7, 20, 27]:
        db.add(
            BodyMeasurement(
                user_id=plan.user_id,
                measured_at=datetime.combine(
                    plan.start_date + timedelta(days=day), time(12), tzinfo=UTC
                ),
                weight_kg=Decimal("62.5") + Decimal(str(rate)) * day / 7,
            )
        )
    db.commit()


def test_plateau_review_is_read_only_and_confirmation_is_explicit_and_idempotent(client, db):
    from sqlalchemy import select

    from app.nutrition.models import NutritionProfile, NutritionTargetUpdateConsent

    plan = _plan(client, db)
    _history(db, plan)
    before = db.get(NutritionProfile, plan.user_id).target_weight_change_kg_per_week
    review = client.get("/api/v1/nutrition/progress-review").json()
    assert review["status"] == "adjustment_available", str(review)
    assert review["current_calories"] > review["proposed_calories"]
    assert db.get(NutritionProfile, plan.user_id).target_weight_change_kg_per_week == before
    payload = {
        "expected_plan_id": str(plan.id),
        "signature": review["signature"],
        "confirmed": False,
    }
    assert (
        client.post(
            "/api/v1/nutrition/progress-review/confirm", headers=ORIGIN, json=payload
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/nutrition/progress-review/confirm", json={**payload, "confirmed": True}
        ).status_code
        == 403
    )
    accepted = client.post(
        "/api/v1/nutrition/progress-review/confirm",
        headers=ORIGIN,
        json={**payload, "confirmed": True},
    )
    assert accepted.status_code == 200, accepted.text
    repeated = client.post(
        "/api/v1/nutrition/progress-review/confirm",
        headers=ORIGIN,
        json={**payload, "confirmed": True},
    )
    assert repeated.json()["estimate_id"] == accepted.json()["estimate_id"]
    assert len(db.scalars(select(NutritionTargetUpdateConsent)).all()) == 1
    assert db.get(NutritionProfile, plan.user_id).target_weight_change_kg_per_week == Decimal(
        str(review["proposed_rate_kg_per_week"])
    )
    assert plan.lifecycle_status == NutritionPlanLifecycleStatus.ACTIVE
    assert client.get("/api/v1/nutrition/progress-review").json()["status"] == "cooldown"
    target = client.get("/api/v1/nutrition/estimates/current").json()
    assert target["id"] == accepted.json()["estimate_id"]
    assert target["is_stale"] is False
    from datetime import UTC, datetime

    from app.entitlements.enums import EntitlementCode
    from app.entitlements.models import EntitlementUsageEvent
    from app.nutrition.progress_review import review_progress

    later = review_progress(db, plan.user_id, now=datetime.now(UTC) + timedelta(days=8))
    assert later.status == "new_plan_required"
    blocked = client.post("/api/v1/nutrition/plans", headers=ORIGIN)
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "ENTITLEMENT_QUOTA_EXCEEDED"
    usage = db.scalar(
        select(EntitlementUsageEvent).where(
            EntitlementUsageEvent.user_id == plan.user_id,
            EntitlementUsageEvent.entitlement_key == EntitlementCode.NUTRITION_PLAN_GENERATE.value,
        )
    )
    assert usage is not None
    usage.occurred_at = datetime.now(UTC) - timedelta(days=8)
    db.commit()
    generated = client.post("/api/v1/nutrition/plans", headers=ORIGIN)
    assert generated.status_code == 201, generated.text
    new_plan = generated.json()["plan"]
    assert new_plan is not None, generated.text
    assert new_plan["id"] != str(plan.id)
    assert (
        str(db.get(NutritionWeeklyPlan, new_plan["id"]).estimate_id)
        == accepted.json()["estimate_id"]
    )
    assert plan.lifecycle_status == NutritionPlanLifecycleStatus.ACTIVE


def test_stale_proposal_is_rejected_without_changing_targets(client, db):
    from sqlalchemy import select

    from app.nutrition.models import NutritionDailyCheckIn, NutritionProfile

    plan = _plan(client, db)
    _history(db, plan)
    review = client.get("/api/v1/nutrition/progress-review").json()
    assert review["can_confirm"]
    row = db.scalar(
        select(NutritionDailyCheckIn).where(NutritionDailyCheckIn.user_id == plan.user_id)
    )
    row.status = "off_plan"
    db.commit()
    result = client.post(
        "/api/v1/nutrition/progress-review/confirm",
        headers=ORIGIN,
        json={
            "expected_plan_id": str(plan.id),
            "signature": review["signature"],
            "confirmed": True,
        },
    )
    assert result.status_code == 409
    assert db.get(NutritionProfile, plan.user_id).target_weight_change_kg_per_week == Decimal(".3")


def test_reported_nonadherence_and_approximate_intake_do_not_trigger_adjustment(client, db):
    from sqlalchemy import select

    from app.nutrition.models import NutritionConsumptionEntry

    plan = _plan(client, db)
    _history(db, plan, status="off_plan")
    assert client.get("/api/v1/nutrition/progress-review").json()["status"] == "improve_adherence"
    for row in db.scalars(
        select(NutritionConsumptionEntry).where(NutritionConsumptionEntry.user_id == plan.user_id)
    ):
        row.confidence = "medium"
    db.commit()
    assert client.get("/api/v1/nutrition/progress-review").json()["status"] == "insufficient_data"


def test_aligned_progress_and_medical_plan_never_offer_automatic_change(client, db):
    from app.nutrition.models import NutritionPlanPhysicianReview

    plan = _plan(client, db)
    _history(db, plan, rate=-0.3)
    assert client.get("/api/v1/nutrition/progress-review").json()["status"] == "continue"
    db.add(
        NutritionPlanPhysicianReview(
            plan_id=plan.id, status="approved", expected_plan_revision=plan.revision
        )
    )
    db.commit()
    review = client.get("/api/v1/nutrition/progress-review").json()
    assert review["status"] == "specialist_review"
    assert review["can_confirm"] is False


def test_safety_limits_are_not_relaxed_to_force_a_proposal(client, db):
    from app.nutrition.estimate_service import create_estimate
    from app.nutrition.models import NutritionProfile

    plan = _plan(client, db)
    profile = db.get(NutritionProfile, plan.user_id)
    profile.target_weight_change_kg_per_week = Decimal("2")
    db.flush()
    estimate = create_estimate(db, plan.user_id)
    plan.estimate_id = estimate.id
    db.commit()
    _history(db, plan)
    review = client.get("/api/v1/nutrition/progress-review").json()
    assert review["status"] == "specialist_review", review
    assert review["can_confirm"] is False


def test_confirm_failure_rolls_back_rate_and_consent(client, db, monkeypatch):
    from sqlalchemy import select

    from app.nutrition import progress_review
    from app.nutrition.adherence_service import AdherenceError
    from app.nutrition.models import NutritionProfile, NutritionTargetUpdateConsent

    plan = _plan(client, db)
    _history(db, plan)
    review = client.get("/api/v1/nutrition/progress-review").json()
    assert review["can_confirm"]

    def fail(*args, **kwargs):
        raise AdherenceError("ESTIMATE_FAILED")

    monkeypatch.setattr(progress_review, "create_estimate", fail)
    result = client.post(
        "/api/v1/nutrition/progress-review/confirm",
        headers=ORIGIN,
        json={
            "expected_plan_id": str(plan.id),
            "signature": review["signature"],
            "confirmed": True,
        },
    )
    assert result.status_code == 409
    assert db.get(NutritionProfile, plan.user_id).target_weight_change_kg_per_week == Decimal(".3")
    assert db.scalar(select(NutritionTargetUpdateConsent)) is None


def test_local_day_excludes_today_and_other_users_records(client, db, test_settings):
    from datetime import UTC, datetime

    from app.nutrition.progress_review import review_progress
    from app.profile.models import UserProfile
    from tests.workout_reviews.test_review_access import _login, _user

    plan = _plan(client, db)
    _history(db, plan)
    profile = db.get(UserProfile, plan.user_id)
    profile.timezone = "Asia/Tehran"
    db.flush()
    utc_late = datetime.combine(date.today(), datetime.min.time(), tzinfo=UTC) + timedelta(hours=22)
    review = review_progress(db, plan.user_id, now=utc_late)
    assert review.end == date.today()
    stranger = _user(db)
    _login(client, db, test_settings, stranger)
    private = client.get("/api/v1/nutrition/progress-review").json()
    assert private["plan_id"] is None
    assert private["weighing_days"] == 0
    assert private["average_logged_kcal"] is None


def test_fast_weight_loss_never_proposes_a_larger_calorie_deficit(client, db):
    plan = _plan(client, db)
    _history(db, plan, rate=-0.7)
    review = client.get("/api/v1/nutrition/progress-review").json()
    assert not review["can_confirm"] or review["proposed_calories"] > review["current_calories"], (
        review
    )
