from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import BillingOfferCode, BillingOrderStatus
from app.billing.models import BillingOfferConfig, BillingOrder

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


def register(client, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    return response.json()["id"]


def add_config(db: Session, price: int = 2_500_000) -> None:
    db.add(
        BillingOfferConfig(
            offer_code=BillingOfferCode.TRAINING_4W,
            price_irr=price,
            currency="IRR",
            is_active=True,
        )
    )
    db.flush()


def test_create_order_snapshots_backend_price_package_and_duration(
    client,
    db: Session,
) -> None:
    user_id = register(client, "billing-order@example.com")
    add_config(db, price=3_100_000)

    response = client.post(
        "/api/v1/billing/orders",
        headers=ORIGIN,
        json={
            "offer_code": "training_4w",
            "provider": "fake",
            "client_idempotency_key": "checkout-attempt-1",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["offer_code"] == "training_4w"
    assert body["package_code_snapshot"] == "training"
    assert body["duration_weeks_snapshot"] == 4
    assert body["amount_irr_snapshot"] == 3_100_000
    assert body["status"] == BillingOrderStatus.CREATED.value
    order = db.get(BillingOrder, body["id"])
    assert order is not None
    assert str(order.user_id) == user_id


def test_create_order_idempotency_returns_existing_order(client, db: Session) -> None:
    register(client, "billing-idempotency@example.com")
    add_config(db)
    payload = {
        "offer_code": "training_4w",
        "provider": "fake",
        "client_idempotency_key": "same-checkout-attempt",
    }

    first = client.post("/api/v1/billing/orders", headers=ORIGIN, json=payload)
    second = client.post("/api/v1/billing/orders", headers=ORIGIN, json=payload)

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert db.scalar(select(BillingOrder).where(BillingOrder.id == first.json()["id"])) is not None


def test_client_cannot_override_backend_amount(client, db: Session) -> None:
    register(client, "billing-price-authority@example.com")
    add_config(db, price=4_200_000)

    response = client.post(
        "/api/v1/billing/orders",
        headers=ORIGIN,
        json={
            "offer_code": "training_4w",
            "provider": "fake",
            "client_idempotency_key": "forged-price",
            "amount_irr": 1,
        },
    )

    assert response.status_code == 422


def test_unavailable_offer_cannot_create_order(client, db: Session) -> None:
    register(client, "billing-unavailable@example.com")
    add_config(db, price=9_000_000)
    db.scalar(
        select(User).where(User.email == "billing-unavailable@example.com")
    )
    config = db.get(BillingOfferConfig, BillingOfferCode.TRAINING_4W)
    assert config is not None
    config.is_active = False
    db.flush()

    response = client.post(
        "/api/v1/billing/orders",
        headers=ORIGIN,
        json={
            "offer_code": "training_4w",
            "provider": "fake",
            "client_idempotency_key": "inactive-offer",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "BILLING_OFFER_UNAVAILABLE"
