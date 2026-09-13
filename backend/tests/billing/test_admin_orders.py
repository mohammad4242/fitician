from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import (
    BillingOfferCode,
    BillingOrderStatus,
    BillingTransactionStatus,
    PaymentProviderCode,
)
from app.billing.models import BillingOrder, BillingTransaction
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.service import grant_package

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


def make_admin(client, db: Session) -> User:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "admin-orders@example.com", "password": PASSWORD},
    )
    assert response.status_code == 201
    admin = db.get(User, response.json()["id"])
    assert admin is not None
    admin.is_admin = True
    db.flush()
    return admin


def test_admin_orders_support_filters_and_linked_access_grant(client, db: Session) -> None:
    admin = make_admin(client, db)
    grant = grant_package(
        db,
        admin.id,
        AccessPackageCode.COMPLETE_CARE,
        source=GrantSource.SUBSCRIPTION,
        starts_at=datetime.now(UTC),
        ends_at=datetime(2026, 11, 1, tzinfo=UTC),
        term_weeks=8,
        idempotency_key="admin-order-linked-grant",
    )
    paid_order = BillingOrder(
        user_id=admin.id,
        offer_code=BillingOfferCode.COMPLETE_CARE_8W,
        package_code_snapshot=AccessPackageCode.COMPLETE_CARE,
        duration_weeks_snapshot=8,
        amount_irr_snapshot=2_000_000,
        currency_snapshot="IRR",
        provider=PaymentProviderCode.FAKE,
        status=BillingOrderStatus.PAID,
        idempotency_key="admin-order-paid",
        access_grant_id=grant.id,
        paid_at=datetime.now(UTC),
    )
    created_order = BillingOrder(
        user_id=admin.id,
        offer_code=BillingOfferCode.TRAINING_4W,
        package_code_snapshot=AccessPackageCode.TRAINING,
        duration_weeks_snapshot=4,
        amount_irr_snapshot=500_000,
        currency_snapshot="IRR",
        provider=PaymentProviderCode.FAKE,
        status=BillingOrderStatus.CREATED,
        idempotency_key="admin-order-created",
    )
    transaction = BillingTransaction(
        order=paid_order,
        provider=PaymentProviderCode.FAKE,
        provider_reference="admin-order-reference",
        amount_irr=2_000_000,
        currency="IRR",
        status=BillingTransactionStatus.VERIFIED,
        verified_at=datetime.now(UTC),
    )
    db.add_all([paid_order, created_order, transaction])
    db.flush()

    filtered = client.get(
        "/api/v1/admin/billing/orders",
        params={"status": "paid", "provider": "fake", "user_id": str(admin.id)},
    )
    detail = client.get(f"/api/v1/admin/billing/orders/{paid_order.id}")
    created_only = client.get(
        "/api/v1/admin/billing/orders",
        params={"status": "created"},
    )

    assert filtered.status_code == detail.status_code == created_only.status_code == 200
    assert [item["id"] for item in filtered.json()] == [str(paid_order.id)]
    assert filtered.json()[0]["access_grant_id"] == str(grant.id)
    assert detail.json()["access_grant_id"] == str(grant.id)
    assert detail.json()["transactions"][0]["provider_reference"] == "admin-order-reference"
    assert [item["id"] for item in created_only.json()] == [str(created_order.id)]
