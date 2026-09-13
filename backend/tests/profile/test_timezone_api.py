from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.profile.models import UserProfile

ORIGIN = {"Origin": "http://localhost:5173"}
VALID_PROFILE = {
    "display_name": "Mohammad",
    "birth_date": "2000-05-14",
    "sex": "male",
    "height_cm": 178,
    "current_weight_kg": 76.5,
    "fitness_goal": "build_muscle",
    "experience_level": "beginner",
    "training_age_months": 24,
    "training_days_per_week": 3,
    "preferred_weekdays": [0, 2, 4],
    "priority_muscles": ["back"],
    "training_location": "gym",
    "session_duration_minutes": 60,
}


def register(client: TestClient, email: str) -> UUID:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": "long password"},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def create_profile(client: TestClient) -> None:
    response = client.post("/api/v1/profile", headers=ORIGIN, json=VALID_PROFILE)
    assert response.status_code == 201


def test_timezone_update_persists_only_for_the_authenticated_profile(
    client: TestClient, db: Session
) -> None:
    first_user_id = register(client, "timezone-first@example.com")
    create_profile(client)
    second_user_id = register(client, "timezone-second@example.com")
    create_profile(client)

    response = client.put(
        "/api/v1/profile/timezone",
        headers=ORIGIN,
        json={"timezone": "Asia/Tehran"},
    )

    assert response.status_code == 200
    assert response.json() == {"timezone": "Asia/Tehran"}
    first_profile = db.get(UserProfile, first_user_id)
    second_profile = db.get(UserProfile, second_user_id)
    assert first_profile is not None
    assert second_profile is not None
    assert first_profile.timezone == "UTC"
    assert second_profile.timezone == "Asia/Tehran"


def test_timezone_update_rejects_invalid_iana_timezone(client: TestClient) -> None:
    register(client, "timezone-invalid@example.com")
    create_profile(client)

    response = client.put(
        "/api/v1/profile/timezone",
        headers=ORIGIN,
        json={"timezone": "Not/AZone"},
    )

    assert response.status_code == 422


def test_timezone_update_requires_trusted_origin(client: TestClient) -> None:
    register(client, "timezone-origin@example.com")
    create_profile(client)

    response = client.put(
        "/api/v1/profile/timezone",
        json={"timezone": "UTC"},
    )

    assert response.status_code == 403


def test_timezone_update_requires_an_existing_profile(client: TestClient) -> None:
    register(client, "timezone-no-profile@example.com")

    response = client.put(
        "/api/v1/profile/timezone",
        headers=ORIGIN,
        json={"timezone": "UTC"},
    )

    assert response.status_code == 404
