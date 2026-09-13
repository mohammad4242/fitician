class BillingError(Exception):
    code = "BILLING_ERROR"
    status_code = 422

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.code
        super().__init__(self.message)


class BillingOfferUnavailableError(BillingError):
    code = "BILLING_OFFER_UNAVAILABLE"

    def __init__(self, offer_code: str) -> None:
        self.offer_code = offer_code
        super().__init__(f"Offer is not currently available: {offer_code}")


class BillingOfferConfigInvalidError(BillingError):
    code = "BILLING_OFFER_CONFIG_INVALID"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class BillingOfferPriceRequiredError(BillingError):
    code = "BILLING_OFFER_PRICE_REQUIRED"

    def __init__(self, offer_code: str) -> None:
        super().__init__(f"A price is required before activating offer: {offer_code}")


class BillingOrderNotFoundError(BillingError):
    code = "BILLING_ORDER_NOT_FOUND"
    status_code = 404

    def __init__(self) -> None:
        super().__init__("Billing order was not found")


class BillingOrderInvalidStateError(BillingError):
    code = "BILLING_ORDER_INVALID_STATE"
    status_code = 409

    def __init__(self, status: str) -> None:
        self.order_status = status
        super().__init__(f"Billing order cannot be changed from state: {status}")


class BillingIdempotencyConflictError(BillingError):
    code = "BILLING_IDEMPOTENCY_CONFLICT"
    status_code = 409

    def __init__(self) -> None:
        super().__init__("The idempotency key is already used by another checkout")


class BillingProviderRequestError(BillingError):
    code = "BILLING_PROVIDER_REQUEST_INVALID"

    def __init__(self, message: str = "The payment provider request is invalid") -> None:
        super().__init__(message)


class BillingProviderUnavailableError(BillingError):
    code = "BILLING_PROVIDER_UNAVAILABLE"
    status_code = 503

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"Payment provider is unavailable: {provider}")


class BillingPaymentVerificationError(BillingError):
    code = "BILLING_PAYMENT_VERIFICATION_FAILED"

    def __init__(self, message: str = "Payment verification failed") -> None:
        super().__init__(message)
