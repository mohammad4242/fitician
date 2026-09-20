import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, event, select, update
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.exceptions import (
    CampaignImmutableError,
    CampaignOverlapError,
    CampaignRedemptionUnavailableError,
    CampaignValidationError,
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
    set_campaign_active,
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
    kind: AccessCampaignKind = AccessCampaignKind.SIGNUP_BONUS,
    package_code: AccessPackageCode = AccessPackageCode.COMPLETE,
    duration_days: int = 28,
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
            package_code=AccessPackageCode.COMPLETE,
            term_weeks=4,
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
    assert first[0].grant.package_code is AccessPackageCode.COMPLETE
    assert first[0].grant.source is GrantSource.PROMOTION
    assert first[0].grant.ends_at == now + timedelta(days=28)
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


def test_campaign_cap_cannot_be_reduced_below_existing_redemptions(db: Session) -> None:
    disable_default_trial(db)
    admin = make_admin(db)
    campaign = create_campaign(
        db,
        campaign_request("cap-update", max_total_redemptions=2),
        actor_user_id=admin.id,
    )
    now = datetime(2026, 9, 20, tzinfo=UTC)
    redeem_campaign(db, campaign.id, make_user(db, "cap-one").id, now=now)
    redeem_campaign(db, campaign.id, make_user(db, "cap-two" ).id, now=now)

    with pytest.raises(CampaignValidationError, match="redemptions"):
        update_campaign(
            db,
            campaign.id,
            AccessCampaignUpdateRequest(max_total_redemptions=1),
            actor_user_id=admin.id,
        )


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
            package_code=AccessPackageCode.COMPLETE,
            term_weeks=8,
            duration_days=56,
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
            duration_days=56,
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
        AccessCampaignUpdateRequest(name="renamed"),
        actor_user_id=admin.id,
    )
    assert updated.name == "renamed"
    deactivated = set_campaign_active(db, campaign.id, False, actor_user_id=admin.id)
    assert deactivated.is_active is False


def test_overlapping_signup_campaign_creates_are_serialized_across_sessions() -> None:
    engine = create_engine(_test_database_url())
    suffix = str(uuid4())
    admin_email = f"campaign-concurrency-admin-{suffix}@example.com"
    codes = (f"concurrent-signup-a-{suffix}", f"concurrent-signup-b-{suffix}")
    lock_statements: list[str] = []
    statement_lock = Lock()

    def record_advisory_lock(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: object,
    ) -> None:
        if "pg_advisory_xact_lock" in statement:
            with statement_lock:
                lock_statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_advisory_lock)
    try:
        with Session(engine) as setup_db:
            admin = make_user(setup_db, suffix)
            admin.email = admin_email
            admin.is_admin = True
            disable_default_trial(setup_db)
            admin_id = admin.id
            setup_db.commit()

        def create_in_session(code: str) -> str:
            with Session(engine) as worker_db:
                try:
                    create_campaign(
                        worker_db,
                        campaign_request(
                            code,
                            available_from=datetime(2026, 11, 1, tzinfo=UTC),
                            available_until=datetime(2026, 11, 30, tzinfo=UTC),
                        ),
                        actor_user_id=admin_id,
                    )
                    worker_db.commit()
                    return "created"
                except CampaignOverlapError:
                    worker_db.rollback()
                    return "overlap"

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(create_in_session, codes))

        assert sorted(outcomes) == ["created", "overlap"]
        assert len(lock_statements) == 2
    finally:
        event.remove(engine, "before_cursor_execute", record_advisory_lock)
        with Session(engine) as cleanup_db:
            cleanup_db.execute(delete(AccessCampaign).where(AccessCampaign.code.in_(codes)))
            cleanup_db.execute(
                update(AccessCampaign)
                .where(AccessCampaign.code == "launch_trial_v1")
                .values(is_active=False)
            )
            cleanup_db.execute(delete(User).where(User.email == admin_email))
            cleanup_db.commit()
        engine.dispose()


def _test_database_url() -> str:
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://fitician:fitician@localhost:5432/fitician_test",
    )
