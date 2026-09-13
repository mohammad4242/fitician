from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.access_management.models import AccessCampaignRedemption
from app.auth.models import User
from app.entitlements.enums import GrantSource
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


def _campaign_redemptions(db: Session, user_id) -> list[AccessCampaignRedemption]:
    return list(
        db.scalars(
            select(AccessCampaignRedemption).where(
                AccessCampaignRedemption.user_id == user_id,
            )
        ).all()
    )


def test_new_email_signup_uses_database_campaign_and_login_is_idempotent(
    client: TestClient,
    db: Session,
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
    assert grant.source is GrantSource.LAUNCH_TRIAL
    assert grant.idempotency_key == "campaign:launch_trial_v1:v1"

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
