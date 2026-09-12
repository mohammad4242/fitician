from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, EntitlementCode, GrantSource
from app.entitlements.exceptions import EntitlementQuotaExceededError
from app.entitlements.models import EntitlementUsageEvent
from app.entitlements.service import (
    consume_quota,
    grant_package,
    quota_status,
    require_quota_available,
)


def make_user(db: Session) -> User:
    user = User(email="entitlement-quota@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    grant_package(
        db,
        user.id,
        AccessPackageCode.COMPLETE_CARE,
        source=GrantSource.MANUAL,
        starts_at=datetime.now(UTC),
    )
    return user


def test_same_resource_is_consumed_once(db: Session) -> None:
    user = make_user(db)
    now = datetime.now(UTC)

    assert consume_quota(
        db,
        user.id,
        EntitlementCode.TRAINING_COACH_REVIEW,
        "workout-plan:one",
        now=now,
    )
    assert not consume_quota(
        db,
        user.id,
        EntitlementCode.TRAINING_COACH_REVIEW,
        "workout-plan:one",
        now=now + timedelta(days=1),
    )

    status = quota_status(db, user.id, EntitlementCode.TRAINING_COACH_REVIEW, now=now)
    assert status is not None
    assert status.limit == 1
    assert status.used == 1
    assert status.remaining == 0
    assert status.window_days == 28
    assert status.reset_at == now + timedelta(days=28)
    assert len(db.scalars(select(EntitlementUsageEvent)).all()) == 1


def test_different_resource_is_rejected_until_rolling_window_resets(db: Session) -> None:
    user = make_user(db)
    now = datetime.now(UTC)
    consume_quota(
        db,
        user.id,
        EntitlementCode.BODY_ANALYSIS_RUN,
        "body-analysis-session:one",
        now=now,
    )

    with pytest.raises(EntitlementQuotaExceededError) as error:
        consume_quota(
            db,
            user.id,
            EntitlementCode.BODY_ANALYSIS_RUN,
            "body-analysis-session:two",
            now=now + timedelta(days=1),
        )

    assert error.value.entitlement is EntitlementCode.BODY_ANALYSIS_RUN
    assert error.value.reset_at == now + timedelta(days=7)
    assert error.value.retry_after_seconds == 6 * 24 * 60 * 60
    require_quota_available(
        db,
        user.id,
        EntitlementCode.BODY_ANALYSIS_RUN,
        now=now + timedelta(days=8),
    )


def test_consumption_does_not_commit_the_callers_transaction(db: Session, monkeypatch) -> None:
    user = make_user(db)
    commit_calls = 0
    original_commit = db.commit

    def track_commit() -> None:
        nonlocal commit_calls
        commit_calls += 1
        original_commit()

    monkeypatch.setattr(db, "commit", track_commit)

    consume_quota(
        db,
        user.id,
        EntitlementCode.BODY_ANALYSIS_RUN,
        "body-analysis-session:pending",
    )

    assert commit_calls == 0
