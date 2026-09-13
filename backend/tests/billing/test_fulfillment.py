from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import BillingOfferCode
from app.billing.models import BillingOfferConfig, BillingOrder
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.models import UserAccessGrant

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


def setup_checkout(client, db: Session, email: str) -> tuple[dict, dict]:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": PASSWORD},
    )
    assert registered.status_code == 201
    db.add(
        BillingOfferConfig(
            offer_code=BillingOfferCode.TRAINING_4W,
            price_irr=1_500_000,
            currency="IRR",
            is_active=True,
        )
    )
    db.flush()
    created = client.post(
        "/api/v1/billing/orders",
        headers=ORIGIN,
        json={
            "offer_code": "training_4w",
            "provider": "fake",
            "client_idempotency_key": f"fulfill-{email}",
        },
    )
    assert created.status_code == 201
    order = created.json()
    checkout = client.post(
        f"/api/v1/billing/orders/{order['id']}/checkout",
        headers=ORIGIN,
        json={"provider": "fake"},
    )
    assert checkout.status_code == 200
    return order, checkout.json()


def test_verified_fake_payment_fulfills_once(client, db: Session) -> None:
    order, checkout = setup_checkout(client, db, "fulfill-once@example.com")

    first = client.post(
        "/api/v1/billing/providers/fake/verify",
        headers=ORIGIN,
        json={
            "transaction_id": checkout["transaction_id"],
            "provider_reference": checkout["provider_reference"],
        },
    )
    second = client.post(
        "/api/v1/billing/providers/fake/verify",
        headers=ORIGIN,
        json={
            "transaction_id": checkout["transaction_id"],
            "provider_reference": checkout["provider_reference"],
        },
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["verified"] is True
    assert first.json()["access_grant_id"] == second.json()["access_grant_id"]
    user = db.scalar(select(User).where(User.email == "fulfill-once@example.com"))
    assert user is not None
    paid_grants = db.scalars(
        select(UserAccessGrant).where(
            UserAccessGrant.user_id == user.id,
            UserAccessGrant.source == GrantSource.SUBSCRIPTION,
        )
    ).all()
    assert len(paid_grants) == 1
    persisted_order = db.get(BillingOrder, order["id"])
    assert persisted_order is not None
    assert persisted_order.access_grant_id == paid_grants[0].id


def test_failed_fake_payment_does_not_create_paid_grant(client, db: Session) -> None:
    order, checkout = setup_checkout(client, db, "fulfill-failed@example.com")
    provider = client.app.state.billing_providers["fake"]
    provider.set_outcome(checkout["transaction_id"], "failed")

    response = client.post(
        "/api/v1/billing/providers/fake/verify",
        headers=ORIGIN,
        json={
            "transaction_id": checkout["transaction_id"],
            "provider_reference": checkout["provider_reference"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is False
    assert body["access_grant_id"] is None
    user = db.scalar(select(User).where(User.email == "fulfill-failed@example.com"))
    assert user is not None
    assert (
        db.scalar(
            select(func.count()).select_from(UserAccessGrant).where(
                UserAccessGrant.user_id == user.id,
                UserAccessGrant.source == GrantSource.SUBSCRIPTION,
            )
        )
        == 0
    )
    assert db.get(BillingOrder, order["id"]).access_grant_id is None


def test_paid_order_uses_subscription_source_and_term_snapshot(client, db: Session) -> None:
    order, checkout = setup_checkout(client, db, "fulfill-term@example.com")
    response = client.post(
        "/api/v1/billing/providers/fake/verify",
        headers=ORIGIN,
        json={
            "transaction_id": checkout["transaction_id"],
            "provider_reference": checkout["provider_reference"],
        },
    )
    assert response.status_code == 200
    user = db.scalar(select(User).where(User.email == "fulfill-term@example.com"))
    assert user is not None
    grant = db.scalar(
        select(UserAccessGrant).where(
            UserAccessGrant.user_id == user.id,
            UserAccessGrant.source == GrantSource.SUBSCRIPTION,
        )
    )
    assert grant is not None
    assert grant.package_code is AccessPackageCode.TRAINING
    assert grant.term_weeks == 4
    assert grant.ends_at is not None
    assert grant.ends_at > grant.starts_at + timedelta(days=27)
