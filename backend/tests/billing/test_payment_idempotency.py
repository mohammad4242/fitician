from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import BillingOfferCode
from app.billing.models import BillingOfferConfig
from app.entitlements.enums import GrantSource
from app.entitlements.models import UserAccessGrant

ORIGIN = {"Origin": "http://localhost:5173"}


def test_replayed_verification_does_not_duplicate_grant(client, db: Session) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "payment-replay@example.com", "password": "long password"},
    )
    assert registered.status_code == 201
    db.add(
        BillingOfferConfig(
            offer_code=BillingOfferCode.TRAINING_6W,
            price_irr=2_000_000,
            currency="IRR",
            is_active=True,
        )
    )
    db.flush()
    order = client.post(
        "/api/v1/billing/orders",
        headers=ORIGIN,
        json={
            "offer_code": "training_6w",
            "provider": "fake",
            "client_idempotency_key": "replay-order",
        },
    ).json()
    checkout = client.post(
        f"/api/v1/billing/orders/{order['id']}/checkout",
        headers=ORIGIN,
        json={"provider": "fake"},
    ).json()
    body = {
        "transaction_id": checkout["transaction_id"],
        "provider_reference": checkout["provider_reference"],
    }

    responses = [
        client.post("/api/v1/billing/providers/fake/verify", headers=ORIGIN, json=body)
        for _ in range(3)
    ]

    assert all(response.status_code == 200 for response in responses)
    assert all(response.json()["verified"] is True for response in responses)
    assert len({response.json()["access_grant_id"] for response in responses}) == 1
    user = db.get(User, registered.json()["id"])
    assert user is not None
    grants = db.scalars(
        select(UserAccessGrant).where(
            UserAccessGrant.user_id == user.id,
            UserAccessGrant.source == GrantSource.SUBSCRIPTION,
        )
    ).all()
    assert len(grants) == 1

