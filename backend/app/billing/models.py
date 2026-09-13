from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import User  # noqa: F401
from app.billing.enums import (
    BillingOfferCode,
    BillingOrderStatus,
    BillingTransactionStatus,
    PaymentProviderCode,
)
from app.database.base import Base
from app.entitlements.enums import AccessPackageCode


def _enum_values(members: type[PyEnum]) -> list[str]:
    return [member.value for member in members]


def _enum_column(members: type[PyEnum], length: int = 64) -> Enum:
    return Enum(
        members,
        native_enum=False,
        create_constraint=False,
        validate_strings=True,
        values_callable=_enum_values,
        length=length,
    )


class BillingOfferConfig(Base):
    __tablename__ = "billing_offer_configs"
    __table_args__ = (
        CheckConstraint("price_irr >= 0", name="ck_billing_offer_configs_price_nonnegative"),
        CheckConstraint(
            "available_until IS NULL OR available_from IS NULL "
            "OR available_until >= available_from",
            name="ck_billing_offer_configs_availability_order",
        ),
        Index(
            "ix_billing_offer_configs_active_window",
            "is_active",
            "available_from",
            "available_until",
        ),
    )

    offer_code: Mapped[BillingOfferCode] = mapped_column(
        _enum_column(BillingOfferCode), primary_key=True
    )
    price_irr: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(8), nullable=False, default="IRR", server_default="IRR"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BillingProviderProduct(Base):
    __tablename__ = "billing_provider_products"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_product_id",
            name="uq_billing_provider_products_provider_external",
        ),
        UniqueConstraint(
            "provider", "offer_code", name="uq_billing_provider_products_provider_offer"
        ),
        Index("ix_billing_provider_products_offer_active", "offer_code", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    offer_code: Mapped[BillingOfferCode] = mapped_column(
        ForeignKey("billing_offer_configs.offer_code", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[PaymentProviderCode] = mapped_column(
        _enum_column(PaymentProviderCode, length=32), nullable=False
    )
    external_product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BillingOrder(Base):
    __tablename__ = "billing_orders"
    __table_args__ = (
        CheckConstraint(
            "duration_weeks_snapshot IN (4, 6, 8)",
            name="ck_billing_orders_duration_values",
        ),
        CheckConstraint(
            "amount_irr_snapshot >= 0",
            name="ck_billing_orders_amount_nonnegative",
        ),
        UniqueConstraint("user_id", "idempotency_key", name="uq_billing_orders_user_idempotency"),
        Index("ix_billing_orders_user_status", "user_id", "status"),
        Index("ix_billing_orders_user_created", "user_id", "created_at"),
        Index("ix_billing_orders_status_expires", "status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    offer_code: Mapped[BillingOfferCode] = mapped_column(
        _enum_column(BillingOfferCode), nullable=False
    )
    package_code_snapshot: Mapped[AccessPackageCode] = mapped_column(
        _enum_column(AccessPackageCode), nullable=False
    )
    duration_weeks_snapshot: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    amount_irr_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency_snapshot: Mapped[str] = mapped_column(String(8), nullable=False)
    provider: Mapped[PaymentProviderCode] = mapped_column(
        _enum_column(PaymentProviderCode, length=32), nullable=False
    )
    status: Mapped[BillingOrderStatus] = mapped_column(
        _enum_column(BillingOrderStatus, length=32), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_grant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_access_grants.id", ondelete="SET NULL"), nullable=True
    )
    transactions: Mapped[list[BillingTransaction]] = relationship(
        back_populates="order", cascade="all, delete-orphan", passive_deletes=True
    )


class BillingTransaction(Base):
    __tablename__ = "billing_transactions"
    __table_args__ = (
        CheckConstraint("amount_irr >= 0", name="ck_billing_transactions_amount_nonnegative"),
        UniqueConstraint(
            "provider", "provider_reference", name="uq_billing_transactions_provider_reference"
        ),
        Index("ix_billing_transactions_order_status", "order_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("billing_orders.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[PaymentProviderCode] = mapped_column(
        _enum_column(PaymentProviderCode, length=32), nullable=False
    )
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_irr: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[BillingTransactionStatus] = mapped_column(
        _enum_column(BillingTransactionStatus, length=32), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order: Mapped[BillingOrder] = relationship(back_populates="transactions")
