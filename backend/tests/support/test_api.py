from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.notifications.models import NotificationInboxItem, NotificationOutboxEvent
from tests.workout_reviews.test_review_access import _login, _user

ORIGIN = {"Origin": "http://localhost:5173"}
BASE = "/api/v1/support/tickets"
ADMIN = "/api/v1/support/admin/tickets"


def create(client, **overrides):
    payload = {
        "category": "technical",
        "subject": "Cannot open my plan",
        "description": "The page keeps loading",
        "request_id": str(uuid4()),
        "metadata": {"platform": "web", "app_version": "1.0", "locale": "fa"},
        **overrides,
    }
    response = client.post(BASE, headers=ORIGIN, json=payload)
    assert response.status_code == 201, response.text
    return response.json(), payload


def setup(client, db, settings, *, admin=False):
    user = _user(db)
    user.is_admin = admin
    _login(client, db, settings, user)
    return user


def reply(client, ticket_id, *, admin=False, **overrides):
    payload = {"body": "Please help", "request_id": str(uuid4()), **overrides}
    path = f"{ADMIN if admin else BASE}/{ticket_id}/messages"
    return client.post(path, headers=ORIGIN, json=payload), payload


def test_create_list_without_profile_and_idempotent_retry(client, db, test_settings):
    user = setup(client, db, test_settings)
    ticket, payload = create(client)
    assert ticket["user_id"] == str(user.id)
    assert ticket["status"] == "open"
    repeated = client.post(BASE, headers=ORIGIN, json=payload)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == ticket["id"]
    assert client.get(BASE).json()["items"][0]["id"] == ticket["id"]
    detail = client.get(f"{BASE}/{ticket['id']}").json()
    assert detail["messages"][0]["body"] == payload["description"]
    assert detail["unread_count"] == 0
    assert (
        client.post(BASE, headers=ORIGIN, json={**payload, "subject": "Other"}).status_code == 409
    )
    assert (
        client.post(
            BASE, headers=ORIGIN, json={**payload, "metadata": {"platform": "ios"}}
        ).status_code
        == 409
    )


def test_cross_user_and_anonymous_access_blocked(client, db, test_settings):
    setup(client, db, test_settings)
    ticket, _ = create(client)
    setup(client, db, test_settings)
    path = f"{BASE}/{ticket['id']}"
    assert client.get(BASE).json()["items"] == []
    assert client.get(path).status_code == 404
    assert client.get(path + "/messages").status_code == 404
    assert reply(client, ticket["id"])[0].status_code == 404
    assert (
        client.put(path + "/read", headers=ORIGIN, json={"message_id": str(uuid4())}).status_code
        == 404
    )
    assert client.get(ADMIN).status_code == 403
    assert reply(client, ticket["id"], admin=True)[0].status_code == 403
    assert (
        client.patch(
            f"{ADMIN}/{ticket['id']}/status",
            headers=ORIGIN,
            json={"status": "closed", "request_id": str(uuid4())},
        ).status_code
        == 403
    )
    client.cookies.clear()
    assert client.get(BASE).status_code == 401
    assert client.post(BASE, headers=ORIGIN, json={}).status_code == 401


def test_admin_reply_notification_and_member_reopen(client, db, test_settings):
    member = setup(client, db, test_settings)
    ticket, _ = create(client)
    admin = setup(client, db, test_settings, admin=True)
    response, payload = reply(client, ticket["id"], admin=True, body="Try again now")
    assert response.status_code == 201
    assert (
        reply(client, ticket["id"], admin=True, **payload)[0].json()["id"] == response.json()["id"]
    )
    detail = client.get(f"{ADMIN}/{ticket['id']}").json()
    assert detail["ticket"]["status"] == "awaiting_user"
    assert detail["viewer_id"] == str(admin.id)
    notifications = db.scalars(
        select(NotificationInboxItem).where(NotificationInboxItem.user_id == member.id)
    ).all()
    assert len(notifications) == 1
    assert notifications[0].event_type == "support_ticket_reply"
    assert notifications[0].payload["data"]["ticket_id"] == ticket["id"]
    assert "Try again now" not in str(notifications[0].payload)
    assert db.scalar(select(func.count()).select_from(NotificationOutboxEvent)) == 1
    _login(client, db, test_settings, member)
    assert client.get(f"{BASE}/{ticket['id']}").json()["unread_count"] == 1
    assert (
        client.put(
            f"{BASE}/{ticket['id']}/read",
            headers=ORIGIN,
            json={"message_id": response.json()["id"]},
        ).status_code
        == 204
    )
    assert client.get(f"{BASE}/{ticket['id']}").json()["unread_count"] == 0
    assert reply(client, ticket["id"])[0].status_code == 201
    assert client.get(f"{BASE}/{ticket['id']}").json()["ticket"]["status"] == "open"


def test_status_retry_closed_thread_and_audit(client, db, test_settings):
    member = setup(client, db, test_settings)
    ticket, _ = create(client)
    message, message_payload = reply(client, ticket["id"])
    assert message.status_code == 201
    setup(client, db, test_settings, admin=True)
    path = f"{ADMIN}/{ticket['id']}/status"
    payload = {"status": "resolved", "request_id": str(uuid4())}
    resolved = client.patch(path, headers=ORIGIN, json=payload)
    assert resolved.status_code == 200
    assert resolved.json()["resolved_at"] is not None
    repeated = client.patch(path, headers=ORIGIN, json=payload)
    assert repeated.json()["updated_at"] == resolved.json()["updated_at"]
    assert (
        client.patch(path, headers=ORIGIN, json={**payload, "status": "closed"}).status_code == 409
    )
    _login(client, db, test_settings, member)
    assert reply(client, ticket["id"])[0].status_code == 201
    assert client.get(f"{BASE}/{ticket['id']}").json()["ticket"]["resolved_at"] is None
    setup(client, db, test_settings, admin=True)
    assert (
        client.patch(
            path, headers=ORIGIN, json={"status": "closed", "request_id": str(uuid4())}
        ).status_code
        == 200
    )
    assert reply(client, ticket["id"], admin=True)[0].status_code == 409
    _login(client, db, test_settings, member)
    assert reply(client, ticket["id"])[0].status_code == 409
    assert reply(client, ticket["id"], **message_payload)[0].json()["id"] == message.json()["id"]
    from app.support.models import SupportStatusEvent

    assert db.scalar(select(func.count()).select_from(SupportStatusEvent)) == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"subject": " "},
        {"description": "\x00bad"},
        {"category": "invalid"},
        {"metadata": {"platform": "web", "device_id": "private"}},
        {"metadata": {"platform": "unknown"}},
        {"subject": "a" * 161},
    ],
)
def test_validate_and_csrf(client, db, test_settings, changes):
    setup(client, db, test_settings)
    payload = {
        "category": "technical",
        "subject": "Help",
        "description": "Please help",
        "request_id": str(uuid4()),
        **changes,
    }
    assert client.post(BASE, headers=ORIGIN, json=payload).status_code == 422
    assert client.post(BASE, json={**payload, "subject": "Help"}).status_code == 403


def test_private_message_cursors_and_request_conflicts(client, db, test_settings):
    setup(client, db, test_settings)
    ticket, _ = create(client)
    other, _ = create(client)
    first, payload = reply(client, ticket["id"], body="First")
    second, _ = reply(client, ticket["id"], body="Second")
    assert first.status_code == second.status_code == 201
    assert reply(client, ticket["id"], **{**payload, "body": "Changed"})[0].status_code == 409
    assert reply(client, other["id"], **payload)[0].status_code == 409
    page = client.get(f"{BASE}/{ticket['id']}/messages", params={"limit": 1}).json()
    assert page["messages"][0]["id"] == second.json()["id"]
    older = client.get(
        f"{BASE}/{ticket['id']}/messages", params={"limit": 1, "before": page["older_cursor"]}
    ).json()
    assert older["messages"][0]["id"] == first.json()["id"]
    assert (
        client.get(
            f"{BASE}/{other['id']}/messages", params={"before": first.json()["id"]}
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"{BASE}/{other['id']}/read", headers=ORIGIN, json={"message_id": first.json()["id"]}
        ).status_code
        == 404
    )
    assert client.get(BASE, params={"limit": 1}).json()["older_cursor"] is not None


def test_admin_queue_filters_counts_and_support_only_projection(client, db, test_settings):
    setup(client, db, test_settings)
    first, _ = create(client, subject="Payment problem", category="billing")
    create(client, subject="Android issue")
    setup(client, db, test_settings, admin=True)
    queue = client.get(ADMIN, params={"category": "billing", "search": "Payment"}).json()
    assert [row["id"] for row in queue["items"]] == [first["id"]]
    assert queue["open_count"] == 2
    assert queue["total"] == 1
    assert (
        client.patch(
            f"{ADMIN}/{first['id']}/status",
            headers=ORIGIN,
            json={"status": "resolved", "request_id": str(uuid4())},
        ).status_code
        == 200
    )
    assert client.get(ADMIN, params={"status": "open"}).json()["total"] == 1
    detail = client.get(f"{ADMIN}/{first['id']}").json()
    assert set(detail) == {"ticket", "messages", "viewer_id", "unread_count", "older_cursor"}
    assert "profile" not in str(detail)
    assert "body_photo" not in str(detail)


def test_rate_limits_allow_exact_retries(client, db, test_settings):
    test_settings.support_ticket_create_limit = 1
    test_settings.support_ticket_reply_limit = 1
    setup(client, db, test_settings)
    ticket, payload = create(client)
    assert client.post(BASE, headers=ORIGIN, json=payload).status_code == 201
    limited = client.post(BASE, headers=ORIGIN, json={**payload, "request_id": str(uuid4())})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0
    sent, payload = reply(client, ticket["id"])
    assert sent.status_code == 201
    assert reply(client, ticket["id"], **payload)[0].status_code == 201
    assert reply(client, ticket["id"])[0].status_code == 429


def test_revoked_admin_and_foreign_ticket_cursor(client, db, test_settings):
    owner = setup(client, db, test_settings)
    ticket, _ = create(client)
    admin = setup(client, db, test_settings, admin=True)
    assert client.get(f"{ADMIN}/{ticket['id']}").status_code == 200
    admin.is_admin = False
    db.commit()
    assert client.get(f"{ADMIN}/{ticket['id']}").status_code == 403
    assert client.get(BASE, params={"before": ticket["id"]}).status_code == 404
    _login(client, db, test_settings, owner)
    assert client.get(f"{BASE}/{ticket['id']}").status_code == 200


def test_notification_failure_rolls_back_reply_and_status(client, db, test_settings, monkeypatch):
    from app.support import service
    from app.support.models import SupportMessage, SupportTicket
    from app.support.schemas import ReplyInput

    setup(client, db, test_settings)
    ticket, _ = create(client)
    admin = setup(client, db, test_settings, admin=True)

    original_publish = service.publish_inbox_notification

    def fail_notification(*args, **kwargs):
        original_publish(*args, **kwargs)
        raise RuntimeError("Notification persistence failed")

    monkeypatch.setattr(service, "publish_inbox_notification", fail_notification)
    with pytest.raises(RuntimeError, match="Notification persistence failed"):
        service.send_reply(
            db, admin, UUID(ticket["id"]), ReplyInput(body="Reply", request_id=uuid4()), admin=True
        )
    db.rollback()
    stored = db.get(SupportTicket, UUID(ticket["id"]))
    assert stored.status.value == "open"
    assert (
        db.scalar(
            select(func.count())
            .select_from(SupportMessage)
            .where(SupportMessage.ticket_id == stored.id)
        )
        == 1
    )
    assert db.scalar(select(func.count()).select_from(NotificationInboxItem)) == 0
    assert db.scalar(select(func.count()).select_from(NotificationOutboxEvent)) == 0


def test_concurrent_create_and_reply_retry_are_single_records(db):
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import create_engine, delete
    from sqlalchemy.orm import Session

    from app.auth.models import User
    from app.support.models import SupportMessage, SupportTicket
    from app.support.schemas import ReplyInput, TicketInput
    from app.support.service import create_ticket, send_reply
    from tests.conftest import TEST_DATABASE_URL

    # Separate committed sessions are necessary to exercise real PostgreSQL locks.
    engine = create_engine(TEST_DATABASE_URL)
    with Session(engine) as isolated:
        user = User(google_sub=f"support-concurrency-{uuid4()}")
        isolated.add(user)
        isolated.commit()
        user_id = user.id
    payload = TicketInput(
        category="technical", subject="Retry", description="Help", request_id=uuid4()
    )
    reply_payload = ReplyInput(body="More information", request_id=uuid4())

    def create_once(_):
        with Session(engine) as isolated:
            return create_ticket(isolated, isolated.get(User, user_id), payload).id

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            ticket_ids = list(executor.map(create_once, range(2)))
        assert ticket_ids[0] == ticket_ids[1]

        def reply_once(_):
            with Session(engine) as isolated:
                return send_reply(
                    isolated, isolated.get(User, user_id), ticket_ids[0], reply_payload, admin=False
                ).id

        with ThreadPoolExecutor(max_workers=2) as executor:
            message_ids = list(executor.map(reply_once, range(2)))
        assert message_ids[0] == message_ids[1]
        with Session(engine) as isolated:
            assert (
                isolated.scalar(
                    select(func.count())
                    .select_from(SupportTicket)
                    .where(SupportTicket.user_id == user_id)
                )
                == 1
            )
            assert (
                isolated.scalar(
                    select(func.count())
                    .select_from(SupportMessage)
                    .where(SupportMessage.ticket_id == ticket_ids[0])
                )
                == 2
            )
    finally:
        with Session(engine) as isolated:
            isolated.execute(delete(User).where(User.id == user_id))
            isolated.commit()
        engine.dispose()


def test_reply_refreshes_locked_ticket_status(db):
    from datetime import UTC, datetime

    from fastapi import HTTPException
    from sqlalchemy import update

    from app.support.models import SupportTicket
    from app.support.schemas import ReplyInput, TicketInput
    from app.support.service import create_ticket, send_reply

    user = _user(db)
    ticket = create_ticket(
        db,
        user,
        TicketInput(category="account", subject="Help", description="Question", request_id=uuid4()),
    )
    cached = db.get(SupportTicket, ticket.id)
    db.execute(
        update(SupportTicket)
        .where(SupportTicket.id == ticket.id)
        .values(status="closed", resolved_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    assert cached.status.value == "open"
    with pytest.raises(HTTPException) as error:
        send_reply(db, user, ticket.id, ReplyInput(body="Reply", request_id=uuid4()), admin=False)
    assert error.value.status_code == 409
