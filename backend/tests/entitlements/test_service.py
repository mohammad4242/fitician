from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, EntitlementCode, GrantSource
from app.entitlements.service import (
    ensure_launch_trial_grant,
    grant_package,
    has_entitlement,
    list_active_grants,
    resolve_access_snapshot,
)


def make_user(db: Session, email: str = "entitlement-service@example.com") -> User:
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.flush()
    return user


def test_user_without_grants_resolves_to_free(db: Session) -> None:
    user = make_user(db)

    snapshot = resolve_access_snapshot(db, user.id)

    assert snapshot.primary_package is AccessPackageCode.FREE
    assert snapshot.active_packages == (AccessPackageCode.FREE,)
    assert snapshot.granted_entitlements == frozenset()
    assert not has_entitlement(db, user.id, EntitlementCode.TRAINING_PLAN_GENERATE)


def test_active_grants_union_and_primary_package_ranking(db: Session) -> None:
    user = make_user(db, "union@example.com")
    now = datetime.now(UTC)
    grant_package(
        db,
        user.id,
        AccessPackageCode.LAUNCH_TRIAL,
        source=GrantSource.LAUNCH_TRIAL,
        starts_at=now,
        ends_at=now + timedelta(days=30),
        idempotency_key="launch_trial:v1",
    )
    grant_package(
        db,
        user.id,
        AccessPackageCode.TRAINING,
        source=GrantSource.SUBSCRIPTION,
        starts_at=now,
    )

    snapshot = resolve_access_snapshot(db, user.id, now=now)

    assert snapshot.primary_package is AccessPackageCode.TRAINING
    assert set(snapshot.active_packages) == {
        AccessPackageCode.FREE,
        AccessPackageCode.TRAINING,
        AccessPackageCode.LAUNCH_TRIAL,
    }
    assert EntitlementCode.TRAINING_PLAN_GENERATE in snapshot.granted_entitlements
    assert EntitlementCode.TRAINING_COACH_REVIEW in snapshot.granted_entitlements
    assert snapshot.trial.active
    assert snapshot.trial.ends_at == now + timedelta(days=30)


def test_expired_and_revoked_grants_do_not_authorize(db: Session) -> None:
    user = make_user(db, "inactive@example.com")
    now = datetime.now(UTC)
    grant_package(
        db,
        user.id,
        AccessPackageCode.TRAINING,
        source=GrantSource.MANUAL,
        starts_at=now - timedelta(days=10),
        ends_at=now - timedelta(seconds=1),
    )
    revoked = grant_package(
        db,
        user.id,
        AccessPackageCode.NUTRITION,
        source=GrantSource.MANUAL,
        starts_at=now - timedelta(days=1),
    )
    revoked.revoked_at = now
    db.flush()

    assert list_active_grants(db, user.id, now=now) == []
    assert resolve_access_snapshot(db, user.id, now=now).primary_package is AccessPackageCode.FREE


def test_trial_grant_is_idempotent_and_lasts_thirty_days(db: Session) -> None:
    user = make_user(db, "trial@example.com")
    now = datetime(2026, 9, 12, tzinfo=UTC)

    first = ensure_launch_trial_grant(db, user.id, now=now)
    second = ensure_launch_trial_grant(db, user.id, now=now + timedelta(days=1))

    assert first.id == second.id
    assert first.package_code is AccessPackageCode.LAUNCH_TRIAL
    assert first.source is GrantSource.LAUNCH_TRIAL
    assert first.starts_at == now
    assert first.ends_at == now + timedelta(days=30)
    assert len(list_active_grants(db, user.id, now=now + timedelta(days=29))) == 1
    assert list_active_grants(db, user.id, now=now + timedelta(days=30, seconds=1)) == []
