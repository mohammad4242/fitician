from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.nutrition.enums import NutritionPlanLifecycleStatus, NutritionPlanReviewStatus
from app.nutrition.models import NutritionWeeklyPlan
from app.nutrition.plan_service import (
    ActiveWeeklyPlanNotFoundError,
    active_weekly_plan,
    select_bundle_plan,
)
from app.profile.models import UserProfile
from app.program_timeline.service import build_program_timeline
from tests.nutrition.test_bundle_selection import _seed_test_bundle
from tests.nutrition.test_clinical_review_api import _member_plan
from tests.nutrition.test_weekly_plan_api import ORIGIN


def test_generated_selected_plan_is_ready_until_member_starts(
    client: TestClient, db: Session
) -> None:
    user, bundle, _, ideal_plan = _seed_test_bundle(client, db)
    selected = select_bundle_plan(
        db,
        user_id=user.id,
        bundle_id=bundle.id,
        plan_id=ideal_plan.id,
    )

    assert selected.plan.lifecycle_status == NutritionPlanLifecycleStatus.READY_TO_START.value
    timeline = build_program_timeline(db, user_id=user.id)
    assert timeline.nutrition.state.value == "ready_to_start"
    assert timeline.nutrition.plan_id == ideal_plan.id


def _ready_plan(client: TestClient, db: Session) -> dict[str, object]:
    plan = _member_plan(client, db)
    persisted = db.get(NutritionWeeklyPlan, plan["id"])
    assert persisted is not None
    if persisted.review is not None:
        db.delete(persisted.review)
        persisted.review = None
    persisted.lifecycle_status = NutritionPlanLifecycleStatus.READY_TO_START
    db.commit()
    return plan


def test_ready_plan_start_sets_anchor_timestamp_and_realigns_template_dates(
    client: TestClient, db: Session
) -> None:
    plan = _ready_plan(client, db)
    start_date = date.today() + timedelta(days=3)

    response = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/start",
        headers=ORIGIN,
        json={"start_date": start_date.isoformat(), "timezone": "Asia/Tehran"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lifecycle_status"] == NutritionPlanLifecycleStatus.ACTIVE.value
    assert body["start_date"] == start_date.isoformat()
    assert body["started_at"] is not None
    assert [day["plan_date"] for day in body["days"]] == [
        (start_date + timedelta(days=index)).isoformat() for index in range(7)
    ]

    persisted = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"]))
    assert persisted is not None
    assert persisted.lifecycle_status is NutritionPlanLifecycleStatus.ACTIVE
    assert persisted.start_date == start_date
    assert persisted.started_at is not None
    profile = db.get(UserProfile, persisted.user_id)
    assert profile is not None
    assert profile.timezone == "Asia/Tehran"


def test_unapproved_required_review_plan_cannot_start(client: TestClient, db: Session) -> None:
    plan = _member_plan(client, db)
    persisted = db.get(NutritionWeeklyPlan, plan["id"])
    assert persisted is not None
    assert persisted.review is not None
    persisted.lifecycle_status = NutritionPlanLifecycleStatus.PENDING_PHYSICIAN_REVIEW
    persisted.review.status = NutritionPlanReviewStatus.PENDING
    db.commit()

    response = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/start",
        headers=ORIGIN,
        json={"start_date": date.today().isoformat(), "timezone": "UTC"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NUTRITION_PLAN_NOT_READY"


def test_reference_comparison_plan_cannot_start(client: TestClient, db: Session) -> None:
    user, bundle, _, ideal_plan = _seed_test_bundle(client, db)

    response = client.post(
        f"/api/v1/nutrition/plans/{ideal_plan.id}/start",
        headers=ORIGIN,
        json={"start_date": date.today().isoformat(), "timezone": "UTC"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NUTRITION_REFERENCE_PLAN_NOT_STARTABLE"


def test_unselected_active_ideal_reference_is_not_effective(
    client: TestClient, db: Session
) -> None:
    user, _bundle, budget_plan, ideal_plan = _seed_test_bundle(client, db)
    budget_plan.lifecycle_status = NutritionPlanLifecycleStatus.ARCHIVED
    ideal_plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    ideal_plan.start_date = date(2026, 9, 1)
    db.commit()

    with pytest.raises(ActiveWeeklyPlanNotFoundError):
        active_weekly_plan(
            db,
            user.id,
            now=datetime(2026, 9, 14, 12, tzinfo=UTC),
        )


def test_selected_ideal_plan_can_start(client: TestClient, db: Session) -> None:
    user, bundle, _, ideal_plan = _seed_test_bundle(client, db)
    select_bundle_plan(db, user_id=user.id, bundle_id=bundle.id, plan_id=ideal_plan.id)
    start = date(2026, 9, 14)

    response = client.post(
        f"/api/v1/nutrition/plans/{ideal_plan.id}/start",
        headers=ORIGIN,
        json={"start_date": start.isoformat(), "timezone": "UTC"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["lifecycle_status"] == NutritionPlanLifecycleStatus.ACTIVE.value
    timeline = build_program_timeline(
        db, user_id=user.id, now=datetime(2026, 9, 14, 12, tzinfo=UTC)
    )
    assert timeline.nutrition.state.value == "active"
    assert timeline.nutrition.plan_id == ideal_plan.id
    assert active_weekly_plan(
        db, user.id, now=datetime(2026, 9, 14, 12, tzinfo=UTC)
    ).id == ideal_plan.id


def test_active_plan_uses_profile_local_date(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _ready_plan(client, db)
    persisted = db.get(NutritionWeeklyPlan, plan["id"])
    assert persisted is not None
    persisted.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    persisted.start_date = date(2026, 9, 14)
    profile = db.get(UserProfile, persisted.user_id)
    assert profile is not None
    profile.timezone = "Asia/Tehran"
    db.commit()

    active = active_weekly_plan(
        db, persisted.user_id, now=datetime(2026, 9, 13, 21, tzinfo=UTC)
    )

    assert active.id == persisted.id
    monkeypatch.setattr(
        "app.time_context.local_date_for_timezone",
        lambda _timezone_name, *, now=None: date(2026, 9, 14),
    )
    response = client.get("/api/v1/nutrition/plans/active")
    assert response.status_code == 200
    assert response.json()["id"] == str(persisted.id)
    timeline = build_program_timeline(
        db, user_id=persisted.user_id, now=datetime(2026, 9, 13, 21, tzinfo=UTC)
    )
    assert timeline.nutrition.plan_id == persisted.id
    tracked = client.put(
        "/api/v1/nutrition/tracking/check-in",
        headers=ORIGIN,
        json={"entry_date": "2026-09-14", "status": "on_plan"},
    )
    assert tracked.status_code == 200
    assert tracked.json()["plan_revision_id"] == str(persisted.id)


def test_future_selected_plan_keeps_current_plan_effective_until_handoff(
    client: TestClient, db: Session
) -> None:
    user, bundle, current_plan, next_plan = _seed_test_bundle(client, db)
    current_plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    current_plan.start_date = date(2026, 9, 1)
    db.commit()

    select_bundle_plan(db, user_id=user.id, bundle_id=bundle.id, plan_id=next_plan.id)
    db.refresh(current_plan)
    assert current_plan.lifecycle_status is NutritionPlanLifecycleStatus.ACTIVE

    start = date(2026, 9, 20)
    response = client.post(
        f"/api/v1/nutrition/plans/{next_plan.id}/start",
        headers=ORIGIN,
        json={"start_date": start.isoformat(), "timezone": "UTC"},
    )
    assert response.status_code == 200, response.text
    timeline = build_program_timeline(
        db, user_id=user.id, now=datetime(2026, 9, 19, 12, tzinfo=UTC)
    )
    assert timeline.nutrition.state.value == "scheduled_start"
    assert timeline.nutrition.plan_id == next_plan.id
    assert active_weekly_plan(
        db, user.id, now=datetime(2026, 9, 19, 12, tzinfo=UTC)
    ).id == current_plan.id
    assert active_weekly_plan(
        db, user.id, now=datetime(2026, 9, 20, 12, tzinfo=UTC)
    ).id == next_plan.id


def test_wrong_owner_cannot_start_another_members_plan(client: TestClient, db: Session) -> None:
    plan = _ready_plan(client, db)
    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={"email": "nutrition-start-other@example.com", "password": "long password"},
        ).status_code
        == 201
    )

    response = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/start",
        headers=ORIGIN,
        json={"start_date": date.today().isoformat(), "timezone": "UTC"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NUTRITION_PLAN_NOT_FOUND"


def test_existing_active_plan_can_be_read_without_restarting(
    client: TestClient, db: Session
) -> None:
    plan = _ready_plan(client, db)
    persisted = db.get(NutritionWeeklyPlan, plan["id"])
    assert persisted is not None
    persisted.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    persisted.started_at = None
    db.commit()

    response = client.post(
        f"/api/v1/nutrition/plans/{plan['id']}/start",
        headers=ORIGIN,
        json={"start_date": persisted.start_date.isoformat(), "timezone": "UTC"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["lifecycle_status"] == NutritionPlanLifecycleStatus.ACTIVE.value
    assert response.json()["started_at"] is None
