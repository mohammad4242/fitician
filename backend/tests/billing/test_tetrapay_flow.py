import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import func, select

from app.billing.enums import PaymentProviderCode
from app.billing.models import BillingOrder, BillingTransaction
from app.billing.providers import build_payment_providers
from app.billing.providers.tetrapay import TetraPayProvider
from app.billing.reconciliation import reconcile_batch
from app.config import Settings
from app.entitlements.enums import GrantSource
from app.entitlements.models import UserAccessGrant
from tests.billing.test_checkout import ORIGIN, create_order
from tests.billing.test_tetrapay import TOKEN, invoice, settings, verification


def setup_checkout(client, db):
    order = create_order(client, db)
    stored = db.get(BillingOrder, UUID(order["id"]))
    stored.provider = PaymentProviderCode.TETRAPAY
    db.flush()
    config = settings(tetrapay_webhook_enabled=True, tetrapay_webhook_secret="whsec_test")

    def handler(req):
        if str(req.url).endswith("/verify"):
            tx = db.scalar(
                select(BillingTransaction).where(BillingTransaction.order_id == stored.id)
            )
            v = verification()
            from dataclasses import replace

            return httpx.Response(200, json=invoice(replace(v, transaction_id=tx.id)))
        return httpx.Response(
            201,
            json={
                "token": TOKEN,
                "payment_url": f"https://sandbox.tetra98.com/pay/{TOKEN}",
                "amount": "1000000",
            },
        )

    provider = TetraPayProvider(config, transport=httpx.MockTransport(handler))
    client.app.state.billing_providers = {PaymentProviderCode.TETRAPAY: provider}
    response = client.post(
        f"/api/v1/billing/orders/{stored.id}/checkout",
        headers=ORIGIN,
        json={"provider": "tetrapay"},
    )
    assert response.status_code == 200
    return stored, response.json(), provider, config


def grants(db):
    return db.scalar(
        select(func.count())
        .select_from(UserAccessGrant)
        .where(UserAccessGrant.source == GrantSource.SUBSCRIPTION)
    )


def test_reuses_checkout_and_full_payment_grants_once(client, db):
    order, checkout, provider, _ = setup_checkout(client, db)
    again = client.post(
        f"/api/v1/billing/orders/{order.id}/checkout", headers=ORIGIN, json={"provider": "tetrapay"}
    )
    assert again.json() == checkout
    assert grants(db) == 0
    for _ in range(3):
        result = client.post(
            "/api/v1/billing/providers/tetrapay/verify",
            headers=ORIGIN,
            json={"transaction_id": checkout["transaction_id"]},
        )
        assert result.status_code == 200
        assert result.json()["verified"] is True
    assert grants(db) == 1


def test_pending_then_recovery_without_browser_after_order_expiry(client, db):
    order, checkout, provider, config = setup_checkout(client, db)
    tx = db.get(BillingTransaction, UUID(checkout["transaction_id"]))
    from dataclasses import replace

    v = replace(verification(), transaction_id=tx.id)
    body = invoice(v)
    body["status"] = "pending"
    provider.transport = httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    result = client.post(
        "/api/v1/billing/providers/tetrapay/verify",
        headers=ORIGIN,
        json={"transaction_id": str(tx.id)},
    )
    assert result.json()["transaction_status"] == "pending"
    assert grants(db) == 0
    body["status"] = "paid"
    order.expires_at = datetime.now(UTC) - timedelta(hours=1)
    tx.next_reconcile_at = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    assert reconcile_batch(db, {PaymentProviderCode.TETRAPAY: provider}) == 1
    assert grants(db) == 1


def test_webhook_duplicate_and_callback_race_safe(client, db):
    order, checkout, provider, _ = setup_checkout(client, db)
    from dataclasses import replace

    v = replace(verification(), transaction_id=UUID(checkout["transaction_id"]))
    body = invoice(v)
    body.update(event="payment.paid", event_id="event-1", sandbox=True)
    raw = json.dumps(body).encode()
    timestamp = str(int(time.time()))
    digest = hmac.new(b"whsec_test", timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-TetraPay-Signature": f"t={timestamp},v1={digest}",
        "X-TetraPay-Event": "payment.paid",
        "X-TetraPay-Event-Id": "event-1",
        "X-TetraPay-Sandbox": "true",
    }
    for _ in range(2):
        response = client.post("/api/v1/billing/webhooks/tetrapay", content=raw, headers=headers)
        assert response.status_code == 200
    assert grants(db) == 1
    response = client.post(
        "/api/v1/billing/providers/tetrapay/verify",
        headers=ORIGIN,
        json={"transaction_id": checkout["transaction_id"]},
    )
    assert response.json()["verified"]
    assert grants(db) == 1
    headers["X-TetraPay-Signature"] = "invalid"
    assert (
        client.post("/api/v1/billing/webhooks/tetrapay", content=raw, headers=headers).status_code
        == 400
    )


def test_token_callback_requires_owner(client, db):
    _, checkout, _, _ = setup_checkout(client, db)
    result = client.post("/api/v1/billing/tetrapay/return", headers=ORIGIN, json={"token": TOKEN})
    assert result.json()["transaction_id"] == checkout["transaction_id"]
    assert result.json()["verified"] is True
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    assert (
        client.post(
            "/api/v1/billing/tetrapay/return", headers=ORIGIN, json={"token": TOKEN}
        ).status_code
        == 401
    )


def test_disabled_providers_and_production_sandbox_rejected():
    assert PaymentProviderCode.TETRAPAY not in build_payment_providers(Settings(_env_file=None))
    for kwargs in [
        dict(tetrapay_enabled=True),
        dict(tetrapay_webhook_enabled=True),
        dict(tetrapay_base_url="https://evil.example"),
        dict(app_env="production", tetrapay_enabled=True, tetrapay_api_key="test"),
    ]:
        with pytest.raises(ValueError):
            Settings(_env_file=None, **kwargs)
