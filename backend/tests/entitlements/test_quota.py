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


def test_distinct_quota_resources_use_a_user_row_lock(db: Session, monkeypatch) -> None:
    user = make_user(db)
    now = datetime.now(UTC)
    user_lock_queries: list[str] = []
    original_scalar = db.scalar

    def capture_user_lock(statement, *args, **kwargs):
        sql = str(statement.compile(dialect=db.get_bind().dialect)).upper()
        if "FROM USERS" in sql:
            user_lock_queries.append(sql)
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(db, "scalar", capture_user_lock)
    assert consume_quota(
        db,
        user.id,
        EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
        "nutrition-plan:first:revision:1",
        now=now,
    )

    with pytest.raises(EntitlementQuotaExceededError):
        consume_quota(
            db,
            user.id,
            EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
            "nutrition-plan:second:revision:1",
            now=now + timedelta(days=1),
        )

    assert len(user_lock_queries) == 2
    assert all("FOR UPDATE" in statement for statement in user_lock_queries)


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


@pytest.mark.parametrize(
    "code",
    [
        EntitlementCode.TRAINING_PLAN_GENERATE,
        EntitlementCode.NUTRITION_PLAN_GENERATE,
    ],
)
def test_full_generation_rolling_boundary_and_idempotency(db: Session, code) -> None:
    user = make_user(db)
    now = datetime.now(UTC)
    assert consume_quota(db, user.id, code, "plan:first", now=now)
    assert not consume_quota(db, user.id, code, "plan:first", now=now)
    with pytest.raises(EntitlementQuotaExceededError):
        require_quota_available(db, user.id, code, now=now + timedelta(days=7, microseconds=-1))
    assert consume_quota(db, user.id, code, "plan:second", now=now + timedelta(days=7))


def test_generation_quotas_are_independent_and_admin_exemption_is_narrow(db: Session) -> None:
    user = make_user(db)
    for code in (EntitlementCode.TRAINING_PLAN_GENERATE, EntitlementCode.NUTRITION_PLAN_GENERATE):
        assert consume_quota(db, user.id, code, "plan:first")
    user.is_admin = True
    db.flush()
    for code in (EntitlementCode.TRAINING_PLAN_GENERATE, EntitlementCode.NUTRITION_PLAN_GENERATE):
        assert quota_status(db, user.id, code) is None
        require_quota_available(db, user.id, code)
        assert not consume_quota(db, user.id, code, "plan:admin")
    consume_quota(db, user.id, EntitlementCode.BODY_ANALYSIS_RUN, "analysis:first")
    with pytest.raises(EntitlementQuotaExceededError):
        require_quota_available(db, user.id, EntitlementCode.BODY_ANALYSIS_RUN)


@pytest.mark.parametrize("same_resource", [False, True])
def test_concurrent_generation_consumption_is_serialized(db: Session, same_resource) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import create_engine, delete

    from tests.conftest import TEST_DATABASE_URL

    engine = create_engine(TEST_DATABASE_URL)
    with Session(engine) as setup:
        user = User(email="concurrent-generation@example.com", password_hash="hash")
        setup.add(user)
        setup.flush()
        grant_package(setup, user.id, AccessPackageCode.TRAINING)
        user_id = user.id
        setup.commit()
    barrier = Barrier(2)

    def generate(index):
        with Session(engine) as session:
            require_quota_available(session, user_id, EntitlementCode.TRAINING_PLAN_GENERATE)
            barrier.wait(timeout=10)
            try:
                consumed = consume_quota(
                    session,
                    user_id,
                    EntitlementCode.TRAINING_PLAN_GENERATE,
                    f"workout-plan:{0 if same_resource else index}",
                )
                session.commit()
                return "consumed" if consumed else "duplicate"
            except EntitlementQuotaExceededError:
                session.rollback()
                return "blocked"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(generate, (1, 2)))
        assert sorted(results) == sorted(["consumed", "duplicate" if same_resource else "blocked"])
        with Session(engine) as session:
            assert (
                len(
                    session.scalars(
                        select(EntitlementUsageEvent).where(
                            EntitlementUsageEvent.user_id == user_id
                        )
                    ).all()
                )
                == 1
            )
    finally:
        with Session(engine) as cleanup:
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()
        engine.dispose()
