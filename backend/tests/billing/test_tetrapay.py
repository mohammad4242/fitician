from uuid import uuid4

import httpx
import pytest

from app.billing.enums import BillingOfferCode
from app.billing.providers.base import (
    PaymentProviderError,
    ProviderCheckoutRequest,
    ProviderVerificationRequest,
)
from app.billing.providers.tetrapay import TetraPayProvider, verify_webhook
from app.config import Settings

TOKEN = "q9Xk2VbR7tLmN4pA8sWcYg"


def settings(**kwargs):
    return Settings(
        _env_file=None,
        app_env="test",
        tetrapay_enabled=True,
        tetrapay_api_key="test-key",
        billing_default_provider="tetrapay",
        **kwargs,
    )


def invoice(request, **changes):
    return dict(
        token=TOKEN,
        status="paid",
        order_id=str(request.transaction_id),
        amount="1000000",
        payable_amount="1005000",
        received_amount="1005000",
        net_amount="995000",
        fee_total="10000",
        fee_payer="5000",
        fee_merchant="5000",
        method="online",
        paid_at="2026-11-23T10:00:00Z",
        verified_before=False,
        **changes,
    )


def verification():
    return ProviderVerificationRequest(uuid4(), uuid4(), TOKEN, 1000000, "IRR")


def provider(handler):
    return TetraPayProvider(settings(), transport=httpx.MockTransport(handler))


def test_create_uses_v1_auth_integer_rials_and_stable_transaction():
    import json

    request = ProviderCheckoutRequest(
        uuid4(), uuid4(), BillingOfferCode.TRAINING_4W, 1000000, "IRR", None, None
    )

    def handler(http_request):
        assert str(http_request.url) == "https://api.sandbox.tetra98.com/api/v1/payments"
        assert http_request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(http_request.content)
        assert body["amount"] == "1000000"
        assert body["order_id"] == str(request.transaction_id)
        assert body["allow_partial"] is False
        assert "webhook_url" not in body
        return httpx.Response(
            201,
            json={
                "token": TOKEN,
                "payment_url": f"https://sandbox.tetra98.com/pay/{TOKEN}",
                "bot_payment_url": "https://t.me/Tetra98_Bot",
                "amount": "1000000",
            },
        )

    result = provider(handler).create_checkout(request)
    assert result.provider_reference == TOKEN


@pytest.mark.parametrize("method", ["online", "card"])
def test_full_payment_verified(method):
    request = verification()
    body = invoice(request)
    body["method"] = method
    assert (
        provider(lambda _: httpx.Response(200, json=body)).verify_payment(request).status
        == "verified"
    )


@pytest.mark.parametrize("status", ["created", "pending", "expired"])
def test_unpaid_states(status):
    request = verification()
    body = invoice(request)
    body.update(status=status, received_amount=None, method=None, paid_at=None)
    assert provider(lambda _: httpx.Response(200, json=body)).verify_payment(request).status == (
        "expired" if status == "expired" else "pending"
    )


@pytest.mark.parametrize(
    "change",
    [
        {"token": "other"},
        {"order_id": "other"},
        {"amount": "1000001"},
        {"received_amount": "500000", "partial": True},
        {"received_amount": "1000000"},
        {"amount": 1000000.0},
        {"payable_amount": "NaN"},
        {"status": "surprise"},
        {"fee_payer": "0"},
        {"sandbox": False},
    ],
)
def test_rejects_mismatches_and_malformed(change):
    request = verification()
    body = invoice(request)
    body.update(change)
    with pytest.raises(PaymentProviderError):
        provider(lambda _: httpx.Response(200, json=body)).verify_payment(request)


@pytest.mark.parametrize("status", [401, 403, 409, 422, 429, 500])
def test_sanitized_errors(status):
    with pytest.raises(PaymentProviderError, match="TetraPay") as error:
        provider(
            lambda _: httpx.Response(
                status, json={"error": {"message": "private"}}, headers={"Retry-After": "42"}
            )
        ).verify_payment(verification())
    assert "private" not in str(error.value)
    if status == 429:
        assert error.value.retry_after == 42


def test_timeout_and_bad_json_and_refund():
    for handler in [
        lambda _: httpx.Response(200, text="invalid"),
        lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("private", request=req)),
    ]:
        with pytest.raises(PaymentProviderError):
            provider(handler).verify_payment(verification())
    with pytest.raises(PaymentProviderError):
        provider(lambda _: httpx.Response(200)).verify_refund(verification())


def test_signature_raw_bytes_timestamp_and_missing_key():
    import hashlib
    import hmac

    raw = b'{ "event": "payment.paid" }'
    digest = hmac.new(b"whsec_test", b"1000." + raw, hashlib.sha256).hexdigest()
    signature = f"t=1000,v1={digest}"
    verify_webhook(raw, signature, "whsec_test", now=1000)
    for body, header, secret, now in [
        (raw + b" ", signature, "whsec_test", 1000),
        (raw, signature, "", 1000),
        (raw, signature, "whsec_test", 1301),
        (raw, "bad", "whsec_test", 1000),
    ]:
        with pytest.raises(PaymentProviderError):
            verify_webhook(body, header, secret, now=now)


def test_http_logs_and_configuration_errors_do_not_expose_payment_secrets(caplog):
    import logging

    request = verification()
    caplog.set_level(logging.INFO, logger="httpx")
    provider(lambda _: httpx.Response(200, json=invoice(request))).verify_payment(request)
    assert TOKEN not in caplog.text
    assert "test-key" not in caplog.text
    with pytest.raises(ValueError) as error:
        Settings(
            _env_file=None,
            tetrapay_enabled=True,
            tetrapay_api_key="private-value",
            tetrapay_base_url="https://untrusted.example",
        )
    assert "private-value" not in str(error.value)


def test_rate_limit_body_fallback_and_empty_verify_body():
    def handler(request):
        assert request.content == b""
        return httpx.Response(429, json={"error": {"code": "RATE_LIMITED", "retryAfter": 120}})

    with pytest.raises(PaymentProviderError) as error:
        provider(handler).verify_payment(verification())
    assert error.value.retry_after == 120
