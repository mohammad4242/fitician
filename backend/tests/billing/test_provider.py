import pytest

from app.billing.enums import PaymentProviderCode
from app.billing.providers import build_payment_providers
from app.billing.providers.fake import FakePaymentProvider
from app.config import Settings


def test_fake_provider_is_available_only_for_local_and_test() -> None:
    local = Settings(app_env="local")
    test = Settings(app_env="test")

    assert set(build_payment_providers(local)) == {PaymentProviderCode.FAKE}
    assert set(build_payment_providers(test)) == {PaymentProviderCode.FAKE}


def test_production_rejects_fake_provider_configuration() -> None:
    with pytest.raises(ValueError, match="fake billing provider"):
        Settings(app_env="production", billing_default_provider="fake")
    with pytest.raises(ValueError, match="fake billing provider"):
        Settings(app_env="production", billing_fake_provider_enabled=True)


def test_fake_provider_is_not_a_test_only_mock() -> None:
    provider = FakePaymentProvider()
    assert provider.code is PaymentProviderCode.FAKE
    assert hasattr(provider, "create_checkout")
    assert hasattr(provider, "verify_payment")
    assert hasattr(provider, "verify_refund")
