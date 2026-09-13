from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.models import User  # noqa: F401
from app.database.base import Base
from app.entitlements.enums import AccessPackageCode, GrantSource


def _enum_values(members: type[PyEnum]) -> list[str]:
    return [member.value for member in members]


class UserAccessGrant(Base):
    """A persisted package grant owned by one member."""

    __tablename__ = "user_access_grants"
    __table_args__ = (
        CheckConstraint(
            "term_weeks IS NULL OR term_weeks IN (4, 6, 8)",
            name="ck_user_access_grants_term_weeks_values",
        ),
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_user_access_grants_user_idempotency_key",
        ),
        Index(
            "ix_user_access_grants_user_id_starts_at_ends_at",
            "user_id",
            "starts_at",
            "ends_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    package_code: Mapped[AccessPackageCode] = mapped_column(
        Enum(
            AccessPackageCode,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=_enum_values,
            length=64,
        ),
        nullable=False,
    )
    source: Mapped[GrantSource] = mapped_column(
        Enum(
            GrantSource,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=_enum_values,
            length=64,
        ),
        nullable=False,
    )
    term_weeks: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EntitlementUsageEvent(Base):
    """An idempotent consumption of a quota-backed entitlement resource."""

    __tablename__ = "entitlement_usage_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "entitlement_key",
            "resource_key",
            name="uq_entitlement_usage_events_user_entitlement_resource",
        ),
        Index(
            "ix_entitlement_usage_events_user_entitlement_occurred",
            "user_id",
            "entitlement_key",
            "occurred_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entitlement_key: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_key: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
