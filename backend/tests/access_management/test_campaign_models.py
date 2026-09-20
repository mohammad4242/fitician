from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.models import AccessCampaign, AccessCampaignRedemption
from app.access_management.schemas import AccessCampaignCreateRequest
from app.auth.models import User
from app.entitlements.enums import AccessPackageCode


def test_campaign_schema_rejects_unsafe_packages_and_accepts_generic_signup_bonuses() -> None:
    with pytest.raises(ValidationError):
        AccessCampaignCreateRequest(
            code="free-promo",
            name="Free",
            kind=AccessCampaignKind.MANUAL_PROMOTION,
            package_code=AccessPackageCode.FREE,
            duration_days=14,
        )

    with pytest.raises(ValidationError):
        AccessCampaignCreateRequest(
            code="too-long",
            name="Too long",
            kind=AccessCampaignKind.SIGNUP_BONUS,
            package_code=AccessPackageCode.LAUNCH_TRIAL,
            duration_days=3651,
            term_weeks=4,
        )

    with pytest.raises(ValidationError, match="launch_trial"):
        AccessCampaignCreateRequest(
            code="signup-package",
            name="Signup package",
            kind=AccessCampaignKind.SIGNUP_BONUS,
            package_code=AccessPackageCode.LAUNCH_TRIAL,
            duration_days=28,
            term_weeks=4,
        )

    with pytest.raises(ValidationError, match="launch_trial"):
        AccessCampaignCreateRequest(
            code="manual-trial",
            name="Manual trial",
            kind=AccessCampaignKind.SIGNUP_BONUS,
            package_code=AccessPackageCode.LAUNCH_TRIAL,
            duration_days=42,
            term_weeks=6,
        )

    for term_weeks, duration_days in ((4, 28), (6, 42), (8, 56)):
        campaign = AccessCampaignCreateRequest(
            code=f"signup-{term_weeks}",
            name="Signup bonus",
            kind=AccessCampaignKind.SIGNUP_BONUS,
            package_code=AccessPackageCode.COMPLETE,
            duration_days=duration_days,
            term_weeks=term_weeks,
        )
        assert campaign.term_weeks == term_weeks

    with pytest.raises(ValidationError, match="duration_days"):
        AccessCampaignCreateRequest(
            code="short-training",
            name="Short training",
            kind=AccessCampaignKind.SIGNUP_BONUS,
            package_code=AccessPackageCode.COMPLETE,
            duration_days=30,
            term_weeks=6,
        )


def test_campaign_schema_requires_training_term_and_valid_window() -> None:
    with pytest.raises(ValidationError):
        AccessCampaignCreateRequest(
            code="missing-term",
            name="Missing term",
            kind=AccessCampaignKind.MANUAL_PROMOTION,
            package_code=AccessPackageCode.TRAINING,
            duration_days=28,
        )

    with pytest.raises(ValidationError):
        AccessCampaignCreateRequest(
            code="bad-window",
            name="Bad window",
            kind=AccessCampaignKind.MANUAL_PROMOTION,
            package_code=AccessPackageCode.COMPLETE,
            duration_days=56,
            term_weeks=8,
            available_from=datetime(2026, 10, 2, tzinfo=UTC),
            available_until=datetime(2026, 10, 1, tzinfo=UTC),
        )


def test_campaign_schema_requires_complete_bilingual_public_copy() -> None:
    common = {
        "code": "public-bonus",
        "name": "Public bonus",
        "kind": AccessCampaignKind.SIGNUP_BONUS,
        "package_code": AccessPackageCode.COMPLETE,
        "duration_days": 42,
        "term_weeks": 6,
        "show_on_landing": True,
    }
    with pytest.raises(ValidationError, match="public_title_fa"):
        AccessCampaignCreateRequest(**common)

    campaign = AccessCampaignCreateRequest(
        **common,
        public_title_fa=" عنوان فارسی ",
        public_title_en=" English title ",
        public_message_fa=" پیام فارسی ",
        public_message_en=" English message ",
        public_cta_fa=" شروع ",
        public_cta_en=" Start ",
        public_badge_fa=" ",
    )
    assert campaign.public_title_fa == "عنوان فارسی"
    assert campaign.public_badge_fa is None

    with pytest.raises(ValidationError, match="manual_promotion"):
        AccessCampaignCreateRequest(
            code="manual-public",
            name="Manual public",
            kind=AccessCampaignKind.MANUAL_PROMOTION,
            package_code=AccessPackageCode.COMPLETE,
            duration_days=42,
            term_weeks=6,
            show_on_register=True,
        )


def test_campaign_redemption_has_database_uniqueness_per_campaign_user(db: Session) -> None:
    user = User(email=f"campaign-{uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    campaign = AccessCampaign(
        code=f"campaign-{uuid4()}",
        name="Campaign",
        kind=AccessCampaignKind.MANUAL_PROMOTION,
        package_code=AccessPackageCode.COMPLETE,
        duration_days=56,
        term_weeks=8,
        is_active=True,
    )
    db.add(campaign)
    db.flush()

    db.add(
        AccessCampaignRedemption(
            campaign_id=campaign.id,
            user_id=user.id,
            package_code_snapshot=campaign.package_code,
            duration_days_snapshot=campaign.duration_days,
            term_weeks_snapshot=campaign.term_weeks,
            redeemed_at=datetime.now(UTC),
        )
    )
    db.flush()
    db.add(
        AccessCampaignRedemption(
            campaign_id=campaign.id,
            user_id=user.id,
            package_code_snapshot=campaign.package_code,
            duration_days_snapshot=campaign.duration_days,
            term_weeks_snapshot=campaign.term_weeks,
            redeemed_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_campaign_table_declares_stable_kind_and_training_term_constraints() -> None:
    constraint_names = {
        constraint.name for constraint in AccessCampaign.__table__.constraints
    }

    assert "ck_access_campaigns_kind_values" in constraint_names
    assert "ck_access_campaigns_training_term" in constraint_names
    assert "ck_access_campaigns_training_duration" in constraint_names
    assert "ck_access_campaigns_manual_promotion_private" in constraint_names
    assert "ck_access_campaigns_signup_trial_package" not in constraint_names
