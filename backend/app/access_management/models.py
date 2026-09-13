from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.access_management.enums import AccessCampaignKind
from app.auth.models import User  # noqa: F401
from app.database.base import Base
from app.entitlements.enums import AccessPackageCode


def _enum_values(members: type[PyEnum]) -> list[str]:
    return [member.value for member in members]


class AccessCampaign(Base):
    __tablename__ = "access_campaigns"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(code)) BETWEEN 1 AND 128",
            name="ck_access_campaigns_code_length",
        ),
        CheckConstraint(
            "kind IN ('signup_trial', 'manual_promotion')",
            name="ck_access_campaigns_kind_values",
        ),
        CheckConstraint(
            "package_code <> 'free'",
            name="ck_access_campaigns_package_not_free",
        ),
        CheckConstraint(
            "duration_days BETWEEN 1 AND 3650",
            name="ck_access_campaigns_duration_days",
        ),
        CheckConstraint(
            "term_weeks IS NULL OR term_weeks IN (4, 6, 8)",
            name="ck_access_campaigns_term_weeks_values",
        ),
        CheckConstraint(
            "package_code <> 'launch_trial' OR term_weeks = 4",
            name="ck_access_campaigns_launch_trial_term",
        ),
        CheckConstraint(
            "package_code NOT IN ('training', 'training_coach', 'complete', 'complete_care') "
            "OR term_weeks IS NOT NULL",
            name="ck_access_campaigns_training_term",
        ),
        CheckConstraint(
            "available_until IS NULL OR available_from IS NULL "
            "OR available_until >= available_from",
            name="ck_access_campaigns_availability_order",
        ),
        CheckConstraint(
            "max_total_redemptions IS NULL OR max_total_redemptions > 0",
            name="ck_access_campaigns_max_redemptions_positive",
        ),
        Index(
            "ix_access_campaigns_kind_active_window",
            "kind",
            "is_active",
            "available_from",
            "available_until",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[AccessCampaignKind] = mapped_column(
        Enum(
            AccessCampaignKind,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=_enum_values,
            length=32,
        ),
        nullable=False,
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
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    term_weeks: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    available_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    available_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    max_total_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AccessCampaignRedemption(Base):
    __tablename__ = "access_campaign_redemptions"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "user_id",
            name="uq_access_campaign_redemptions_campaign_user",
        ),
        Index(
            "ix_access_campaign_redemptions_campaign_id",
            "campaign_id",
        ),
        Index(
            "ix_access_campaign_redemptions_user_id",
            "user_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("access_campaigns.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    access_grant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_access_grants.id", ondelete="SET NULL"), nullable=True
    )
    package_code_snapshot: Mapped[AccessPackageCode] = mapped_column(
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
    duration_days_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    term_weeks_snapshot: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
