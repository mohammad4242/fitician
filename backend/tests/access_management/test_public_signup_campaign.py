from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.models import AccessCampaign, AccessCampaignRedemption
from app.auth.models import User
from app.entitlements.enums import AccessPackageCode


@pytest.fixture
def make_campaign(db: Session) -> Callable[..., AccessCampaign]:
    owner = User(email="public-campaign-owner@example.com", password_hash="hash")
    db.add(owner)
    db.flush()

    def factory(**overrides: object) -> AccessCampaign:
        values: dict[str, object] = {
            "code": "public-signup-bonus",
            "name": "Public signup bonus",
            "kind": AccessCampaignKind.SIGNUP_BONUS,
            "package_code": AccessPackageCode.COMPLETE,
            "duration_days": 42,
            "term_weeks": 6,
            "is_active": True,
            "show_on_landing": True,
            "show_on_register": True,
            "public_badge_fa": "هدیه ثبت‌نام",
            "public_badge_en": "Signup Gift",
            "public_title_fa": "عنوان فارسی",
            "public_title_en": "English title",
            "public_message_fa": "پیام فارسی",
            "public_message_en": "English message",
            "public_cta_fa": "شروع",
            "public_cta_en": "Start",
            "created_by_user_id": owner.id,
        }
        values.update(overrides)
        campaign = AccessCampaign(**values)
        db.add(campaign)
        db.flush()
        return campaign

    return factory


def test_public_signup_campaign_endpoint_is_available_without_authentication(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/campaigns/signup/active",
        params={"surface": "landing"},
    )

    assert response.status_code == 200
    assert response.json() is None


def test_public_endpoint_returns_only_safe_active_campaign_fields(
    client: TestClient,
    make_campaign: Callable[..., AccessCampaign],
) -> None:
    make_campaign(max_total_redemptions=10)

    response = client.get("/api/v1/campaigns/signup/active", params={"surface": "landing"})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "public-signup-bonus"
    assert body["package_code"] == "complete"
    assert body["duration_days"] == 42
    assert body["term_weeks"] == 6
    assert body["public_title_fa"] == "عنوان فارسی"
    assert body["public_title_en"] == "English title"
    assert body["show_on_landing"] is True
    assert body["show_on_register"] is True
    assert {
        "id",
        "created_by_user_id",
        "redemption_count",
        "max_total_redemptions",
        "description",
    }.isdisjoint(body)


@pytest.mark.parametrize(
    "overrides",
    [
        {"is_active": False},
        {"available_from": datetime.now(UTC) + timedelta(days=1)},
        {"available_until": datetime.now(UTC) - timedelta(seconds=1)},
    ],
)
def test_public_endpoint_hides_inactive_or_out_of_window_campaigns(
    client: TestClient,
    make_campaign: Callable[..., AccessCampaign],
    overrides: dict[str, object],
) -> None:
    make_campaign(**overrides)

    response = client.get("/api/v1/campaigns/signup/active", params={"surface": "landing"})

    assert response.status_code == 200
    assert response.json() is None


def test_public_endpoint_hides_campaign_when_redemption_cap_is_reached(
    client: TestClient,
    db: Session,
    make_campaign: Callable[..., AccessCampaign],
) -> None:
    campaign = make_campaign(max_total_redemptions=1)
    user = User(email="public-campaign-redeemer@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    db.add(
        AccessCampaignRedemption(
            campaign_id=campaign.id,
            user_id=user.id,
            package_code_snapshot=AccessPackageCode.COMPLETE,
            duration_days_snapshot=42,
            term_weeks_snapshot=6,
        )
    )
    db.flush()

    response = client.get("/api/v1/campaigns/signup/active", params={"surface": "landing"})

    assert response.status_code == 200
    assert response.json() is None


def test_public_endpoint_respects_surface_visibility(
    client: TestClient,
    make_campaign: Callable[..., AccessCampaign],
) -> None:
    make_campaign(show_on_landing=True, show_on_register=False)

    landing = client.get("/api/v1/campaigns/signup/active", params={"surface": "landing"})
    register = client.get("/api/v1/campaigns/signup/active", params={"surface": "register"})

    assert landing.status_code == register.status_code == 200
    assert landing.json() is not None
    assert register.json() is None


def test_public_endpoint_never_exposes_manual_promotions(
    client: TestClient,
    make_campaign: Callable[..., AccessCampaign],
) -> None:
    make_campaign(
        code="manual-public-campaign",
        kind=AccessCampaignKind.MANUAL_PROMOTION,
        show_on_landing=False,
        show_on_register=False,
    )

    response = client.get("/api/v1/campaigns/signup/active", params={"surface": "landing"})

    assert response.status_code == 200
    assert response.json() is None
