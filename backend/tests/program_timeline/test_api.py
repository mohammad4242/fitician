from uuid import uuid4

from fastapi.testclient import TestClient

from tests.nutrition.test_weekly_plan_api import ORIGIN


def _register(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": f"timeline-api-{uuid4()}@example.com", "password": "long password"},
    )
    assert response.status_code == 201


def test_program_timeline_today_returns_local_date_and_states(client: TestClient) -> None:
    _register(client)

    response = client.get(
        "/api/v1/program-timeline/today",
        params={"timezone": "Asia/Tehran"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["timezone"] == "Asia/Tehran"
    assert body["local_date"]
    assert body["workout"]["state"] == "no_plan"
    assert body["nutrition"]["state"] == "no_plan"


def test_program_timeline_rejects_invalid_query_timezone(client: TestClient) -> None:
    _register(client)

    response = client.get(
        "/api/v1/program-timeline/today",
        params={"timezone": "Not/AZone"},
    )

    assert response.status_code == 422
