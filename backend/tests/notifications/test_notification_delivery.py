from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.notifications.fcm import FcmSendOutcome
from app.notifications.models import (
    NotificationDevice,
    NotificationDeviceToken,
    NotificationEventDelivery,
)
from app.notifications.outbox import enqueue_notification_event
from app.notifications.worker import run_delivery_once, run_outbox_once


class FakeProvider:
    def __init__(self, *outcomes: FcmSendOutcome) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[str] = []

    def send(
        self,
        *,
        token_value: str,
        event_type: str,
        payload: dict[str, object],
    ) -> FcmSendOutcome:
        del event_type, payload
        self.calls.append(token_value)
        return self.outcomes.pop(0)


def _pending_delivery(db: Session) -> tuple[NotificationEventDelivery, NotificationDeviceToken]:
    user = User(email=f"delivery-{uuid4()}@example.com", password_hash="test-hash")
    db.add(user)
    db.flush()
    device = NotificationDevice(
        user_id=user.id,
        device_id="device-1",
        platform="android",
        app_version="1.0.0",
    )
    db.add(device)
    db.flush()
    token = NotificationDeviceToken(
        device_id=device.id,
        provider="fcm",
        token_hash=sha256(b"delivery-token").hexdigest(),
        token_value="delivery-token",
    )
    db.add(token)
    enqueue_notification_event(
        db,
        user_id=user.id,
        event_type="plan_approved",
        category="approved_plans",
        deduplication_key="plan:1:approved",
        payload={"title": "Plan ready", "body": "Your plan is ready."},
    )
    db.commit()
    assert run_outbox_once(db, worker_id="fanout", now=datetime.now(UTC)) == 1
    delivery = db.scalar(select(NotificationEventDelivery))
    assert delivery is not None
    return delivery, token


def test_delivery_success_is_sent_once(db: Session) -> None:
    delivery, _token = _pending_delivery(db)
    provider = FakeProvider(FcmSendOutcome.sent("message-1"))

    assert run_delivery_once(db, provider=provider, worker_id="sender-1") == 1
    assert run_delivery_once(db, provider=provider, worker_id="sender-2") == 0

    db.refresh(delivery)
    assert delivery.status == "sent"
    assert delivery.provider_message_id == "message-1"
    assert delivery.sent_at is not None
    assert delivery.attempt_count == 1
    assert provider.calls == ["delivery-token"]


def test_retry_waits_then_succeeds_without_duplicate_delivery(db: Session) -> None:
    delivery, _token = _pending_delivery(db)
    first_now = datetime.now(UTC)
    provider = FakeProvider(
        FcmSendOutcome.retryable("UNAVAILABLE"),
        FcmSendOutcome.sent("message-2"),
    )

    assert run_delivery_once(
        db,
        provider=provider,
        worker_id="sender-1",
        now=first_now,
        retry_base_seconds=10,
        retry_max_seconds=60,
    ) == 1
    db.refresh(delivery)
    assert delivery.status == "pending"
    assert delivery.attempt_count == 1
    assert delivery.next_attempt_at == first_now + timedelta(seconds=10)
    assert run_delivery_once(db, provider=provider, worker_id="sender-2", now=first_now) == 0
    assert run_delivery_once(
        db,
        provider=provider,
        worker_id="sender-2",
        now=first_now + timedelta(seconds=10),
        retry_base_seconds=10,
        retry_max_seconds=60,
    ) == 1

    db.refresh(delivery)
    assert delivery.status == "sent"
    assert delivery.attempt_count == 2
    assert provider.calls == ["delivery-token", "delivery-token"]


def test_invalid_token_is_cleaned_up_and_dead_lettered(db: Session) -> None:
    delivery, token = _pending_delivery(db)
    provider = FakeProvider(FcmSendOutcome.invalid_token("UNREGISTERED"))

    assert run_delivery_once(db, provider=provider, worker_id="sender-1") == 1

    db.refresh(delivery)
    db.refresh(token)
    assert delivery.status == "dead_letter"
    assert delivery.dead_letter_at is not None
    assert delivery.last_error == "UNREGISTERED"
    assert token.invalid_at is not None
    assert token.invalid_reason == "UNREGISTERED"


def test_retry_exhaustion_moves_delivery_to_dead_letter(db: Session) -> None:
    delivery, _token = _pending_delivery(db)
    now = datetime.now(UTC)
    provider = FakeProvider(
        FcmSendOutcome.retryable("UNAVAILABLE"),
        FcmSendOutcome.retryable("UNAVAILABLE"),
    )

    assert run_delivery_once(
        db,
        provider=provider,
        worker_id="sender-1",
        now=now,
        max_attempts=2,
        retry_base_seconds=1,
        retry_max_seconds=1,
    ) == 1
    assert run_delivery_once(
        db,
        provider=provider,
        worker_id="sender-1",
        now=now + timedelta(seconds=1),
        max_attempts=2,
        retry_base_seconds=1,
        retry_max_seconds=1,
    ) == 1

    db.refresh(delivery)
    assert delivery.status == "dead_letter"
    assert delivery.attempt_count == 2
    assert delivery.dead_letter_at is not None
    assert provider.calls == ["delivery-token", "delivery-token"]


def test_delivery_routes_each_token_to_its_provider(db: Session) -> None:
    delivery, token = _pending_delivery(db)
    token.provider = "apns"
    db.commit()
    provider = FakeProvider(FcmSendOutcome.sent("apns-message"))

    assert run_delivery_once(
        db,
        provider={"apns": provider},
        worker_id="sender-apns",
    ) == 1

    db.refresh(delivery)
    assert delivery.status == "sent"
    assert provider.calls == ["delivery-token"]


def test_old_delivery_is_dead_lettered_after_token_moves_to_another_user(db: Session) -> None:
    user_a = User(email=f"delivery-a-{uuid4()}@example.com", password_hash="test-hash")
    user_b = User(email=f"delivery-b-{uuid4()}@example.com", password_hash="test-hash")
    db.add_all([user_a, user_b])
    db.flush()
    device_a = NotificationDevice(
        user_id=user_a.id,
        device_id="device-a",
        platform="android",
        app_version="1.0.0",
    )
    device_b = NotificationDevice(
        user_id=user_b.id,
        device_id="device-b",
        platform="android",
        app_version="1.0.0",
    )
    db.add_all([device_a, device_b])
    db.flush()
    token = NotificationDeviceToken(
        device_id=device_a.id,
        provider="fcm",
        token_hash=sha256(b"shared-token").hexdigest(),
        token_value="shared-token",
    )
    db.add(token)
    event_a = enqueue_notification_event(
        db,
        user_id=user_a.id,
        event_type="plan_approved",
        category="approved_plans",
        deduplication_key="user-a:plan-approved",
        payload={"title": "Plan ready", "body": "A's plan is ready."},
    )
    db.commit()
    assert run_outbox_once(db, worker_id="fanout-a") == 1
    delivery_a = db.scalar(
        select(NotificationEventDelivery).where(
            NotificationEventDelivery.event_id == event_a.id
        )
    )
    assert delivery_a is not None and delivery_a.token_id == token.id

    token.device_id = device_b.id
    db.commit()
    provider = FakeProvider(FcmSendOutcome.sent("message-b"))

    assert run_delivery_once(db, provider=provider, worker_id="sender-a") == 1

    db.refresh(delivery_a)
    assert provider.calls == []
    assert delivery_a.status == "dead_letter"
    assert delivery_a.dead_letter_at is not None
    assert delivery_a.last_error == "TOKEN_OWNER_MISMATCH"
    assert delivery_a.locked_by is None
    assert delivery_a.locked_at is None

    event_b = enqueue_notification_event(
        db,
        user_id=user_b.id,
        event_type="plan_approved",
        category="approved_plans",
        deduplication_key="user-b:plan-approved",
        payload={"title": "Plan ready", "body": "B's plan is ready."},
    )
    db.commit()
    assert run_outbox_once(db, worker_id="fanout-b") == 1
    delivery_b = db.scalar(
        select(NotificationEventDelivery).where(
            NotificationEventDelivery.event_id == event_b.id
        )
    )
    assert delivery_b is not None and delivery_b.token_id == token.id

    assert run_delivery_once(db, provider=provider, worker_id="sender-b") == 1

    db.refresh(delivery_b)
    assert delivery_b.status == "sent"
    assert provider.calls == ["shared-token"]
