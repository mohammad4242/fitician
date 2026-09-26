from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.body_analysis.enums import SpecialistRole
from app.body_analysis.models import UserSpecialistRole
from app.workout_reviews.repository import ensure_pending_review
from tests.workout_reviews.test_api import _plan as make_review_plan

ORIGIN = {"Origin": "http://localhost:5173"}


def _register(client: TestClient, email: str) -> UUID:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": "long password"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": email, "password": "long password"},
    )
    assert response.status_code == 200, response.text


def test_assigned_review_detail_stays_private_through_member_changes(
    client: TestClient,
    db: Session,
) -> None:
    member_email = f"assigned-member-{uuid4()}@example.com"
    member_id = _register(client, member_email)
    plan = make_review_plan(db, member_id)
    review = ensure_pending_review(db, plan)
    db.commit()

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    assigned_email = f"assigned-coach-{uuid4()}@example.com"
    assigned_id = _register(client, assigned_email)
    db.add(UserSpecialistRole(user_id=assigned_id, role=SpecialistRole.COACH))
    db.commit()
    claimed = client.post(
        f"/api/v1/coach/workout-reviews/{review.id}/claim",
        headers=ORIGIN,
    )
    assert claimed.status_code == 200, claimed.text
    submitted = client.post(
        f"/api/v1/coach/workout-reviews/{review.id}/submit",
        headers=ORIGIN,
        json={"expected_revision": 1},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "awaiting_member_acceptance"

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    other_email = f"other-coach-{uuid4()}@example.com"
    other_id = _register(client, other_email)
    db.add(UserSpecialistRole(user_id=other_id, role=SpecialistRole.COACH))
    db.commit()
    foreign_awaiting = client.get(f"/api/v1/coach/workout-reviews/{review.id}")
    assert foreign_awaiting.status_code == 409
    assert foreign_awaiting.json()["detail"]["code"] == "REVIEW_ALREADY_CLAIMED"

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    _login(client, assigned_email)
    assigned_awaiting = client.get(f"/api/v1/coach/workout-reviews/{review.id}")
    assert assigned_awaiting.status_code == 200, assigned_awaiting.text
    assert assigned_awaiting.json()["source_plan"]["id"] == str(plan.id)

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    _login(client, member_email)
    rejected = client.post(
        f"/api/v1/workout-reviews/{review.id}/reject",
        headers=ORIGIN,
        json={"expected_revision": 1, "explanation": "Please revise day two"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "member_changes_requested"

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    _login(client, other_email)
    foreign_changes = client.get(f"/api/v1/coach/workout-reviews/{review.id}")
    assert foreign_changes.status_code == 409
    assert foreign_changes.json()["detail"]["code"] == "REVIEW_ALREADY_CLAIMED"

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    _login(client, assigned_email)
    assigned_changes = client.get(f"/api/v1/coach/workout-reviews/{review.id}")
    assert assigned_changes.status_code == 200, assigned_changes.text
    assert assigned_changes.json()["source_plan"]["id"] == str(plan.id)


def test_member_can_read_diff_and_accept_coach_proposal(
    client: TestClient,
    db: Session,
) -> None:
    member_email = f"member-api-{uuid4()}@example.com"
    member_id = _register(client, member_email)
    plan = make_review_plan(db, member_id)
    review = ensure_pending_review(db, plan)
    db.commit()

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    coach_id = _register(client, f"coach-api-{uuid4()}@example.com")
    db.add(UserSpecialistRole(user_id=coach_id, role=SpecialistRole.COACH))
    db.commit()

    claimed = client.post(
        f"/api/v1/coach/workout-reviews/{review.id}/claim",
        headers=ORIGIN,
    )
    assert claimed.status_code == 200, claimed.text
    submitted = client.post(
        f"/api/v1/coach/workout-reviews/{review.id}/submit",
        headers=ORIGIN,
        json={"expected_revision": 1},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "awaiting_member_acceptance"

    mine = client.get("/api/v1/coach/workout-reviews?view=mine")
    assert mine.status_code == 200, mine.text
    assert any(
        item["id"] == str(review.id)
        and item["status"] == "awaiting_member_acceptance"
        for item in mine.json()
    )

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    _login(client, member_email)
    current = client.get("/api/v1/workout-reviews/current")

    assert current.status_code == 200, current.text
    payload = current.json()
    assert payload["status"] == "awaiting_member_acceptance"
    assert payload["source_plan"]["status"] == "active"
    assert payload["proposed_plan"]["status"] == "pending_review"
    assert payload["difference_summary"] == []

    accepted = client.post(
        f"/api/v1/workout-reviews/{review.id}/accept",
        headers=ORIGIN,
        json={"expected_revision": 1},
    )

    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "approved"
    assert accepted.json()["proposed_plan"]["status"] == "active"


def test_member_action_is_owner_scoped_and_rejection_requires_explanation(
    client: TestClient,
    db: Session,
) -> None:
    member_email = f"owner-api-{uuid4()}@example.com"
    member_id = _register(client, member_email)
    plan = make_review_plan(db, member_id)
    review = ensure_pending_review(db, plan)
    db.commit()

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    coach_id = _register(client, f"coach-owner-api-{uuid4()}@example.com")
    db.add(UserSpecialistRole(user_id=coach_id, role=SpecialistRole.COACH))
    db.commit()
    assert client.post(
        f"/api/v1/coach/workout-reviews/{review.id}/claim",
        headers=ORIGIN,
    ).status_code == 200
    assert client.post(
        f"/api/v1/coach/workout-reviews/{review.id}/submit",
        headers=ORIGIN,
        json={"expected_revision": 1},
    ).status_code == 200

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    other_email = f"other-api-{uuid4()}@example.com"
    _register(client, other_email)
    forbidden = client.post(
        f"/api/v1/workout-reviews/{review.id}/accept",
        headers=ORIGIN,
        json={"expected_revision": 1},
    )
    assert forbidden.status_code == 409
    assert forbidden.json()["detail"]["code"] == "MEMBER_NOT_ALLOWED"

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    _login(client, member_email)
    missing_explanation = client.post(
        f"/api/v1/workout-reviews/{review.id}/reject",
        headers=ORIGIN,
        json={"expected_revision": 1, "explanation": "  "},
    )
    assert missing_explanation.status_code == 422

    rejected = client.post(
        f"/api/v1/workout-reviews/{review.id}/reject",
        headers=ORIGIN,
        json={"expected_revision": 1, "explanation": "روز دوم نیاز به اصلاح دارد"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "member_changes_requested"
