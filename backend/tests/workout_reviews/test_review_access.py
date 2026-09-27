from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.models import AuthSession, User
from app.auth.security import make_session_token
from app.body_analysis.enums import SpecialistRole
from app.body_analysis.models import UserSpecialistRole
from app.config import Settings
from app.workout_reviews.enums import WorkoutReviewStatus
from app.workout_reviews.repository import ensure_pending_review, supersede_open_review
from app.workout_reviews.service import WorkoutReviewService
from tests.profile.test_review_summary import _seed_profile
from tests.workout_reviews.test_api import _plan


def _user(db: Session, *, coach: bool = False) -> User:
    user = User(google_sub=f"review-access-{uuid4()}")
    db.add(user)
    db.flush()
    if coach:
        db.add(UserSpecialistRole(user_id=user.id, role=SpecialistRole.COACH))
    return user


def _login(client: TestClient, db: Session, settings: Settings, user: User) -> None:
    token, token_hash = make_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    db.commit()
    client.cookies.clear()
    client.cookies.set(settings.session_cookie_name, token)


@pytest.mark.parametrize("terminal_status", ["approved", "rejected", "superseded"])
def test_terminal_review_detail_keeps_assignment_private(
    client: TestClient, db: Session, test_settings: Settings, terminal_status: str
) -> None:
    member = _user(db)
    assigned = _user(db, coach=True)
    other = _user(db, coach=True)
    _seed_profile(db, member.id)
    review = ensure_pending_review(db, _plan(db, member.id))
    service = WorkoutReviewService(db)
    service.claim(review.id, assigned.id)
    _login(client, db, test_settings, other)
    url = f"/api/v1/coach/workout-reviews/{review.id}"
    assert client.get(url).status_code == 409

    if terminal_status == "approved":
        service.submit_for_member(review.id, assigned.id, expected_revision=review.draft_revision)
        service.accept_by_member(review.id, member.id)
    elif terminal_status == "rejected":
        service.reject(
            review.id,
            assigned.id,
            expected_revision=review.draft_revision,
            explanation="A new plan is needed",
        )
    else:
        supersede_open_review(db, review.source_plan_id)
        db.commit()
    assert review.status == terminal_status

    denied = client.get(url)
    assert denied.status_code == 409
    assert denied.json()["detail"]["code"] == "REVIEW_ALREADY_CLAIMED"
    assert "controlled_hypertension" not in denied.text
    assert "profile_summary" not in denied.json()

    _login(client, db, test_settings, assigned)
    allowed = client.get(url)
    assert allowed.status_code == 200
    summary = allowed.json()["profile_summary"]
    assert summary["user_id"] == str(member.id)
    assert summary["medical"]["conditions"][0]["code"] == "controlled_hypertension"


def test_approved_queue_only_lists_the_viewers_reviews(
    client: TestClient, db: Session, test_settings: Settings
) -> None:
    coaches = [_user(db, coach=True), _user(db, coach=True)]
    reviews = []
    service = WorkoutReviewService(db)
    for coach in coaches:
        member = _user(db)
        review = ensure_pending_review(db, _plan(db, member.id))
        service.claim(review.id, coach.id)
        service.submit_for_member(review.id, coach.id, expected_revision=review.draft_revision)
        service.accept_by_member(review.id, member.id)
        reviews.append(review)

    for coach, review in zip(coaches, reviews, strict=True):
        _login(client, db, test_settings, coach)
        response = client.get("/api/v1/coach/workout-reviews?view=approved")
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [str(review.id)]


def test_unassigned_superseded_review_is_not_shared(
    client: TestClient, db: Session, test_settings: Settings
) -> None:
    member = _user(db)
    coach = _user(db, coach=True)
    review = ensure_pending_review(db, _plan(db, member.id))
    _login(client, db, test_settings, coach)
    url = f"/api/v1/coach/workout-reviews/{review.id}"
    assert client.get(url).status_code == 200  # Shared pending queue remains available.
    supersede_open_review(db, review.source_plan_id)
    db.commit()
    assert review.status is WorkoutReviewStatus.SUPERSEDED
    assert client.get(url).status_code == 409
