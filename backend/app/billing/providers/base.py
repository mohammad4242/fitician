from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from app.billing.enums import BillingOfferCode, PaymentProviderCode

CheckoutKind = Literal["redirect", "native"]
PaymentOutcomeStatus = Literal["verified", "failed", "refunded"]


class PaymentProviderError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ProviderCheckoutRequest:
    order_id: UUID
    transaction_id: UUID
    offer_code: BillingOfferCode
    amount_irr: int
    currency: str
    external_product_id: str | None
    callback_base_url: str | None


@dataclass(frozen=True, slots=True)
class ProviderCheckoutResult:
    checkout_kind: CheckoutKind
    checkout_url: str | None
    provider_product_id: str | None
    provider_reference: str


@dataclass(frozen=True, slots=True)
class ProviderVerificationRequest:
    order_id: UUID
    transaction_id: UUID
    provider_reference: str
    amount_irr: int
    currency: str


@dataclass(frozen=True, slots=True)
class ProviderPaymentResult:
    status: PaymentOutcomeStatus
    provider_reference: str


class PaymentProvider(Protocol):
    code: PaymentProviderCode

    def create_checkout(self, request: ProviderCheckoutRequest) -> ProviderCheckoutResult:
        ...

    def verify_payment(self, request: ProviderVerificationRequest) -> ProviderPaymentResult:
        ...

    def verify_refund(self, request: ProviderVerificationRequest) -> ProviderPaymentResult:
        ...
