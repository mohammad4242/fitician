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


@pytest.mark.parametrize(
    "change",
    [
        {"status": "pending"},
        {"status": "created"},
        {"status": "expired"},
        {"token": "forged"},
        {"order_id": "forged"},
        {"amount": "999999"},
        {"received_amount": "500000", "partial": True},
        {"received_amount": "1000000"},
        {"amount": 1000000.0},
        {"sandbox": False},
        {"method": "unknown"},
    ],
)
def test_untrusted_results_never_issue_access(client, db, change):
    _, checkout, provider, _ = setup_checkout(client, db)
    from dataclasses import replace

    v = replace(verification(), transaction_id=UUID(checkout["transaction_id"]))
    body = invoice(v)
    body.update(change)
    provider.transport = httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    client.post(
        "/api/v1/billing/providers/tetrapay/verify",
        headers=ORIGIN,
        json={"transaction_id": checkout["transaction_id"]},
    )
    assert grants(db) == 0
    assert db.get(BillingOrder, UUID(checkout["order_id"])).access_grant_id is None
    if change.get("partial"):
        tx = db.get(BillingTransaction, UUID(checkout["transaction_id"]))
        assert tx.provider_evidence["received_amount"] == "500000"
        assert tx.provider_evidence["reason"] == "PAYMENT_INCOMPLETE"


def test_checkout_timeout_recovers_same_durable_transaction(client, db):
    order, checkout, provider, _ = setup_checkout(client, db)
    tx = db.get(BillingTransaction, UUID(checkout["transaction_id"]))
    tx.checkout_url = tx.provider_reference = None
    tx.next_reconcile_at = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    count = 0

    def handler(req):
        nonlocal count
        count += 1
        assert json.loads(req.content)["order_id"] == str(tx.id)
        raise httpx.ReadTimeout("sensitive", request=req)

    provider.transport = httpx.MockTransport(handler)
    result = client.post(
        f"/api/v1/billing/orders/{order.id}/checkout", headers=ORIGIN, json={"provider": "tetrapay"}
    )
    assert result.status_code == 422
    db.refresh(tx)
    assert tx.provider_reference is None
    assert tx.next_reconcile_at > datetime.now(UTC)
    # New provider instance simulates process restart. Same external id recovers the invoice.
    replacement = TetraPayProvider(
        provider.settings,
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                json={
                    "token": TOKEN,
                    "payment_url": f"https://sandbox.tetra98.com/pay/{TOKEN}",
                    "amount": "1000000",
                },
            )
        ),
    )
    client.app.state.billing_providers[PaymentProviderCode.TETRAPAY] = replacement
    tx.next_reconcile_at = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    result = client.post(
        f"/api/v1/billing/orders/{order.id}/checkout", headers=ORIGIN, json={"provider": "tetrapay"}
    )
    assert result.json()["transaction_id"] == checkout["transaction_id"]
    assert count == 1
    assert grants(db) == 0


def test_unsigned_webhook_disabled_and_provider_methods(client, db):
    _, _, provider, _ = setup_checkout(client, db)
    provider.settings.tetrapay_webhook_enabled = False
    assert (
        client.post("/api/v1/billing/webhooks/tetrapay", json={"status": "paid"}).status_code == 503
    )
    assert grants(db) == 0
    methods = client.get("/api/v1/billing/checkout-methods").json()
    assert methods["providers"] == ["tetrapay"]
    assert client.get("/api/v1/billing/pending-checkouts").json()[0]["provider_reference"] == TOKEN


def test_success_cannot_be_reallocated_by_a_different_reference(client, db):
    _, checkout, _, _ = setup_checkout(client, db)
    payload = {"transaction_id": checkout["transaction_id"]}
    assert client.post(
        "/api/v1/billing/providers/tetrapay/verify", headers=ORIGIN, json=payload
    ).json()["verified"]
    payload["provider_reference"] = "another-token"
    assert (
        client.post(
            "/api/v1/billing/providers/tetrapay/verify", headers=ORIGIN, json=payload
        ).status_code
        == 422
    )
    assert grants(db) == 1


def test_independent_database_sessions_serialize_webhook_and_verifiers(test_settings):
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import replace
    from threading import Barrier
    from uuid import uuid4

    from sqlalchemy import create_engine, delete
    from sqlalchemy.orm import Session

    from app.auth.models import User
    from app.billing.enums import BillingOfferCode, BillingOrderStatus, BillingTransactionStatus
    from app.billing.schemas import VerifyPaymentRequest
    from app.billing.service import reconcile_payment, verify_payment
    from app.entitlements.enums import AccessPackageCode

    engine = create_engine(test_settings.database_url)
    user_id, order_id, tx_id = uuid4(), uuid4(), uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.com", password_hash="unused"))
        session.flush()
        session.add(
            BillingOrder(
                id=order_id,
                user_id=user_id,
                offer_code=BillingOfferCode.TRAINING_4W,
                package_code_snapshot=AccessPackageCode.TRAINING,
                duration_weeks_snapshot=4,
                amount_irr_snapshot=1000000,
                currency_snapshot="IRR",
                provider=PaymentProviderCode.TETRAPAY,
                status=BillingOrderStatus.PENDING,
                idempotency_key=str(order_id),
            )
        )
        session.flush()
        session.add(
            BillingTransaction(
                id=tx_id,
                order_id=order_id,
                provider=PaymentProviderCode.TETRAPAY,
                provider_reference=TOKEN,
                amount_irr=1000000,
                currency="IRR",
                provider_mode="sandbox",
                status=BillingTransactionStatus.PENDING,
            )
        )
        session.commit()
    v = replace(verification(), transaction_id=tx_id)
    provider = TetraPayProvider(
        settings(), transport=httpx.MockTransport(lambda _: httpx.Response(200, json=invoice(v)))
    )
    barrier = Barrier(3)

    def worker(kind):
        with Session(engine) as session:
            # Preload stale objects, like requests arriving at different replicas.
            tx = session.get(BillingTransaction, tx_id)
            barrier.wait(timeout=10)
            if kind == "webhook":
                order = session.scalar(
                    select(BillingOrder)
                    .where(BillingOrder.id == order_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                session.refresh(tx)
                result = reconcile_payment(
                    session,
                    tx,
                    order,
                    provider,
                    trusted_result=provider.validate_payment(invoice(v), v),
                )
            else:
                result = verify_payment(
                    session,
                    user_id,
                    PaymentProviderCode.TETRAPAY,
                    VerifyPaymentRequest(transaction_id=tx_id),
                    provider,
                )
            session.commit()
            return result.access_grant_id

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            ids = list(pool.map(worker, ["return", "scheduler", "webhook"]))
        assert len(set(ids)) == 1 and ids[0] is not None
        with Session(engine) as session:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(UserAccessGrant)
                    .where(
                        UserAccessGrant.user_id == user_id,
                        UserAccessGrant.source == GrantSource.SUBSCRIPTION,
                    )
                )
                == 1
            )
    finally:
        with Session(engine) as session:
            session.execute(delete(BillingOrder).where(BillingOrder.id == order_id))
            session.execute(delete(User).where(User.id == user_id))
            session.commit()
        engine.dispose()


def test_signed_sandbox_event_and_stored_mode_cannot_cross_into_live(client, db):
    _, checkout, provider, _ = setup_checkout(client, db)
    provider.settings.tetrapay_mode = "live"
    provider.settings.tetrapay_base_url = "https://api.tetra98.com/api/v1"
    from dataclasses import replace

    body = invoice(replace(verification(), transaction_id=UUID(checkout["transaction_id"])))
    body.update(event="payment.paid", event_id="sandbox-crossing", sandbox=True)
    raw = json.dumps(body).encode()
    timestamp = str(int(time.time()))
    digest = hmac.new(b"whsec_test", timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    result = client.post(
        "/api/v1/billing/webhooks/tetrapay",
        content=raw,
        headers={
            "X-TetraPay-Signature": f"t={timestamp},v1={digest}",
            "X-TetraPay-Event": "payment.paid",
            "X-TetraPay-Event-Id": "sandbox-crossing",
            "X-TetraPay-Sandbox": "true",
        },
    )
    assert result.status_code == 400
    result = client.post(
        "/api/v1/billing/providers/tetrapay/verify",
        headers=ORIGIN,
        json={"transaction_id": checkout["transaction_id"]},
    )
    assert result.status_code == 422
    assert grants(db) == 0


def test_pending_checkout_is_reusable_after_internal_ttl(client, db):
    order, checkout, _, _ = setup_checkout(client, db)
    order.expires_at = datetime.now(UTC) - timedelta(hours=1)
    db.flush()
    response = client.post(
        f"/api/v1/billing/orders/{order.id}/checkout", headers=ORIGIN, json={"provider": "tetrapay"}
    )
    assert response.status_code == 200
    assert response.json()["transaction_id"] == checkout["transaction_id"]
    assert grants(db) == 0
