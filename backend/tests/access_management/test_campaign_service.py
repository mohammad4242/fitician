from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.exceptions import (
    CampaignImmutableError,
    CampaignOverlapError,
    CampaignRedemptionUnavailableError,
)
from app.access_management.models import AccessCampaign, AccessCampaignRedemption
from app.access_management.schemas import (
    AccessCampaignCreateRequest,
    AccessCampaignUpdateRequest,
)
from app.access_management.service import (
    create_campaign,
    provision_signup_campaigns,
    redeem_campaign,
    update_campaign,
)
from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.models import UserAccessGrant


def make_user(db: Session, suffix: str | None = None) -> User:
    user = User(email=f"campaign-user-{suffix or uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    return user


def make_admin(db: Session) -> User:
    admin = make_user(db, "admin")
    admin.is_admin = True
    db.flush()
    return admin


def disable_default_trial(db: Session) -> None:
    db.execute(
        update(AccessCampaign)
        .where(AccessCampaign.code == "launch_trial_v1")
        .values(is_active=False)
    )


def campaign_request(
    code: str,
    *,
    kind: AccessCampaignKind = AccessCampaignKind.SIGNUP_TRIAL,
    package_code: AccessPackageCode = AccessPackageCode.TRAINING,
    duration_days: int = 14,
    term_weeks: int | None = 4,
    active: bool = True,
    available_from: datetime | None = None,
    available_until: datetime | None = None,
    max_total_redemptions: int | None = None,
) -> AccessCampaignCreateRequest:
    return AccessCampaignCreateRequest(
        code=code,
        name=code,
        kind=kind,
        package_code=package_code,
        duration_days=duration_days,
        term_weeks=term_weeks,
        is_active=active,
        available_from=available_from,
        available_until=available_until,
        max_total_redemptions=max_total_redemptions,
    )


def test_active_signup_campaign_provisions_one_package_and_is_idempotent(db: Session) -> None:
    disable_default_trial(db)
    admin = make_admin(db)
    campaign = create_campaign(
        db,
        campaign_request(
            "signup-service",
            package_code=AccessPackageCode.COMPLETE_CARE,
            term_weeks=8,
        ),
        actor_user_id=admin.id,
    )
    user = make_user(db)
    now = datetime(2026, 9, 20, tzinfo=UTC)

    first = provision_signup_campaigns(db, user.id, now=now)
    second = provision_signup_campaigns(db, user.id, now=now + timedelta(days=1))

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].grant.id == second[0].grant.id
    assert first[0].grant.package_code is AccessPackageCode.COMPLETE_CARE
    assert first[0].grant.source is GrantSource.PROMOTION
    assert first[0].grant.ends_at == now + timedelta(days=14)
    assert db.scalar(
        select(AccessCampaignRedemption).where(
            AccessCampaignRedemption.campaign_id == campaign.id,
            AccessCampaignRedemption.user_id == user.id,
        )
    ) is not None
    assert (
        len(db.scalars(select(UserAccessGrant).where(UserAccessGrant.user_id == user.id)).all())
        == 1
    )


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        (datetime(2026, 9, 9, tzinfo=UTC), False),
        (datetime(2026, 9, 20, tzinfo=UTC), True),
        (datetime(2026, 10, 2, tzinfo=UTC), False),
    ],
)
def test_signup_campaign_obeys_eligibility_window(
    db: Session,
    when: datetime,
    expected: bool,
) -> None:
    disable_default_trial(db)
    create_campaign(
        db,
        campaign_request(
            f"window-{when.day}",
            available_from=datetime(2026, 9, 10, tzinfo=UTC),
            available_until=datetime(2026, 10, 1, tzinfo=UTC),
        ),
        actor_user_id=make_admin(db).id,
    )
    user = make_user(db)

    result = provision_signup_campaigns(db, user.id, now=when)

    assert bool(result) is expected


def test_disabled_signup_campaign_does_not_provision_access(db: Session) -> None:
    disable_default_trial(db)
    create_campaign(
        db,
        campaign_request("disabled", active=False),
        actor_user_id=make_admin(db).id,
    )
    user = make_user(db)

    assert provision_signup_campaigns(db, user.id, now=datetime.now(UTC)) == []


def test_signup_campaign_cap_is_enforced(db: Session) -> None:
    disable_default_trial(db)
    admin = make_admin(db)
    campaign = create_campaign(
        db,
        campaign_request("capped", max_total_redemptions=1),
        actor_user_id=admin.id,
    )
    first_user = make_user(db, "first")
    second_user = make_user(db, "second")
    now = datetime(2026, 9, 20, tzinfo=UTC)

    assert len(provision_signup_campaigns(db, first_user.id, now=now)) == 1
    with pytest.raises(CampaignRedemptionUnavailableError):
        redeem_campaign(db, campaign.id, second_user.id, now=now)


def test_active_signup_campaigns_cannot_overlap_but_promotions_can(db: Session) -> None:
    disable_default_trial(db)
    admin = make_admin(db)
    first = create_campaign(
        db,
        campaign_request(
            "first-overlap",
            available_from=datetime(2026, 9, 10, tzinfo=UTC),
            available_until=datetime(2026, 9, 20, tzinfo=UTC),
        ),
        actor_user_id=admin.id,
    )
    with pytest.raises(CampaignOverlapError):
        create_campaign(
            db,
            campaign_request(
                "second-overlap",
                available_from=datetime(2026, 9, 20, tzinfo=UTC),
                available_until=datetime(2026, 9, 30, tzinfo=UTC),
            ),
            actor_user_id=admin.id,
        )

    promotion = create_campaign(
        db,
        campaign_request(
            "manual-overlap",
            kind=AccessCampaignKind.MANUAL_PROMOTION,
            active=True,
            available_from=first.available_from,
            available_until=first.available_until,
        ),
        actor_user_id=admin.id,
    )
    assert promotion.kind is AccessCampaignKind.MANUAL_PROMOTION


def test_manual_promotion_does_not_auto_apply_and_can_be_redeemed_once(db: Session) -> None:
    disable_default_trial(db)
    admin = make_admin(db)
    campaign = create_campaign(
        db,
        campaign_request(
            "manual-only",
            kind=AccessCampaignKind.MANUAL_PROMOTION,
            package_code=AccessPackageCode.COMPLETE,
            term_weeks=8,
        ),
        actor_user_id=admin.id,
    )
    user = make_user(db)
    now = datetime(2026, 9, 20, tzinfo=UTC)

    assert provision_signup_campaigns(db, user.id, now=now) == []
    first = redeem_campaign(
        db,
        campaign.id,
        user.id,
        now=now,
        actor_user_id=admin.id,
        reason="beta tester",
        manual=True,
    )
    second = redeem_campaign(
        db,
        campaign.id,
        user.id,
        now=now + timedelta(days=1),
        actor_user_id=admin.id,
        reason="retry",
        manual=True,
    )

    assert first.created is True
    assert second.created is False
    assert first.grant.id == second.grant.id


def test_redeemed_campaign_semantics_are_immutable(db: Session) -> None:
    disable_default_trial(db)
    admin = make_admin(db)
    campaign = create_campaign(
        db,
        campaign_request("immutable"),
        actor_user_id=admin.id,
    )
    user = make_user(db)
    redeem_campaign(db, campaign.id, user.id, now=datetime(2026, 9, 20, tzinfo=UTC))

    with pytest.raises(CampaignImmutableError):
        update_campaign(
            db,
            campaign.id,
            AccessCampaignUpdateRequest(duration_days=30),
            actor_user_id=admin.id,
        )

    updated = update_campaign(
        db,
        campaign.id,
        AccessCampaignUpdateRequest(name="renamed", is_active=False),
        actor_user_id=admin.id,
    )
    assert updated.name == "renamed"
    assert updated.is_active is False
