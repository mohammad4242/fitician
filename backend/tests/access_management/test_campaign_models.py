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


def test_campaign_schema_rejects_free_and_invalid_benefit_semantics() -> None:
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
            kind=AccessCampaignKind.SIGNUP_TRIAL,
            package_code=AccessPackageCode.TRAINING,
            duration_days=3651,
            term_weeks=4,
        )

    with pytest.raises(ValidationError):
        AccessCampaignCreateRequest(
            code="bad-launch",
            name="Bad launch",
            kind=AccessCampaignKind.SIGNUP_TRIAL,
            package_code=AccessPackageCode.LAUNCH_TRIAL,
            duration_days=14,
            term_weeks=6,
        )


def test_campaign_schema_requires_training_term_and_valid_window() -> None:
    with pytest.raises(ValidationError):
        AccessCampaignCreateRequest(
            code="missing-term",
            name="Missing term",
            kind=AccessCampaignKind.SIGNUP_TRIAL,
            package_code=AccessPackageCode.TRAINING,
            duration_days=14,
        )

    with pytest.raises(ValidationError):
        AccessCampaignCreateRequest(
            code="bad-window",
            name="Bad window",
            kind=AccessCampaignKind.SIGNUP_TRIAL,
            package_code=AccessPackageCode.COMPLETE,
            duration_days=14,
            term_weeks=8,
            available_from=datetime(2026, 10, 2, tzinfo=UTC),
            available_until=datetime(2026, 10, 1, tzinfo=UTC),
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
        duration_days=30,
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
