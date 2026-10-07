from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.access_management.insights_service import overview, period_boundaries
from app.auth.models import AuthSession, User
from app.profile.models import BodyMeasurement
from tests.access_management.test_admin_user_access import ORIGIN, make_admin, register


def test_tehran_period_boundaries() -> None:
    today, week, month = period_boundaries(datetime(2026, 10, 7, 21, 0, tzinfo=UTC))
    assert today == datetime(2026, 10, 7, 20, 30, tzinfo=UTC)
    assert week == datetime(2026, 10, 2, 20, 30, tzinfo=UTC)
    assert month == datetime(2026, 9, 30, 20, 30, tzinfo=UTC)


def test_overview_signup_counts_and_daily_zero_fill(db: Session) -> None:
    now = datetime(2026, 10, 7, 10, tzinfo=UTC)
    for days in (0, 0, 3, 10, 40):
        db.add(
            User(
                email=f"{uuid4()}@example.com",
                password_hash="unused",
                created_at=now - timedelta(days=days),
            )
        )
    db.flush()
    result = overview(db, now=now)
    assert result.total_users == 5
    assert result.registrations_today == 2
    assert result.registrations_week == 3
    assert result.registrations_month == 3
    assert len(result.daily_signups) == 30
    assert sum(point.count for point in result.daily_signups) == 4
    assert result.daily_signups[-1].count == 2


def test_users_pagination_filters_and_counts(client: TestClient, db: Session) -> None:
    admin = make_admin(client, db)
    now = datetime.now(UTC)
    for days in (0, 2, 40):
        db.add(
            User(
                email=f"member{days}@example.com",
                password_hash="unused",
                created_at=now - timedelta(days=days),
            )
        )
    db.flush()
    response = client.get("/api/v1/admin/access/users", params={"q": "member", "limit": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 1 and body["offset"] == 0
    assert len(body["items"]) == 1
    next_page = client.get(
        "/api/v1/admin/access/users", params={"q": "member", "limit": 1, "offset": 1}
    )
    assert next_page.json()["items"][0]["user_id"] != body["items"][0]["user_id"]
    today = client.get(
        "/api/v1/admin/access/users", params={"q": "member", "signup_period": "today"}
    )
    assert today.json()["total"] == 1
    assert admin.id
    assert client.get("/api/v1/admin/access/users", params={"limit": 101}).status_code == 422
    assert (
        client.get("/api/v1/admin/access/users", params={"signup_period": "custom"}).status_code
        == 422
    )


def test_insights_progress_and_legacy_login_evidence(client: TestClient, db: Session) -> None:
    member = register(client, "360-member@example.com")
    user_id = member["id"]
    db.add(
        AuthSession(
            user_id=user_id,
            token_hash="a" * 64,
            created_at=datetime.now(UTC) - timedelta(days=70),
            expires_at=datetime.now(UTC),
        )
    )
    db.add(BodyMeasurement(user_id=user_id, weight_kg=81.4, waist_circumference_cm=90))
    db.flush()
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)
    root = f"/api/v1/admin/access/users/{user_id}"
    result = client.get(f"{root}/insights")
    assert result.status_code == 200
    assert result.json()["login_count"] == 0  # registration is never a login
    assert result.json()["latest_weight_kg"] == 81.4
    logins = client.get(f"{root}/logins").json()
    assert any(row["evidence"] == "legacy_web_session" for row in logins["items"])
    assert all(row["evidence"] != "explicit_login" for row in logins["items"])
    assert "token_hash" not in str(logins)
    progress = client.get(f"{root}/progress").json()
    assert progress["items"][0]["weight_kg"] == 81.4
    activity = client.get(f"{root}/activity", params={"limit": 1}).json()
    assert activity["total"] >= 2 and len(activity["items"]) == 1
    assert "password_hash" not in result.text
    for section in ("workout-plans", "nutrition-plans"):
        assert client.get(f"{root}/{section}").json()["items"] == []
        assert client.get(f"{root}/{section}/{uuid4()}").status_code == 404


@pytest.mark.parametrize(
    "section",
    ["", "/insights", "/activity", "/logins", "/workout-plans", "/nutrition-plans", "/progress"],
)
def test_user_360_requires_admin(client: TestClient, section: str) -> None:
    member = register(client, "360-no-admin@example.com")
    assert client.get(f"/api/v1/admin/access/users/{member['id']}{section}").status_code == 403
    assert client.get("/api/v1/admin/access/overview").status_code == 403


def test_workout_history_safe_details_and_ownership(client: TestClient, db: Session) -> None:
    from uuid import UUID

    from app.workout_cycles.models import WorkoutCycle, WorkoutCycleSession
    from app.workouts.models import WorkoutDay
    from tests.workout_cycles.test_api import _plan

    member = register(client, "workout-360@example.com")
    plan = _plan(db, UUID(member["id"]), duration_weeks=6)
    plan.profile_snapshot["medical_history"] = "PRIVATE MEDICAL TEXT"
    plan.body_analysis_provenance = {"private_media": "PRIVATE PHOTO"}
    plan.warnings = ["PRIVATE MEDICAL TEXT"]
    day = WorkoutDay(
        workout_plan_id=plan.id,
        day_number=1,
        title_en="Day 1",
        title_fa="روز ۱",
        estimated_duration_minutes=45,
    )
    db.add(day)
    db.flush()
    cycle = WorkoutCycle(user_id=plan.user_id, workout_plan_id=plan.id, duration_weeks=6)
    db.add(cycle)
    db.flush()
    now = datetime.now(UTC)
    db.add(
        WorkoutCycleSession(
            cycle_id=cycle.id,
            workout_day_id=day.id,
            week_number=2,
            session_number=1,
            scheduled_date=now.date(),
            status="completed",
            completed_at=now,
        )
    )
    db.flush()
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    admin = make_admin(client, db)
    root = f"/api/v1/admin/access/users/{plan.user_id}"
    history = client.get(f"{root}/workout-plans").json()
    assert history["total"] == 1
    assert history["items"][0]["training_days"] == 1
    assert history["items"][0]["duration_weeks"] == 6
    detail = client.get(f"{root}/workout-plans/{plan.id}")
    assert detail.status_code == 200
    assert detail.json()["days"][0]["title_en"] == "Day 1"
    assert "PRIVATE" not in detail.text
    assert "profile_snapshot" not in detail.text
    assert (
        client.get(f"/api/v1/admin/access/users/{admin.id}/workout-plans/{plan.id}").status_code
        == 404
    )
    assert client.get(f"{root}/insights").json()["completed_workout_sessions"] == 1
    activity = client.get(
        f"{root}/activity", params={"event_type": "workout.session_completed"}
    ).json()
    assert activity["total"] == 1
    assert activity["items"][0]["metadata"]["week_number"] == 2


def test_nutrition_history_reuses_serializer_and_excludes_private_fields(
    client: TestClient, db: Session
) -> None:
    from sqlalchemy import select

    from app.nutrition.models import NutritionWeeklyPlan
    from tests.nutrition.test_weekly_plan_api import _register_and_estimate, _seed_foods_and_prices

    _register_and_estimate(client, db, "nutrition-360@example.com")
    _seed_foods_and_prices(db)
    generated = client.post("/api/v1/nutrition/plans", headers=ORIGIN)
    assert generated.status_code == 201
    plan = db.scalar(
        select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == generated.json()["plan"]["id"])
    )
    assert plan is not None
    plan.input_snapshot = {**plan.input_snapshot, "medications": ["PRIVATE MEDICAL TEXT"]}
    if plan.review:
        plan.review.user_visible_notes = "PRIVATE CLINICAL NOTE"
    db.flush()
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    admin = make_admin(client, db)
    root = f"/api/v1/admin/access/users/{plan.user_id}"
    history = client.get(f"{root}/nutrition-plans").json()
    assert history["total"] >= 1
    assert history["items"][0]["revision"] >= 1
    assert "input_snapshot" not in str(history)
    detail = client.get(f"{root}/nutrition-plans/{plan.id}")
    assert detail.status_code == 200
    assert len(detail.json()["days"]) == 7
    for private in (
        "PRIVATE",
        "input_snapshot",
        "physician_user_visible_notes",
        "medical",
        "image_url",
    ):
        assert private not in detail.text
    assert (
        client.get(f"/api/v1/admin/access/users/{admin.id}/nutrition-plans/{plan.id}").status_code
        == 404
    )
    plan.is_user_visible = False
    db.flush()
    assert client.get(f"{root}/nutrition-plans/{plan.id}").status_code == 404


def test_overview_activity_paid_access_purchases_and_safe_analysis(db: Session) -> None:
    from app.billing.models import BillingOrder
    from app.body_analysis.models import BodyAnalysis
    from app.body_photos.models import BodyPhotoSession
    from app.entitlements.enums import AccessPackageCode, GrantSource
    from app.entitlements.service import grant_package
    from app.user_activity.service import record_activity

    now = datetime(2026, 10, 7, 12, tzinfo=UTC)
    users = [
        User(
            email=f"metric{number}@example.com",
            password_hash="unused",
            created_at=now - timedelta(days=60),
        )
        for number in range(4)
    ]
    db.add_all(users)
    db.flush()
    for user, days in zip(users, (0, 3, 20, 40), strict=True):
        record_activity(
            db,
            user.id,
            "auth.login_succeeded",
            metadata={"platform": "web", "auth_method": "password"},
            occurred_at=now - timedelta(days=days),
        )
    grant_package(
        db,
        users[0].id,
        AccessPackageCode.TRAINING,
        source=GrantSource.SUBSCRIPTION,
        starts_at=now - timedelta(days=3),
        ends_at=now + timedelta(days=35),
        term_weeks=4,
        idempotency_key="metric-paid",
    )
    grant_package(
        db,
        users[1].id,
        AccessPackageCode.COMPLETE,
        source=GrantSource.PROMOTION,
        starts_at=now - timedelta(days=3),
        ends_at=now + timedelta(days=35),
        term_weeks=4,
        idempotency_key="metric-promoted",
    )
    for days in (0, 2, 40):
        db.add(
            BillingOrder(
                user_id=users[0].id,
                offer_code="training_4w",
                package_code_snapshot="training",
                duration_weeks_snapshot=4,
                amount_irr_snapshot=100,
                currency_snapshot="IRR",
                provider="fake",
                status="paid",
                idempotency_key=str(uuid4()),
                paid_at=now - timedelta(days=days),
            )
        )
    photo_session = BodyPhotoSession(user_id=users[0].id, purpose="initial_plan", state="completed")
    db.add(photo_session)
    db.flush()
    db.add(
        BodyAnalysis(
            session_id=photo_session.id,
            revision=1,
            provider="fake",
            model_id="fake",
            prompt_version="v1",
            schema_version="v1",
            status="completed",
            completed_at=now,
            raw_result={"private": "PRIVATE PHOTO"},
        )
    )
    db.flush()
    result = overview(db, now=now)
    assert (result.active_users_24h, result.active_users_7d, result.active_users_30d) == (1, 2, 3)
    assert result.active_paid_users == 1
    assert (result.purchases_today, result.purchases_week, result.purchases_month) == (1, 2, 2)
    assert result.body_analyses_completed == 1


def test_custom_dates_sort_activity_dedup_and_login_exactness(
    client: TestClient, db: Session
) -> None:
    from sqlalchemy import select

    from app.user_activity.models import UserActivityEvent
    from app.user_activity.service import record_activity

    member = register(client, "custom-360@example.com")
    user = db.get(User, member["id"])
    assert user is not None
    user.created_at = datetime(2025, 1, 1, 20, 30, tzinfo=UTC)
    db.flush()
    login = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": user.email, "password": "long password"},
    )
    assert login.status_code == 200
    event = db.scalar(
        select(UserActivityEvent).where(
            UserActivityEvent.user_id == user.id,
            UserActivityEvent.event_type == "auth.login_succeeded",
        )
    )
    assert event is not None
    assert event.safe_metadata["auth_method"] == "password"
    measurement = BodyMeasurement(user_id=user.id, weight_kg=82)
    db.add(measurement)
    db.flush()
    record_activity(
        db,
        user.id,
        "body.measurement_recorded",
        resource_type="body_measurement",
        resource_id=str(measurement.id),
        metadata={"weight_kg": 82},
        deduplication_key="dedup-360",
    )
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)
    root = f"/api/v1/admin/access/users/{user.id}"
    assert client.get(f"{root}/insights").json()["login_count"] == 1
    assert client.get(f"{root}/logins").json()["total"] == 1
    activity = client.get(
        f"{root}/activity", params={"event_type": "body.measurement_recorded"}
    ).json()
    assert activity["total"] == 1 and activity["items"][0]["source"] == "explicit"
    custom = client.get(
        "/api/v1/admin/access/users",
        params={
            "q": "custom-360",
            "signup_period": "custom",
            "from_date": "2025-01-02",
            "to_date": "2025-01-02",
            "sort": "last_activity",
        },
    )
    assert custom.status_code == 200
    assert custom.json()["total"] == 1
    assert (
        client.get(
            "/api/v1/admin/access/users", params={"q": "custom-360", "sort": "oldest"}
        ).json()["total"]
        == 1
    )


def test_progress_only_displays_actually_observed_values(client: TestClient, db: Session) -> None:
    member = register(client, "measurements-360@example.com")
    user_id = member["id"]
    now = datetime.now(UTC)
    db.add(
        BodyMeasurement(
            user_id=user_id,
            weight_kg=81,
            measured_at=now - timedelta(days=2),
            observed_fields=["weight_kg"],
        )
    )
    db.add(
        BodyMeasurement(
            user_id=user_id,
            weight_kg=90,
            waist_circumference_cm=88,
            measured_at=now,
            observed_fields=["waist_circumference_cm"],
        )
    )
    db.flush()
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)
    root = f"/api/v1/admin/access/users/{user_id}"
    assert client.get(f"{root}/insights").json()["latest_weight_kg"] == 81
    page = client.get(f"{root}/progress").json()
    assert page["items"][0]["weight_kg"] is None
    assert page["items"][0]["waist_circumference_cm"] == 88
    assert page["items"][1]["weight_kg"] == 81


def test_native_legacy_evidence_is_not_an_explicit_login(client: TestClient, db: Session) -> None:
    from app.auth.models import MobileAuthEvent, MobileTokenFamily

    member = register(client, "native-legacy-360@example.com")
    family = MobileTokenFamily(
        user_id=member["id"],
        device_id="legacy-device",
        platform="android",
        app_version="1.2.3",
        device_name="Pixel",
    )
    db.add(family)
    db.flush()
    db.add(
        MobileAuthEvent(
            user_id=member["id"],
            family_id=family.id,
            event_type="token_issued",
            event_data={"private_token": "PRIVATE"},
        )
    )
    db.flush()
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)
    root = f"/api/v1/admin/access/users/{member['id']}"
    result = client.get(f"{root}/logins")
    assert result.status_code == 200
    assert result.json()["total"] == 1
    assert result.json()["items"][0]["evidence"] == "legacy_mobile_token_issued"
    assert result.json()["items"][0]["platform"] == "android"
    assert result.json()["items"][0]["auth_method"] is None
    assert "PRIVATE" not in result.text and "device_id" not in result.text
    assert client.get(f"{root}/insights").json()["login_count"] == 0


def test_batch_user_summary_query_count_is_independent_of_page_size(db: Session) -> None:
    from sqlalchemy import event

    from app.access_management.insights_service import users_page

    now = datetime.now(UTC)
    db.add_all(
        [
            User(email=f"batch{number}@example.com", password_hash="unused", created_at=now)
            for number in range(12)
        ]
    )
    db.flush()
    connection = db.connection()
    queries = []

    def count_query(_conn, _cursor, statement, _parameters, _context, _executemany):
        queries.append(statement)

    event.listen(connection, "before_cursor_execute", count_query)
    try:
        for size in (1, 12):
            queries.clear()
            page = users_page(
                db,
                q="batch",
                limit=size,
                offset=0,
                signup_period="all",
                from_date=None,
                to_date=None,
                sort="newest",
                now=now,
            )
            assert len(page.items) == size
            assert len(queries) == 6
    finally:
        event.remove(connection, "before_cursor_execute", count_query)


def test_analysis_operational_completion_counts_pending_review(db: Session) -> None:
    from app.access_management.insights_service import analyses_page, insights
    from app.body_analysis.models import BodyAnalysis
    from app.body_photos.models import BodyPhotoSession

    user = User(email="analysis-review-360@example.com", password_hash="unused")
    db.add(user)
    db.flush()
    photo_session = BodyPhotoSession(
        user_id=user.id, purpose="initial_plan", state="review_pending"
    )
    db.add(photo_session)
    db.flush()
    db.add(
        BodyAnalysis(
            session_id=photo_session.id,
            revision=1,
            provider="fake",
            model_id="fake",
            prompt_version="v1",
            schema_version="v1",
            status="review_pending",
            completed_at=datetime.now(UTC),
            raw_result={"private": "PRIVATE"},
        )
    )
    db.flush()
    assert insights(db, user.id).body_analyses_completed == 1
    assert overview(db).body_analyses_completed == 1
    rows = analyses_page(db, user.id, limit=1, offset=0)
    assert rows.items[0].status == "review_pending"
    assert "PRIVATE" not in rows.model_dump_json()


@pytest.mark.parametrize(
    "section", ["body-analyses", f"workout-plans/{uuid4()}", f"nutrition-plans/{uuid4()}"]
)
def test_admin_only_plan_details_and_analysis_metadata(client: TestClient, section: str) -> None:
    member = register(client, "details-member-360@example.com")
    assert client.get(f"/api/v1/admin/access/users/{member['id']}/{section}").status_code == 403


def test_signup_filters_exclude_future_and_respect_boundaries(db: Session) -> None:
    from app.access_management.insights_service import users_page

    now = datetime(2026, 10, 7, 12, tzinfo=UTC)
    today, week, month = period_boundaries(now)
    for number, created in enumerate(
        [
            today,
            today - timedelta(microseconds=1),
            week,
            month,
            month - timedelta(microseconds=1),
            now + timedelta(days=1),
        ]
    ):
        db.add(
            User(email=f"boundary{number}@example.com", password_hash="unused", created_at=created)
        )
    db.flush()
    for period, expected in [("today", 1), ("week", 3), ("month", 4), ("all", 6)]:
        page = users_page(
            db,
            q="boundary",
            limit=25,
            offset=0,
            signup_period=period,
            from_date=None,
            to_date=None,
            sort="newest",
            now=now,
        )
        assert page.total == expected


def test_workout_history_includes_approved_plan_review(db: Session) -> None:
    from app.access_management.plan_insights import workout_plans
    from app.workout_reviews.enums import WorkoutReviewStatus
    from app.workout_reviews.models import WorkoutPlanReview
    from tests.workout_cycles.test_api import _plan

    user = User(email="approved-plan-360@example.com", password_hash="unused")
    db.add(user)
    db.flush()
    original = _plan(db, user.id)
    from app.workouts.models import WorkoutPlanStatus

    original.status = WorkoutPlanStatus.SUPERSEDED
    db.flush()
    approved = _plan(db, user.id)
    db.add(
        WorkoutPlanReview(
            user_id=user.id,
            source_plan_id=original.id,
            approved_plan_id=approved.id,
            status=WorkoutReviewStatus.APPROVED,
        )
    )
    db.flush()
    result = workout_plans(db, user.id, limit=25, offset=0)
    assert result.total == 2
    item = next(item for item in result.items if item.id == approved.id)
    assert item.review_status == "approved"
