from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.profile.models import BodyMeasurement
from app.progress.service import overview
from tests.workout_cycles.test_session_service import make_profile
from tests.workout_reviews.test_review_access import _login, _user


def test_legacy_changes_and_carry_forward_are_not_fake_observations(db):
    user = _user(db)
    make_profile(db, user.id)
    db.query(BodyMeasurement).filter_by(user_id=user.id).delete()
    for day, weight, waist, hip in [(1, 80, 90, 100), (2, 80, 89, 100), (3, 79, None, 99)]:
        db.add(
            BodyMeasurement(
                user_id=user.id,
                weight_kg=Decimal(weight),
                waist_circumference_cm=waist,
                hip_circumference_cm=hip,
                shoulder_circumference_cm=120,
                measured_at=datetime(2026, 10, day, tzinfo=UTC),
            )
        )
    db.flush()
    body = overview(
        db, user.id, preset="four_weeks", timezone="UTC", now=datetime(2026, 10, 4, tzinfo=UTC)
    ).body_measurements
    assert [p.value for p in body.weight.points] == [80, 79]
    assert body.weight.delta == -1
    assert [p.value for p in body.waist.points] == [90, 89]
    assert body.waist.delta == -1
    assert body.hip.delta == -1
    assert body.shoulder_width.points == []
    assert body.waist.unit == "cm" and body.weight.unit == "kg"


def test_explicit_equal_values_width_and_carry_forwards(client, db, test_settings):
    user = _user(db)
    make_profile(db, user.id)
    _login(client, db, test_settings, user)
    for _ in range(2):
        response = client.post(
            "/api/v1/profile/body-measurements",
            headers={"Origin": "http://localhost:5173"},
            json={
                "request_id": str(uuid4()),
                "shoulder_width_cm": 45,
                "waist_circumference_cm": 90,
            },
        )
        assert response.status_code == 201, response.text
    records = list(
        db.scalars(
            select(BodyMeasurement)
            .where(BodyMeasurement.user_id == user.id)
            .order_by(BodyMeasurement.measured_at)
        )
    )
    assert records[-1].shoulder_width_cm == 45
    assert records[-1].observed_fields == ["shoulder_width_cm", "waist_circumference_cm"]
    assert records[-1].weight_kg == 80
    body = client.get("/api/v1/progress/overview?preset=four_weeks").json()["body_measurements"]
    assert len(body["shoulder_width"]["points"]) == 2
    assert body["shoulder_width"]["delta"] == 0
    assert len(body["weight"]["points"]) == 1
    assert (
        client.post(
            "/api/v1/profile/body-measurements",
            headers={"Origin": "http://localhost:5173"},
            json={"shoulder_width_cm": 120},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/profile/body-measurements",
            headers={"Origin": "http://localhost:5173"},
            json={},
        ).status_code
        == 422
    )


def test_measurement_retry_is_idempotent(client, db, test_settings):
    user = _user(db)
    make_profile(db, user.id)
    _login(client, db, test_settings, user)
    payload = {"request_id": str(uuid4()), "weight_kg": 79}
    headers = {"Origin": "http://localhost:5173"}
    first = client.post("/api/v1/profile/body-measurements", headers=headers, json=payload)
    retry = client.post("/api/v1/profile/body-measurements", headers=headers, json=payload)
    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]
    assert (
        client.post(
            "/api/v1/profile/body-measurements", headers=headers, json={**payload, "weight_kg": 78}
        ).status_code
        == 409
    )
