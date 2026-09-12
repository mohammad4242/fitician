from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.models import EntitlementUsageEvent, UserAccessGrant


def test_entitlement_tables_have_expected_columns_and_constraints() -> None:
    grants = UserAccessGrant.__table__
    usage = EntitlementUsageEvent.__table__

    assert grants.name == "user_access_grants"
    assert usage.name == "entitlement_usage_events"
    assert {
        "id",
        "user_id",
        "package_code",
        "source",
        "starts_at",
        "ends_at",
        "revoked_at",
        "idempotency_key",
        "created_at",
    } == set(grants.columns.keys())
    assert {
        "id",
        "user_id",
        "entitlement_key",
        "resource_key",
        "occurred_at",
        "created_at",
    } == set(usage.columns.keys())
    assert grants.c.idempotency_key.nullable
    assert grants.c.ends_at.nullable
    assert grants.c.revoked_at.nullable


def test_entitlement_foreign_keys_cascade_to_user() -> None:
    for table in (UserAccessGrant.__table__, EntitlementUsageEvent.__table__):
        foreign_keys = list(table.c.user_id.foreign_keys)
        assert len(foreign_keys) == 1
        assert foreign_keys[0].target_fullname == "users.id"
        assert foreign_keys[0].ondelete == "CASCADE"


def test_entitlement_constraints_and_indexes_are_named() -> None:
    grants = UserAccessGrant.__table__
    usage = EntitlementUsageEvent.__table__
    grant_constraints = {constraint.name: constraint for constraint in grants.constraints}
    usage_constraints = {constraint.name: constraint for constraint in usage.constraints}

    assert "uq_user_access_grants_user_idempotency_key" in grant_constraints
    assert "uq_entitlement_usage_events_user_entitlement_resource" in usage_constraints
    assert {
        column.name
        for column in grant_constraints["uq_user_access_grants_user_idempotency_key"].columns
    } == {"user_id", "idempotency_key"}
    assert {
        column.name
        for column in usage_constraints[
            "uq_entitlement_usage_events_user_entitlement_resource"
        ].columns
    } == {"user_id", "entitlement_key", "resource_key"}
    assert any(
        index.name == "ix_entitlement_usage_events_user_entitlement_occurred"
        and [column.name for column in index.columns]
        == ["user_id", "entitlement_key", "occurred_at"]
        for index in usage.indexes
    )


def test_models_are_registered_in_shared_metadata() -> None:
    metadata = UserAccessGrant.metadata
    assert metadata is EntitlementUsageEvent.metadata
    assert "user_access_grants" in metadata.tables
    assert "entitlement_usage_events" in metadata.tables
    assert inspect(UserAccessGrant).local_table is UserAccessGrant.__table__


def test_postgres_constraints_allow_normal_grants_and_prevent_duplicate_semantics(
    db: Session,
) -> None:
    user = User(email="entitlement-model@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    starts_at = datetime.now(UTC)

    db.add_all(
        [
            UserAccessGrant(
                user_id=user.id,
                package_code=AccessPackageCode.TRAINING,
                source=GrantSource.MANUAL,
                starts_at=starts_at,
            ),
            UserAccessGrant(
                user_id=user.id,
                package_code=AccessPackageCode.TRAINING,
                source=GrantSource.SUBSCRIPTION,
                starts_at=starts_at + timedelta(days=30),
            ),
        ]
    )
    db.flush()

    with db.begin_nested():
        db.add(
            UserAccessGrant(
                user_id=user.id,
                package_code=AccessPackageCode.LAUNCH_TRIAL,
                source=GrantSource.LAUNCH_TRIAL,
                starts_at=starts_at,
                idempotency_key="launch_trial:v1",
            )
        )
        db.flush()

    with pytest.raises(IntegrityError, match="uq_user_access_grants_user_idempotency_key"):
        with db.begin_nested():
            db.add(
                UserAccessGrant(
                    user_id=user.id,
                    package_code=AccessPackageCode.LAUNCH_TRIAL,
                    source=GrantSource.LAUNCH_TRIAL,
                    starts_at=starts_at,
                    idempotency_key="launch_trial:v1",
                )
            )
            db.flush()

    db.add(
        EntitlementUsageEvent(
            user_id=user.id,
            entitlement_key="body_analysis.run",
            resource_key="body-analysis-session:one",
            occurred_at=starts_at,
        )
    )
    db.flush()
    with pytest.raises(
        IntegrityError,
        match="uq_entitlement_usage_events_user_entitlement_resource",
    ):
        with db.begin_nested():
            db.add(
                EntitlementUsageEvent(
                    user_id=user.id,
                    entitlement_key="body_analysis.run",
                    resource_key="body-analysis-session:one",
                    occurred_at=starts_at,
                )
            )
            db.flush()

    assert (
        len(db.scalars(select(UserAccessGrant).where(UserAccessGrant.user_id == user.id)).all())
        == 3
    )
