from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import BillingOfferCode
from app.billing.models import BillingOfferConfig

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


def register_admin(client, db: Session, email: str = "billing-admin@example.com") -> User:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    user.is_admin = True
    db.flush()
    return user


def test_admin_can_view_all_offers_and_update_price_window(client, db: Session) -> None:
    register_admin(client, db)
    db.add(
        BillingOfferConfig(
            offer_code=BillingOfferCode.TRAINING_4W,
            price_irr=1_000_000,
            currency="IRR",
            is_active=True,
        )
    )
    db.flush()
    available_until = datetime.now(UTC) + timedelta(days=10)

    listed = client.get("/api/v1/admin/billing/offers")
    updated = client.patch(
        "/api/v1/admin/billing/offers/training_6w",
        headers=ORIGIN,
        json={
            "price_irr": 2_750_000,
            "currency": "IRR",
            "is_active": True,
            "available_until": available_until.isoformat(),
        },
    )

    assert listed.status_code == 200
    assert len(listed.json()) == 18
    existing = next(item for item in listed.json() if item["offer_code"] == "training_4w")
    assert existing["price_irr"] == 1_000_000
    assert existing["duration_weeks"] == 4
    assert updated.status_code == 200
    body = updated.json()
    assert body["offer_code"] == "training_6w"
    assert body["package_code"] == "training"
    assert body["duration_weeks"] == 6
    assert body["price_irr"] == 2_750_000
    assert body["is_available"] is True


def test_admin_update_cannot_change_immutable_offer_definition(client, db: Session) -> None:
    register_admin(client, db, "billing-admin-immutable@example.com")

    response = client.patch(
        "/api/v1/admin/billing/offers/training_4w",
        headers=ORIGIN,
        json={"price_irr": 1_000_000, "duration_weeks": 8, "package_code": "complete"},
    )

    assert response.status_code == 422


def test_non_admin_cannot_access_billing_admin_api(client) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "billing-member@example.com", "password": PASSWORD},
    )
    assert registered.status_code == 201

    response = client.get("/api/v1/admin/billing/offers")

    assert response.status_code == 403


def test_admin_can_view_order_and_transaction_history(client, db: Session) -> None:
    register_admin(client, db, "billing-admin-orders@example.com")
    db.add(
        BillingOfferConfig(
            offer_code=BillingOfferCode.NUTRITION_4W,
            price_irr=1_900_000,
            currency="IRR",
            is_active=True,
        )
    )
    db.flush()
    created = client.post(
        "/api/v1/billing/orders",
        headers=ORIGIN,
        json={
            "offer_code": "nutrition_4w",
            "provider": "fake",
            "client_idempotency_key": "admin-order-history",
        },
    )
    assert created.status_code == 201

    listed = client.get("/api/v1/admin/billing/orders")
    detail = client.get(f"/api/v1/admin/billing/orders/{created.json()['id']}")

    assert listed.status_code == detail.status_code == 200
    assert listed.json()[0]["id"] == created.json()["id"]
    assert detail.json()["transactions"] == []
    assert "email" not in detail.json()
