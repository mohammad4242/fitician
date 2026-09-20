from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.models import AccessCampaign, AccessCampaignRedemption
from app.auth.models import PhoneOtpChallenge, User
from app.auth.providers import FakeSmsProvider
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.models import UserAccessGrant

ORIGIN = {"Origin": "http://localhost:5173"}


class GoogleProvider:
    def __init__(self, sub: str, email: str) -> None:
        self.identity = SimpleNamespace(
            sub=sub,
            email=email,
            email_verified=True,
            name="Campaign member",
            picture=None,
        )

    def verify(self, _credential: str) -> SimpleNamespace:
        return self.identity


class AppleProvider:
    def __init__(self, sub: str, email: str) -> None:
        self.identity = SimpleNamespace(
            sub=sub,
            email=email,
            email_verified=True,
            name="Campaign member",
            picture=None,
        )

    def verify(self, _credential: str, _nonce: str) -> SimpleNamespace:
        return self.identity


def _campaign_redemptions(db: Session, user_id) -> list[AccessCampaignRedemption]:
    return list(
        db.scalars(
            select(AccessCampaignRedemption).where(
                AccessCampaignRedemption.user_id == user_id,
            )
        ).all()
    )


@pytest.fixture
def signup_bonus(db: Session) -> AccessCampaign:
    admin = User(email="signup-bonus-test-admin@example.com", password_hash="hash")
    db.add(admin)
    db.flush()
    campaign = AccessCampaign(
        code="signup_bonus_test",
        name="Signup bonus test",
        kind=AccessCampaignKind.SIGNUP_BONUS,
        package_code=AccessPackageCode.COMPLETE,
        duration_days=42,
        term_weeks=6,
        is_active=True,
        created_by_user_id=admin.id,
    )
    db.add(campaign)
    db.flush()
    return campaign


def test_new_email_signup_uses_database_campaign_and_login_is_idempotent(
    client: TestClient,
    db: Session,
    signup_bonus: AccessCampaign,
) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "campaign-email@example.com", "password": "long password"},
    )
    assert registered.status_code == 201
    user = db.get(User, registered.json()["id"])
    assert user is not None
    redemptions = _campaign_redemptions(db, user.id)
    assert len(redemptions) == 1
    grant = db.get(UserAccessGrant, redemptions[0].access_grant_id)
    assert grant is not None
    assert grant.source is GrantSource.PROMOTION
    assert grant.package_code is AccessPackageCode.COMPLETE
    assert grant.term_weeks == 6
    assert grant.ends_at == redemptions[0].redeemed_at + timedelta(days=42)
    assert grant.idempotency_key == f"campaign:{signup_bonus.code}:v1"

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    login = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": "campaign-email@example.com", "password": "long password"},
    )

    assert login.status_code == 200
    assert len(_campaign_redemptions(db, user.id)) == 1
    assert (
        db.scalar(
            select(func.count())
            .select_from(UserAccessGrant)
            .where(UserAccessGrant.user_id == user.id)
        )
        == 1
    )


def test_google_link_to_existing_account_does_not_create_campaign_redemption(
    client: TestClient,
    db: Session,
    signup_bonus: AccessCampaign,
) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "campaign-google-link@example.com", "password": "long password"},
    )
    assert registered.status_code == 201
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    user = db.get(User, registered.json()["id"])
    assert user is not None
    before = len(_campaign_redemptions(db, user.id))
    client.app.state.google_identity_provider = GoogleProvider(
        "campaign-google-sub",
        "campaign-google-link@example.com",
    )

    linked = client.post(
        "/api/v1/auth/google",
        headers=ORIGIN,
        json={"credential": "google-token"},
    )

    assert linked.status_code == 200
    assert len(_campaign_redemptions(db, user.id)) == before


def test_apple_new_user_and_existing_account_link_do_not_duplicate_campaign_redemption(
    client: TestClient,
    db: Session,
    signup_bonus: AccessCampaign,
) -> None:
    client.app.state.apple_identity_provider = AppleProvider(
        "campaign-apple-new",
        "campaign-apple-new@example.com",
    )
    new_user_response = client.post(
        "/api/v1/auth/mobile/apple",
        json={
            "app_version": "1.0.0",
            "device_id": "campaign-apple-new-device",
            "device_name": "iPhone",
            "identity_token": "apple-token",
            "nonce": "nonce",
            "platform": "ios",
        },
    )
    assert new_user_response.status_code == 200
    new_user = db.get(User, new_user_response.json()["user"]["id"])
    assert new_user is not None
    assert len(_campaign_redemptions(db, new_user.id)) == 1

    repeated_response = client.post(
        "/api/v1/auth/mobile/apple",
        json={
            "app_version": "1.0.0",
            "device_id": "campaign-apple-repeat-device",
            "device_name": "iPhone",
            "identity_token": "apple-token",
            "nonce": "nonce",
            "platform": "ios",
        },
    )
    assert repeated_response.status_code == 200
    assert len(_campaign_redemptions(db, new_user.id)) == 1

    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "campaign-apple-link@example.com", "password": "long password"},
    )
    assert registered.status_code == 201
    linked_user = db.get(User, registered.json()["id"])
    assert linked_user is not None
    before = len(_campaign_redemptions(db, linked_user.id))
    client.app.state.apple_identity_provider = AppleProvider(
        "campaign-apple-link",
        "campaign-apple-link@example.com",
    )

    linked = client.post(
        "/api/v1/auth/mobile/apple",
        json={
            "app_version": "1.0.0",
            "device_id": "campaign-apple-link-device",
            "device_name": "iPhone",
            "identity_token": "apple-token",
            "nonce": "nonce",
            "platform": "ios",
        },
    )

    assert linked.status_code == 200
    assert linked.json()["user"]["id"] == str(linked_user.id)
    assert len(_campaign_redemptions(db, linked_user.id)) == before


def test_phone_new_user_and_existing_login_keep_one_campaign_redemption(
    client: TestClient,
    db: Session,
    signup_bonus: AccessCampaign,
) -> None:
    sms_provider = FakeSmsProvider()
    client.app.state.sms_provider = sms_provider
    phone = "09123456789"

    sent = client.post(
        "/api/v1/auth/phone/send-otp",
        headers=ORIGIN,
        json={"phone_number": phone},
    )
    assert sent.status_code == 202
    first_code = sms_provider.deliveries[-1].code
    verified = client.post(
        "/api/v1/auth/phone/verify-otp",
        headers=ORIGIN,
        json={"phone_number": phone, "code": first_code},
    )
    assert verified.status_code == 200
    user = db.scalar(select(User).where(User.phone_number == "+989123456789"))
    assert user is not None
    assert len(_campaign_redemptions(db, user.id)) == 1

    challenge = db.scalar(
        select(PhoneOtpChallenge)
        .where(PhoneOtpChallenge.phone_number == "+989123456789")
        .order_by(PhoneOtpChallenge.created_at.desc())
    )
    assert challenge is not None
    challenge.resend_available_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    second_sent = client.post(
        "/api/v1/auth/phone/send-otp",
        headers=ORIGIN,
        json={"phone_number": phone},
    )
    assert second_sent.status_code == 202
    second_verified = client.post(
        "/api/v1/auth/phone/verify-otp",
        headers=ORIGIN,
        json={"phone_number": phone, "code": sms_provider.deliveries[-1].code},
    )

    assert second_verified.status_code == 200
    assert len(_campaign_redemptions(db, user.id)) == 1
