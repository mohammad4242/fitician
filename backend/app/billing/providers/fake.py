from __future__ import annotations

from app.billing.enums import PaymentProviderCode
from app.billing.providers.base import (
    PaymentOutcomeStatus,
    PaymentProviderError,
    ProviderCheckoutRequest,
    ProviderCheckoutResult,
    ProviderPaymentResult,
    ProviderVerificationRequest,
)


class FakePaymentProvider:
    """Deterministic local/test provider; never use this as a production adapter."""

    code = PaymentProviderCode.FAKE

    def __init__(self, callback_base_url: str | None = None) -> None:
        self.callback_base_url = callback_base_url
        self._outcomes: dict[str, PaymentOutcomeStatus] = {}

    def set_outcome(
        self,
        transaction_id: object,
        outcome: PaymentOutcomeStatus,
    ) -> None:
        self._outcomes[str(transaction_id)] = outcome

    def create_checkout(self, request: ProviderCheckoutRequest) -> ProviderCheckoutResult:
        provider_reference = f"fake-payment:{request.transaction_id}"
        callback_base = request.callback_base_url or self.callback_base_url
        if callback_base:
            checkout_url = (
                f"{callback_base.rstrip('/')}/billing/checkout-result"
                f"?order_id={request.order_id}&transaction_id={request.transaction_id}"
                f"&provider_reference={provider_reference}"
            )
        else:
            checkout_url = (
                "/billing/checkout-result"
                f"?order_id={request.order_id}&transaction_id={request.transaction_id}"
                f"&provider_reference={provider_reference}"
            )
        return ProviderCheckoutResult(
            checkout_kind="redirect",
            checkout_url=checkout_url,
            provider_product_id=None,
            provider_reference=provider_reference,
        )

    def _verify(
        self,
        request: ProviderVerificationRequest,
        *,
        refund: bool,
    ) -> ProviderPaymentResult:
        expected_reference = f"fake-payment:{request.transaction_id}"
        if request.provider_reference != expected_reference:
            raise PaymentProviderError("Fake payment reference does not match the transaction")
        outcome = self._outcomes.get(str(request.transaction_id), "verified")
        if refund and outcome != "refunded":
            outcome = "failed"
        return ProviderPaymentResult(status=outcome, provider_reference=expected_reference)

    def verify_payment(self, request: ProviderVerificationRequest) -> ProviderPaymentResult:
        return self._verify(request, refund=False)

    def verify_refund(self, request: ProviderVerificationRequest) -> ProviderPaymentResult:
        return self._verify(request, refund=True)
