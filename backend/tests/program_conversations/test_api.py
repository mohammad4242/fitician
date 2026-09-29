from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.body_analysis.models import UserSpecialistRole
from app.workout_reviews.repository import ensure_pending_review
from tests.workout_reviews.test_api import _plan
from tests.workout_reviews.test_review_access import _login, _user

ORIGIN = {"Origin": "http://localhost:5173"}


def test_text_conversation_is_private_idempotent_and_tracks_unread(client, db, test_settings):
    member, coach, stranger = _user(db), _user(db, coach=True), _user(db, coach=True)
    review = ensure_pending_review(db, _plan(db, member.id))
    review.claimed_by_user_id = coach.id
    review.lease_acquired_at = datetime.now(UTC)
    db.commit()
    url = f"/api/v1/program-conversations/workout/{review.id}"
    _login(client, db, test_settings, member)
    assert client.get(url).status_code == 200
    payload = {"body": "How should I choose the weight?", "request_id": str(uuid4())}
    sent = client.post(url, headers=ORIGIN, json=payload)
    assert sent.status_code == 201
    assert client.post(url, headers=ORIGIN, json=payload).json()["id"] == sent.json()["id"]
    _login(client, db, test_settings, coach)
    received = client.get(url).json()
    assert received["unread_count"] == 1
    assert received["messages"][0]["body"] == payload["body"]
    assert (
        client.put(
            url + "/read", headers=ORIGIN, json={"message_id": sent.json()["id"]}
        ).status_code
        == 204
    )
    assert client.get(url).json()["unread_count"] == 0
    _login(client, db, test_settings, stranger)
    assert client.get(url).status_code == 404
    review.claimed_by_user_id = stranger.id
    db.commit()
    assert client.get(url).status_code == 200
    _login(client, db, test_settings, coach)
    assert client.get(url).status_code == 404


def test_unassigned_and_role_revoked_conversations_cannot_send(client, db, test_settings):
    member, coach = _user(db), _user(db, coach=True)
    review = ensure_pending_review(db, _plan(db, member.id))
    db.commit()
    url = f"/api/v1/program-conversations/workout/{review.id}"
    _login(client, db, test_settings, member)
    assert client.get(url).json()["available"] is False
    assert (
        client.post(
            url, headers=ORIGIN, json={"body": "Question", "request_id": str(uuid4())}
        ).status_code
        == 409
    )
    review.claimed_by_user_id = coach.id
    review.lease_acquired_at = datetime.now(UTC)
    db.commit()
    role = db.scalar(select(UserSpecialistRole).where(UserSpecialistRole.user_id == coach.id))
    db.delete(role)
    db.commit()
    _login(client, db, test_settings, coach)
    assert client.get(url).status_code == 404


def test_nutrition_conversation_follows_physician_assignment(client, db, test_settings):
    from uuid import UUID

    from app.auth.models import User
    from app.nutrition.models import NutritionPlanPhysicianReview
    from tests.nutrition.test_clinical_review_api import _login_physician, _member_plan

    plan = _member_plan(client, db, email="conversation-nutrition@example.com")
    member = db.scalar(select(User).where(User.email == "conversation-nutrition@example.com"))
    physician = _login_physician(client, db)
    review = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == UUID(plan["id"])
        )
    )
    assert review is not None
    review.physician_user_id = physician.id
    db.commit()
    url = f"/api/v1/program-conversations/nutrition/{review.id}"
    _login(client, db, test_settings, member)
    assert client.get(f"/api/v1/program-conversations/nutrition/by-plan/{plan['id']}").json()[
        "review_id"
    ] == str(review.id)
    sent = client.post(
        url, headers=ORIGIN, json={"body": "Question about this meal", "request_id": str(uuid4())}
    )
    assert sent.status_code == 201
    _login(client, db, test_settings, physician)
    assert client.get(url).json()["unread_count"] == 1
    assert (
        client.post(
            url, headers=ORIGIN, json={"body": "Reply", "request_id": str(uuid4())}
        ).status_code
        == 201
    )


def test_message_request_conflict_blank_body_and_cookie_csrf_are_rejected(
    client, db, test_settings
):
    member, coach = _user(db), _user(db, coach=True)
    review = ensure_pending_review(db, _plan(db, member.id))
    review.claimed_by_user_id = coach.id
    review.lease_acquired_at = datetime.now(UTC)
    db.commit()
    _login(client, db, test_settings, member)
    url = f"/api/v1/program-conversations/workout/{review.id}"
    payload = {"body": "First message", "request_id": str(uuid4())}
    assert client.post(url, json=payload).status_code == 403
    assert client.post(url, headers=ORIGIN, json={**payload, "body": "   "}).status_code == 422
    assert client.post(url, headers=ORIGIN, json=payload).status_code == 201
    assert (
        client.post(url, headers=ORIGIN, json={**payload, "body": "Different message"}).status_code
        == 409
    )
    assert client.get(url, params={"limit": 1}).json()["messages"][0]["body"] == payload["body"]


def test_conversation_and_inbox_pagination_are_private(client, db, test_settings):
    member, coach, stranger = _user(db), _user(db, coach=True), _user(db)
    review = ensure_pending_review(db, _plan(db, member.id))
    review.claimed_by_user_id = coach.id
    review.lease_acquired_at = datetime.now(UTC)
    db.commit()
    url = f"/api/v1/program-conversations/workout/{review.id}"
    _login(client, db, test_settings, member)
    sent = []
    for body in ["First", "Second", "Third"]:
        response = client.post(url, headers=ORIGIN, json={"body": body, "request_id": str(uuid4())})
        assert response.status_code == 201
        sent.append(response.json()["id"])
    latest = client.get(url, params={"limit": 2}).json()
    previous = client.get(url, params={"limit": 2, "before": latest["older_cursor"]}).json()
    assert len(latest["messages"]) == 2
    assert len(previous["messages"]) == 1
    assert set(sent) == {message["id"] for message in latest["messages"] + previous["messages"]}
    _login(client, db, test_settings, coach)
    inbox = client.get("/api/v1/notifications/inbox", params={"limit": 2}).json()
    assert inbox["unread_count"] == 3
    item = inbox["items"][0]
    assert "First" not in str(item["payload"])
    assert "Second" not in str(item["payload"])
    assert (
        client.put(f"/api/v1/notifications/inbox/{item['id']}/read", headers=ORIGIN).status_code
        == 204
    )
    assert client.get("/api/v1/notifications/inbox").json()["unread_count"] == 2
    assert (
        len(
            client.get(
                "/api/v1/notifications/inbox", params={"before": inbox["older_cursor"]}
            ).json()["items"]
        )
        == 1
    )
    _login(client, db, test_settings, stranger)
    assert (
        client.put(f"/api/v1/notifications/inbox/{item['id']}/read", headers=ORIGIN).status_code
        == 404
    )
    assert (
        client.get("/api/v1/notifications/inbox", params={"before": item["id"]}).status_code == 404
    )
