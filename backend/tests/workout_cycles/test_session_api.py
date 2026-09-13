from datetime import date
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.workout_cycles.enums import WorkoutCycleSessionStatus
from app.workout_cycles.models import WorkoutCycleSession
from app.workouts.enums import WorkoutPlanStatus
from app.workouts.models import WorkoutDay, WorkoutPlan

ORIGIN = {"Origin": "http://localhost:5173"}
PROFILE = {
    "display_name": "Session API User",
    "birth_date": "2000-05-14",
    "sex": "male",
    "height_cm": 178,
    "current_weight_kg": 76.5,
    "fitness_goal": "build_muscle",
    "experience_level": "beginner",
    "training_days_per_week": 2,
    "preferred_weekdays": [0, 2],
    "training_location": "gym",
    "session_duration_minutes": 45,
}


def register_and_profile(client: TestClient, email: str) -> UUID:
    registration = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": "long password"},
    )
    assert registration.status_code == 201
    profile = client.post("/api/v1/profile", headers=ORIGIN, json=PROFILE)
    assert profile.status_code == 201
    return UUID(registration.json()["id"])


def make_plan(db: Session, user_id: UUID) -> WorkoutPlan:
    plan = WorkoutPlan(
        user_id=user_id,
        status=WorkoutPlanStatus.ACTIVE,
        generation_signature="a" * 64,
        profile_snapshot={"plan_duration_weeks": 4},
        provider="fake",
        model_id="fake",
        prompt_version="v1",
        generation_policy_version="v1",
        candidate_set_hash="b" * 64,
        generation_method="coach_review",
    )
    plan.days = [
        WorkoutDay(
            day_number=1,
            title_en="Saturday",
            title_fa="شنبه",
            estimated_duration_minutes=45,
            weekday=0,
        ),
        WorkoutDay(
            day_number=2,
            title_en="Monday",
            title_fa="دوشنبه",
            estimated_duration_minutes=50,
            weekday=2,
        ),
    ]
    db.add(plan)
    db.flush()
    return plan


def test_start_route_returns_exact_sessions_and_metadata(client: TestClient, db: Session) -> None:
    user_id = register_and_profile(client, f"session-api-start-{uuid4()}@example.com")
    plan = make_plan(db, user_id)

    response = client.post(
        "/api/v1/workout-cycles/start",
        headers=ORIGIN,
        json={
            "workout_plan_id": str(plan.id),
            "start_date": "2026-09-13",
            "timezone": "UTC",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["has_exact_session_tracking"] is True
    assert payload["total_sessions"] == 8
    assert payload["completed_sessions"] == 0
    assert payload["sessions"][0]["scheduled_date"] == "2026-09-14"
    assert payload["sessions"][0]["status"] == WorkoutCycleSessionStatus.SCHEDULED.value


def test_session_mutation_routes_require_origin_and_owner(client: TestClient, db: Session) -> None:
    owner_id = register_and_profile(client, f"session-api-owner-{uuid4()}@example.com")
    plan = make_plan(db, owner_id)
    started = client.post(
        "/api/v1/workout-cycles/start",
        headers=ORIGIN,
        json={
            "workout_plan_id": str(plan.id),
            "start_date": "2026-09-12",
            "timezone": "UTC",
        },
    )
    assert started.status_code == 201
    session_id = started.json()["sessions"][0]["id"]

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    register_and_profile(client, f"session-api-other-{uuid4()}@example.com")

    assert (
        client.post(
            f"/api/v1/workout-cycles/current/sessions/{session_id}/complete",
            headers=ORIGIN,
        )
    ).status_code == 404
    assert (
        client.post(f"/api/v1/workout-cycles/current/sessions/{session_id}/skip").status_code == 403
    )


def test_session_routes_map_finished_and_second_start_conflicts(
    client: TestClient, db: Session
) -> None:
    user_id = register_and_profile(client, f"session-api-conflict-{uuid4()}@example.com")
    plan = make_plan(db, user_id)
    start_payload = {
        "workout_plan_id": str(plan.id),
        "start_date": "2026-09-12",
        "timezone": "UTC",
    }
    started = client.post("/api/v1/workout-cycles/start", headers=ORIGIN, json=start_payload)
    assert started.status_code == 201
    session_id = started.json()["sessions"][0]["id"]

    completed = client.post(
        f"/api/v1/workout-cycles/current/sessions/{session_id}/complete",
        headers=ORIGIN,
    )
    assert completed.status_code == 200
    assert (
        client.post(
            f"/api/v1/workout-cycles/current/sessions/{session_id}/complete",
            headers=ORIGIN,
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/workout-cycles/start",
            headers=ORIGIN,
            json={**start_payload, "start_date": "2026-09-13"},
        ).status_code
        == 409
    )


def test_reschedule_route_validates_date_and_collisions(client: TestClient, db: Session) -> None:
    user_id = register_and_profile(client, f"session-api-reschedule-{uuid4()}@example.com")
    plan = make_plan(db, user_id)
    started = client.post(
        "/api/v1/workout-cycles/start",
        headers=ORIGIN,
        json={
            "workout_plan_id": str(plan.id),
            "start_date": "2026-09-12",
            "timezone": "UTC",
        },
    )
    assert started.status_code == 201
    second_session_id = started.json()["sessions"][1]["id"]

    collision = client.post(
        f"/api/v1/workout-cycles/current/sessions/{second_session_id}/reschedule",
        headers=ORIGIN,
        json={"scheduled_date": "2026-09-12"},
    )
    assert collision.status_code == 409
    invalid_timezone = client.post(
        "/api/v1/workout-cycles/start",
        headers=ORIGIN,
        json={
            "workout_plan_id": str(plan.id),
            "start_date": "2026-09-12",
            "timezone": "Not/AZone",
        },
    )
    assert invalid_timezone.status_code == 422


def test_session_response_is_persisted_and_owned_by_cycle(db: Session, client: TestClient) -> None:
    user_id = register_and_profile(client, f"session-api-persisted-{uuid4()}@example.com")
    plan = make_plan(db, user_id)
    response = client.post(
        "/api/v1/workout-cycles/start",
        headers=ORIGIN,
        json={
            "workout_plan_id": str(plan.id),
            "start_date": date(2026, 9, 12).isoformat(),
            "timezone": "UTC",
        },
    )
    assert response.status_code == 201
    session_id = UUID(response.json()["sessions"][0]["id"])
    persisted = db.get(WorkoutCycleSession, session_id)
    assert persisted is not None
    assert persisted.cycle_id == UUID(response.json()["cycle_id"])
