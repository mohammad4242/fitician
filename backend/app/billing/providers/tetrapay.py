"""TetraPay API v1. See the pinned official OpenAPI snapshot in docs/integrations."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any, Literal, NoReturn
from urllib.parse import quote, urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

from app.billing.enums import PaymentProviderCode
from app.billing.providers.base import (
    PaymentProviderError,
    ProviderCheckoutRequest,
    ProviderCheckoutResult,
    ProviderPaymentResult,
    ProviderVerificationRequest,
)
from app.config import Settings

Money = str


class Payment(BaseModel):
    model_config = ConfigDict(strict=True)
    token: str = Field(
        min_length=1,
        max_length=64,
    )
    order_id: str
    status: Literal["created", "pending", "paid", "expired"]
    amount: Money = Field(pattern=r"^[0-9]{1,18}$")
    payable_amount: Money = Field(pattern=r"^[0-9]{1,18}$")
    received_amount: Money | None = Field(pattern=r"^[0-9]{1,18}$")
    net_amount: Money = Field(pattern=r"^[0-9]{1,18}$")
    fee_total: Money = Field(pattern=r"^[0-9]{1,18}$")
    fee_payer: Money = Field(pattern=r"^[0-9]{1,18}$")
    fee_merchant: Money = Field(pattern=r"^[0-9]{1,18}$")
    method: Literal["online", "card"] | None
    paid_at: str | None
    partial: StrictBool = False
    sandbox: StrictBool | None = None


def verify_webhook(
    raw: bytes,
    signature: str,
    secret: str,
    *,
    now: float | None = None,
) -> None:
    match = re.fullmatch(r"t=([0-9]{1,12}),v1=([a-f0-9]{64})", signature)
    if not secret or match is None:
        raise PaymentProviderError("TetraPay invalid webhook signature")
    timestamp, received = match.groups()
    expected = hmac.new(
        secret.encode(), timestamp.encode() + b"." + raw, hashlib.sha256
    ).hexdigest()
    if abs((time.time() if now is None else now) - int(timestamp)) > 300 or not hmac.compare_digest(
        expected,
        received,
    ):
        raise PaymentProviderError("TetraPay invalid webhook signature")


class TetraPayHTTPLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # httpx INFO includes the token-bearing path; retain our fixed diagnostic codes instead.
        return not any(
            host in record.getMessage()
            for host in (
                "api.tetra98.com",
                "api.sandbox.tetra98.com",
            )
        )


class TetraPayProvider:
    code = PaymentProviderCode.TETRAPAY

    def __init__(self, settings: Settings, *, transport: httpx.BaseTransport | None = None):
        http_logger = logging.getLogger("httpx")
        if not any(isinstance(item, TetraPayHTTPLogFilter) for item in http_logger.filters):
            http_logger.addFilter(TetraPayHTTPLogFilter())
        self.settings = settings
        self.transport = transport

    def _request(self, path: str, *, body: dict[str, object] | None = None) -> dict[str, Any]:
        key = self.settings.tetrapay_api_key
        if not self.settings.tetrapay_enabled or key is None or not key.get_secret_value().strip():
            raise PaymentProviderError("TetraPay unavailable")
        try:
            with httpx.Client(
                timeout=httpx.Timeout(6, connect=2),
                trust_env=False,
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = client.post(
                    self.settings.tetrapay_base_url + path,
                    headers={"Authorization": f"Bearer {key.get_secret_value()}"},
                    json=body,
                )
            if response.status_code not in {200, 201}:
                delay = response.headers.get("Retry-After", "")
                if not delay:
                    try:
                        retry = response.json().get("error", {}).get("retryAfter")
                        if type(retry) is int and retry > 0:
                            delay = str(retry)
                    except (ValueError, AttributeError):
                        pass
                error = PaymentProviderError(f"TetraPay HTTP {response.status_code}")
                if delay.isascii() and delay.isdigit():
                    error.retry_after = max(1, min(int(delay), 86400))
                if response.status_code == 429 and error.retry_after is None:
                    error.retry_after = 60
                raise error
            if len(response.content) > 65536:
                raise PaymentProviderError("TetraPay invalid response")
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError
            # Sandbox does not always include a body marker; the fixed API host isolates tokens.
            if response.headers.get("X-TetraPay-Sandbox") == "true":
                data["sandbox"] = True
            if "sandbox" in data and data["sandbox"] is not (
                self.settings.tetrapay_mode == "sandbox"
            ):
                raise PaymentProviderError("TetraPay environment mismatch")
            return data
        except (httpx.HTTPError, ValueError) as error:
            raise PaymentProviderError("TetraPay unavailable or invalid response") from None

    def create_checkout(self, request: ProviderCheckoutRequest) -> ProviderCheckoutResult:
        if request.currency != "IRR" or request.amount_irr <= 0:
            raise PaymentProviderError("TetraPay requires positive IRR amount")
        body: dict[str, object] = {
            "amount": str(request.amount_irr),
            "order_id": str(request.transaction_id),
            "callback_url": self.settings.tetrapay_callback_url,
            "allow_partial": False,
        }
        if self.settings.tetrapay_webhook_enabled:
            body["webhook_url"] = self.settings.tetrapay_webhook_url
        data = self._request("/payments", body=body)
        token, url = data.get("token"), data.get("payment_url")
        if not isinstance(token, str) or not 1 <= len(token) <= 64:
            raise PaymentProviderError("TetraPay invalid checkout token")
        if not isinstance(url, str) or len(url) > 2000 or not valid_checkout_url(url):
            raise PaymentProviderError("TetraPay invalid checkout URL")
        if data.get("amount") != str(request.amount_irr):
            raise PaymentProviderError("TetraPay checkout amount mismatch")
        return ProviderCheckoutResult("redirect", url, None, token)

    def validate_payment(
        self, data: dict[str, Any], request: ProviderVerificationRequest
    ) -> ProviderPaymentResult:
        try:
            payment = Payment.model_validate(data)
        except ValidationError:
            raise PaymentProviderError("TetraPay invalid payment response") from None
        evidence: dict[str, str | None] = {
            key: getattr(payment, key)
            for key in [
                "status",
                "amount",
                "payable_amount",
                "received_amount",
                "net_amount",
                "fee_total",
                "fee_payer",
                "fee_merchant",
                "method",
            ]
        }
        evidence["partial"] = str(payment.partial).lower()

        def reject(reason: str) -> NoReturn:
            error = PaymentProviderError("TetraPay rejected payment")
            error.evidence = {**evidence, "reason": reason}
            raise error

        if (
            payment.token != request.provider_reference
            or payment.order_id != str(request.transaction_id)
            or request.currency != "IRR"
            or int(payment.amount) != request.amount_irr
        ):
            reject("PAYMENT_IDENTITY_AMOUNT_MISMATCH")
        if payment.sandbox is not None and payment.sandbox != (
            self.settings.tetrapay_mode == "sandbox"
        ):
            reject("PAYMENT_ENVIRONMENT_MISMATCH")
        if (
            int(payment.payable_amount) != int(payment.amount) + int(payment.fee_payer)
            or int(payment.fee_total) != int(payment.fee_payer) + int(payment.fee_merchant)
            or int(payment.net_amount) != int(payment.amount) - int(payment.fee_merchant)
        ):
            reject("PAYMENT_AMOUNT_MISMATCH")
        if payment.status == "paid":
            if (
                payment.partial
                or payment.received_amount is None
                or int(payment.received_amount) < int(payment.payable_amount)
                or payment.method is None
                or payment.paid_at is None
            ):
                reject("PAYMENT_INCOMPLETE")
            try:
                paid_at = datetime.fromisoformat(payment.paid_at.replace("Z", "+00:00"))
                if paid_at.tzinfo is None or paid_at.utcoffset() != datetime.now(UTC).utcoffset():
                    raise ValueError
            except ValueError:
                raise PaymentProviderError("TetraPay invalid payment time") from None
            return ProviderPaymentResult("verified", payment.token, evidence)
        return ProviderPaymentResult(
            "expired" if payment.status == "expired" else "pending", payment.token, evidence
        )

    def verify_payment(self, request: ProviderVerificationRequest) -> ProviderPaymentResult:
        if not 1 <= len(request.provider_reference) <= 64:
            raise PaymentProviderError("TetraPay invalid token")
        return self.validate_payment(
            self._request(f"/payments/{quote(request.provider_reference, safe='')}/verify"), request
        )

    def verify_refund(self, request: ProviderVerificationRequest) -> ProviderPaymentResult:
        raise PaymentProviderError("TetraPay automated refunds are unsupported")


def valid_checkout_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname is not None
            and (
                parsed.hostname in {"tetrapay.online", "tetra98.com"}
                or parsed.hostname.endswith((".tetra98.com", ".tetrapay.online"))
            )
            and parsed.port in {None, 443}
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False
