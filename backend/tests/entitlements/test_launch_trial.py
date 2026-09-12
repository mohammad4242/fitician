from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import PhoneOtpChallenge, User
from app.entitlements.models import UserAccessGrant

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


class GoogleProvider:
    def __init__(self, *, sub: str, email: str | None, verified: bool = True) -> None:
        self.identity = SimpleNamespace(
            sub=sub,
            email=email,
            email_verified=verified,
            name="Trial Member",
            picture=None,
        )

    def verify(self, _credential: str) -> SimpleNamespace:
        return self.identity


class AppleProvider:
    def __init__(self, *, sub: str, email: str | None, verified: bool = True) -> None:
        self.identity = SimpleNamespace(
            sub=sub,
            email=email,
            email_verified=verified,
            name="Trial Member",
            picture=None,
        )

    def verify(self, _token: str, _nonce: str) -> SimpleNamespace:
        return self.identity


def grant_count(db: Session, user_id) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(UserAccessGrant)
            .where(
                UserAccessGrant.user_id == user_id,
                UserAccessGrant.idempotency_key == "launch_trial:v1",
            )
        )
        or 0
    )


def test_email_registration_gets_one_trial_and_repeated_registration_does_not_add_one(
    client: TestClient,
    db: Session,
) -> None:
    first = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "email-trial@example.com", "password": PASSWORD},
    )
    assert first.status_code == 201
    user = db.get(User, first.json()["id"])
    assert user is not None
    assert grant_count(db, user.id) == 1

    repeat = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "email-trial@example.com", "password": PASSWORD},
    )
    assert repeat.status_code == 409
    assert grant_count(db, user.id) == 1


def test_google_new_user_gets_one_trial_and_existing_login_keeps_one(
    client: TestClient,
    db: Session,
) -> None:
    provider = GoogleProvider(sub="trial-google", email="google-trial@example.com")
    client.app.state.google_identity_provider = provider

    first = client.post(
        "/api/v1/auth/google",
        headers=ORIGIN,
        json={"credential": "google-token"},
    )
    second = client.post(
        "/api/v1/auth/google",
        headers=ORIGIN,
        json={"credential": "google-token"},
    )

    assert first.status_code == second.status_code == 200
    user = db.scalar(select(User).where(User.google_sub == "trial-google"))
    assert user is not None
    assert grant_count(db, user.id) == 1


def test_google_link_to_existing_email_account_does_not_create_a_second_trial(
    client: TestClient,
    db: Session,
) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "google-link-trial@example.com", "password": PASSWORD},
    )
    assert registered.status_code == 201
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    client.app.state.google_identity_provider = GoogleProvider(
        sub="linked-google",
        email="google-link-trial@example.com",
    )

    linked = client.post(
        "/api/v1/auth/google",
        headers=ORIGIN,
        json={"credential": "google-token"},
    )

    assert linked.status_code == 200
    user = db.get(User, registered.json()["id"])
    assert user is not None
    assert grant_count(db, user.id) == 1
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_apple_new_user_and_existing_email_link_have_one_trial(
    client: TestClient,
    db: Session,
) -> None:
    client.app.state.apple_identity_provider = AppleProvider(
        sub="trial-apple",
        email="apple-trial@example.com",
    )
    new_user = client.post(
        "/api/v1/auth/mobile/apple",
        json={
            "app_version": "1.0.0",
            "device_id": "trial-apple-device",
            "device_name": "iPhone",
            "identity_token": "apple-token",
            "nonce": "nonce",
            "platform": "ios",
        },
    )
    assert new_user.status_code == 200
    user = db.scalar(select(User).where(User.apple_sub == "trial-apple"))
    assert user is not None
    assert grant_count(db, user.id) == 1

    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "apple-link-trial@example.com", "password": PASSWORD},
    )
    assert registered.status_code == 201
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    client.app.state.apple_identity_provider = AppleProvider(
        sub="linked-apple",
        email="apple-link-trial@example.com",
    )
    linked = client.post(
        "/api/v1/auth/mobile/apple",
        json={
            "app_version": "1.0.0",
            "device_id": "trial-apple-link-device",
            "device_name": "iPhone",
            "identity_token": "apple-token",
            "nonce": "nonce",
            "platform": "ios",
        },
    )
    assert linked.status_code == 200
    linked_user = db.get(User, registered.json()["id"])
    assert linked_user is not None
    assert grant_count(db, linked_user.id) == 1


def test_phone_new_user_gets_one_trial_and_existing_login_keeps_one(
    client: TestClient,
    db: Session,
) -> None:
    first_send = client.post(
        "/api/v1/auth/phone/send-otp",
        headers=ORIGIN,
        json={"phone_number": "09123456789"},
    )
    assert first_send.status_code == 202
    first_code = client.app.state.sms_provider.deliveries[-1].code
    first_login = client.post(
        "/api/v1/auth/phone/verify-otp",
        headers=ORIGIN,
        json={"phone_number": "09123456789", "code": first_code},
    )
    assert first_login.status_code == 200
    user = db.scalar(select(User).where(User.phone_number == "+989123456789"))
    assert user is not None
    assert grant_count(db, user.id) == 1

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    challenge = db.scalar(
        select(PhoneOtpChallenge)
        .where(PhoneOtpChallenge.phone_number == "+989123456789")
        .order_by(PhoneOtpChallenge.created_at.desc())
    )
    assert challenge is not None
    challenge.resend_available_at = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    second_send = client.post(
        "/api/v1/auth/phone/send-otp",
        headers=ORIGIN,
        json={"phone_number": "09123456789"},
    )
    assert second_send.status_code == 202
    second_code = client.app.state.sms_provider.deliveries[-1].code
    second_login = client.post(
        "/api/v1/auth/phone/verify-otp",
        headers=ORIGIN,
        json={"phone_number": "09123456789", "code": second_code},
    )
    assert second_login.status_code == 200
    assert grant_count(db, user.id) == 1
