from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.auth.models import User
from app.user_activity.models import UserActivityEvent
from app.user_activity.service import UnsafeActivityMetadataError, record_activity


def test_record_activity_filters_metadata_and_deduplicates(db):
    user = User(email="activity@example.com", password_hash="hashed")
    db.add(user)
    db.flush()
    occurred_at = datetime(2026, 10, 7, 10, tzinfo=UTC)

    first = record_activity(
        db,
        user.id,
        "auth.login_succeeded",
        resource_type="auth_session",
        resource_id="session-1",
        metadata={"platform": "web", "auth_method": "password"},
        occurred_at=occurred_at,
        deduplication_key="auth-session:session-1",
    )
    second = record_activity(
        db,
        user.id,
        "auth.login_succeeded",
        resource_type="auth_session",
        resource_id="session-1",
        metadata={"platform": "web", "auth_method": "password"},
        occurred_at=occurred_at,
        deduplication_key="auth-session:session-1",
    )

    assert first.id == second.id
    db.flush()
    assert db.scalar(
        select(UserActivityEvent).where(UserActivityEvent.user_id == user.id)
    ).safe_metadata == {
        "platform": "web",
        "auth_method": "password",
    }


def test_record_activity_rejects_unknown_event_or_metadata(db):
    user = User(email="unsafe@example.com", password_hash="hashed")
    db.add(user)
    db.flush()

    with pytest.raises(UnsafeActivityMetadataError):
        record_activity(db, user.id, "page.view")
    with pytest.raises(UnsafeActivityMetadataError):
        record_activity(db, user.id, "auth.login_succeeded", metadata={"password": "secret"})
    with pytest.raises(UnsafeActivityMetadataError):
        record_activity(db, user.id, "auth.login_succeeded", metadata={"token": "secret"})


def test_record_activity_participates_in_caller_transaction(db):
    user = User(email="rollback@example.com", password_hash="hashed")
    db.add(user)
    db.flush()
    record_activity(db, user.id, "auth.registered", metadata={"platform": "web"})
    db.flush()
    db.rollback()
    assert db.scalar(select(User).where(User.email == "rollback@example.com")) is None
    assert db.scalar(select(UserActivityEvent)) is None


def test_non_deduplicated_events_persist_safe_metadata(db):
    user = User(email="login@example.com", password_hash="hashed")
    db.add(user)
    db.flush()

    event = record_activity(
        db,
        user.id,
        "auth.login_succeeded",
        metadata={"platform": "android", "auth_method": "google"},
    )

    assert event.safe_metadata == {"platform": "android", "auth_method": "google"}


def test_record_activity_rejects_non_finite_metadata(db):
    user = User(email="numeric@example.com", password_hash="hashed")
    db.add(user)
    db.flush()

    with pytest.raises(UnsafeActivityMetadataError):
        record_activity(
            db, user.id, "body.measurement_recorded", metadata={"weight_kg": float("nan")}
        )


def test_shared_profile_completion_and_noop_retry_record_once(db):
    from datetime import date

    from sqlalchemy import func

    from app.profile.models import UserProfile
    from app.profile.schemas import SharedProfileUpsert
    from app.profile.service import upsert_shared_profile

    user = User(email="shared-completion@example.com", password_hash="unused")
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id, product_mode="nutrition"))
    db.flush()
    payload = SharedProfileUpsert(
        display_name="Member",
        birth_date=date(1995, 1, 1),
        sex="male",
        height_cm=180,
        fitness_goal="maintain_weight",
        current_weight_kg=80,
    )
    upsert_shared_profile(db, user.id, payload)
    upsert_shared_profile(db, user.id, payload)
    assert (
        db.scalar(
            select(func.count())
            .select_from(UserActivityEvent)
            .where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.event_type == "profile.completed",
            )
        )
        == 1
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(UserActivityEvent)
            .where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.event_type == "profile.updated",
            )
        )
        == 1
    )
