from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.billing.enums import (
    BillingOfferCode,
    BillingOrderStatus,
    BillingTransactionStatus,
    PaymentProviderCode,
)
from app.entitlements.enums import AccessPackageCode, EntitlementCode


class BillingQuotaPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entitlement: EntitlementCode
    limit: int
    window_days: int


class BillingOfferResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offer_code: BillingOfferCode
    package_code: AccessPackageCode
    duration_weeks: Literal[4, 6, 8]
    price_irr: int | None
    currency: str | None
    is_available: bool
    entitlements: list[EntitlementCode]
    quota_policies: list[BillingQuotaPolicyResponse]


class AdminBillingOfferResponse(BillingOfferResponse):
    is_active: bool
    available_from: datetime | None
    available_until: datetime | None


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offer_code: BillingOfferCode
    provider: PaymentProviderCode
    client_idempotency_key: str = Field(min_length=1, max_length=255)


class BillingOrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    offer_code: BillingOfferCode
    package_code_snapshot: AccessPackageCode
    duration_weeks_snapshot: Literal[4, 6, 8]
    amount_irr_snapshot: int
    currency_snapshot: str
    provider: PaymentProviderCode
    status: BillingOrderStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    paid_at: datetime | None
    refunded_at: datetime | None


class CreateCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: PaymentProviderCode


class VerifyPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: UUID
    provider_reference: str | None = Field(default=None, max_length=255)


class BillingCheckoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: UUID
    transaction_id: UUID
    provider: PaymentProviderCode
    checkout_kind: Literal["redirect", "native"]
    checkout_url: str | None
    provider_product_id: str | None
    provider_reference: str | None


class BillingPaymentResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: UUID
    transaction_id: UUID
    transaction_status: BillingTransactionStatus
    order_status: BillingOrderStatus
    verified: bool
    access_grant_id: UUID | None


class BillingTransactionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    order_id: UUID
    provider: PaymentProviderCode
    provider_reference: str | None
    amount_irr: int
    currency: str
    status: BillingTransactionStatus
    created_at: datetime
    verified_at: datetime | None
    failed_at: datetime | None
    refunded_at: datetime | None


class AdminBillingOrderResponse(BillingOrderResponse):
    user_id: UUID | None
    transactions: list[BillingTransactionResponse]


class UpdateBillingOfferConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price_irr: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    is_active: bool | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None

    @model_validator(mode="after")
    def validate_availability(self) -> "UpdateBillingOfferConfigRequest":
        if (
            self.available_from is not None
            and self.available_until is not None
            and self.available_until < self.available_from
        ):
            raise ValueError("available_until must be after available_from")
        return self
