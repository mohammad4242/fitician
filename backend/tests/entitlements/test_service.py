from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, EntitlementCode, GrantSource
from app.entitlements.exceptions import AccessTermTooShortError
from app.entitlements.service import (
    ensure_requested_term_weeks,
    grant_package,
    has_entitlement,
    list_active_grants,
    max_active_term_weeks_for_entitlement,
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


def test_paid_term_is_persisted_and_invalid_terms_are_rejected(db: Session) -> None:
    user = make_user(db, "term@example.com")

    grant = grant_package(
        db,
        user.id,
        AccessPackageCode.TRAINING,
        source=GrantSource.SUBSCRIPTION,
        term_weeks=6,
    )

    assert grant.term_weeks == 6
    with pytest.raises(ValueError, match="term_weeks"):
        grant_package(
            db,
            user.id,
            AccessPackageCode.TRAINING,
            source=GrantSource.SUBSCRIPTION,
            term_weeks=5,
        )


def test_training_term_limit_uses_active_grants_that_provide_generation(db: Session) -> None:
    user = make_user(db, "term-limit@example.com")
    now = datetime(2026, 9, 12, tzinfo=UTC)
    grant_package(
        db,
        user.id,
        AccessPackageCode.TRAINING,
        source=GrantSource.SUBSCRIPTION,
        starts_at=now,
        ends_at=now + timedelta(weeks=6),
        term_weeks=6,
    )

    assert max_active_term_weeks_for_entitlement(
        db, user.id, EntitlementCode.TRAINING_PLAN_GENERATE, now=now
    ) == 6
    with pytest.raises(AccessTermTooShortError) as error:
        ensure_requested_term_weeks(
            db,
            user.id,
            EntitlementCode.TRAINING_PLAN_GENERATE,
            requested_weeks=8,
            now=now,
        )
    assert error.value.maximum_weeks == 6
