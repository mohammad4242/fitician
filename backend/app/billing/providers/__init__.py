from app.billing.enums import PaymentProviderCode
from app.billing.exceptions import BillingProviderUnavailableError
from app.billing.providers.base import PaymentProvider
from app.billing.providers.fake import FakePaymentProvider
from app.config import Settings


def build_payment_providers(settings: Settings) -> dict[PaymentProviderCode, PaymentProvider]:
    if settings.app_env in {"local", "test"} and settings.billing_default_provider == "fake":
        return {
            PaymentProviderCode.FAKE: FakePaymentProvider(settings.billing_callback_base_url)
        }
    return {}


def resolve_payment_provider(
    providers: dict[PaymentProviderCode, PaymentProvider],
    provider: PaymentProviderCode,
) -> PaymentProvider:
    selected = providers.get(provider)
    if selected is None:
        raise BillingProviderUnavailableError(provider.value)
    return selected


__all__ = [
    "FakePaymentProvider",
    "PaymentProvider",
    "build_payment_providers",
    "resolve_payment_provider",
]
