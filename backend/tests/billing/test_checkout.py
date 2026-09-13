from sqlalchemy.orm import Session

from app.billing.enums import BillingOfferCode, BillingOrderStatus, BillingTransactionStatus
from app.billing.models import BillingOfferConfig, BillingOrder, BillingTransaction

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


def register(client, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201


def create_order(client, db: Session, email: str = "checkout@example.com") -> dict:
    register(client, email)
    db.add(
        BillingOfferConfig(
            offer_code=BillingOfferCode.TRAINING_4W,
            price_irr=1_000_000,
            currency="IRR",
            is_active=True,
        )
    )
    db.flush()
    response = client.post(
        "/api/v1/billing/orders",
        headers=ORIGIN,
        json={
            "offer_code": "training_4w",
            "provider": "fake",
            "client_idempotency_key": f"checkout-{email}",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_fake_checkout_creates_pending_transaction_without_unlocking_directly(
    client,
    db: Session,
) -> None:
    order_body = create_order(client, db)

    response = client.post(
        f"/api/v1/billing/orders/{order_body['id']}/checkout",
        headers=ORIGIN,
        json={"provider": "fake"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == order_body["id"]
    assert body["provider"] == "fake"
    assert body["checkout_kind"] == "redirect"
    assert body["checkout_url"]
    assert body["provider_reference"].startswith("fake-payment:")
    transaction = db.get(BillingTransaction, body["transaction_id"])
    assert transaction is not None
    assert transaction.status is BillingTransactionStatus.PENDING
    order = db.get(BillingOrder, order_body["id"])
    assert order is not None
    assert order.status is BillingOrderStatus.PENDING
    assert order.access_grant_id is None


def test_checkout_requires_order_ownership(client, db: Session) -> None:
    order_body = create_order(client, db, "checkout-owner@example.com")
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    register(client, "checkout-other@example.com")

    response = client.post(
        f"/api/v1/billing/orders/{order_body['id']}/checkout",
        headers=ORIGIN,
        json={"provider": "fake"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "BILLING_ORDER_NOT_FOUND"


def test_checkout_provider_must_match_order(client, db: Session) -> None:
    order_body = create_order(client, db, "checkout-provider@example.com")

    response = client.post(
        f"/api/v1/billing/orders/{order_body['id']}/checkout",
        headers=ORIGIN,
        json={"provider": "fake"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "fake"


def test_billing_order_history_is_owner_scoped(client, db: Session) -> None:
    order_body = create_order(client, db, "checkout-history@example.com")
    own = client.get("/api/v1/billing/orders")
    assert own.status_code == 200
    assert [item["id"] for item in own.json()] == [order_body["id"]]

    client.post("/api/v1/auth/logout", headers=ORIGIN)
    register(client, "checkout-history-other@example.com")
    other = client.get("/api/v1/billing/orders")
    assert other.status_code == 200
    assert other.json() == []

    missing = client.get(f"/api/v1/billing/orders/{order_body['id']}")
    assert missing.status_code == 404
