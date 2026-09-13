from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import BillingOfferCode, BillingOrderStatus, BillingTransactionStatus
from app.billing.models import BillingOfferConfig, BillingOrder, BillingTransaction
from app.entitlements.models import UserAccessGrant

ORIGIN = {"Origin": "http://localhost:5173"}


def test_verified_refund_revokes_grant_without_deleting_order(client, db: Session) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "refund@example.com", "password": "long password"},
    )
    assert registered.status_code == 201
    db.add(
        BillingOfferConfig(
            offer_code=BillingOfferCode.NUTRITION_4W,
            price_irr=2_100_000,
            currency="IRR",
            is_active=True,
        )
    )
    db.flush()
    order = client.post(
        "/api/v1/billing/orders",
        headers=ORIGIN,
        json={
            "offer_code": "nutrition_4w",
            "provider": "fake",
            "client_idempotency_key": "refund-order",
        },
    ).json()
    checkout = client.post(
        f"/api/v1/billing/orders/{order['id']}/checkout",
        headers=ORIGIN,
        json={"provider": "fake"},
    ).json()
    verified = client.post(
        "/api/v1/billing/providers/fake/verify",
        headers=ORIGIN,
        json={
            "transaction_id": checkout["transaction_id"],
            "provider_reference": checkout["provider_reference"],
        },
    )
    assert verified.status_code == 200
    grant_id = verified.json()["access_grant_id"]
    provider = client.app.state.billing_providers["fake"]
    provider.set_outcome(checkout["transaction_id"], "refunded")

    first = client.post(
        "/api/v1/billing/providers/fake/refund",
        headers=ORIGIN,
        json={
            "transaction_id": checkout["transaction_id"],
            "provider_reference": checkout["provider_reference"],
        },
    )
    second = client.post(
        "/api/v1/billing/providers/fake/refund",
        headers=ORIGIN,
        json={
            "transaction_id": checkout["transaction_id"],
            "provider_reference": checkout["provider_reference"],
        },
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["verified"] is False
    assert first.json()["order_status"] == BillingOrderStatus.REFUNDED.value
    assert first.json()["transaction_status"] == BillingTransactionStatus.REFUNDED.value
    assert first.json()["access_grant_id"] == grant_id
    persisted_grant = db.get(UserAccessGrant, grant_id)
    assert persisted_grant is not None
    assert persisted_grant.revoked_at is not None
    persisted_order = db.get(BillingOrder, order["id"])
    assert persisted_order is not None
    assert persisted_order.status is BillingOrderStatus.REFUNDED
    assert str(persisted_order.access_grant_id) == grant_id
    persisted_transaction = db.get(BillingTransaction, checkout["transaction_id"])
    assert persisted_transaction is not None
    assert persisted_transaction.status is BillingTransactionStatus.REFUNDED

    history = client.get("/api/v1/billing/orders")
    assert history.status_code == 200
    assert history.json()[0]["id"] == order["id"]
    user = db.get(User, registered.json()["id"])
    assert user is not None
    assert db.get(UserAccessGrant, grant_id) is not None
