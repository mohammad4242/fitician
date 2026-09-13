from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import BillingOfferCode, BillingOrderStatus, PaymentProviderCode
from app.billing.models import BillingOrder
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.models import UserAccessGrant
from app.entitlements.service import grant_package

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    return response.json()


def make_admin(client: TestClient, db: Session) -> User:
    body = register(client, "revoke-admin@example.com")
    admin = db.get(User, body["id"])
    assert admin is not None
    admin.is_admin = True
    db.flush()
    return admin


def test_revoke_is_reasoned_idempotent_and_does_not_delete_or_refund_paid_order(
    client: TestClient,
    db: Session,
) -> None:
    member = register(client, "revoke-member@example.com")
    member_id = member["id"]
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)
    grant = grant_package(
        db,
        member_id,
        AccessPackageCode.COMPLETE_CARE,
        source=GrantSource.SUBSCRIPTION,
        starts_at=datetime.now(UTC),
        ends_at=datetime.now(UTC) + timedelta(weeks=8),
        term_weeks=8,
        idempotency_key="paid-grant-for-revoke",
    )
    order = BillingOrder(
        user_id=member_id,
        offer_code=BillingOfferCode.COMPLETE_CARE_8W,
        package_code_snapshot=AccessPackageCode.COMPLETE_CARE,
        duration_weeks_snapshot=8,
        amount_irr_snapshot=1_200_000,
        currency_snapshot="IRR",
        provider=PaymentProviderCode.FAKE,
        status=BillingOrderStatus.PAID,
        idempotency_key="paid-order-for-revoke",
        access_grant_id=grant.id,
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()

    path = f"/api/v1/admin/access/grants/{grant.id}/revoke"
    missing_reason = client.post(path, headers=ORIGIN, json={})
    revoked = client.post(path, headers=ORIGIN, json={"reason": "customer support"})
    retry = client.post(path, headers=ORIGIN, json={"reason": "retry"})

    assert missing_reason.status_code == 422
    assert revoked.status_code == retry.status_code == 200
    assert revoked.json()["id"] == retry.json()["id"] == str(grant.id)
    db.refresh(grant)
    db.refresh(order)
    assert grant.revoked_at is not None
    assert db.get(UserAccessGrant, grant.id) is not None
    assert order.status is BillingOrderStatus.PAID
    assert order.refunded_at is None


def test_restore_requires_a_new_grant_and_unrevoke_is_not_available(
    client: TestClient,
    db: Session,
) -> None:
    member = register(client, "restore-member@example.com")
    member_id = member["id"]
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)
    first = client.post(
        f"/api/v1/admin/access/users/{member_id}/grants",
        headers=ORIGIN,
        json={
            "package_code": "training_coach",
            "term_weeks": 4,
            "ends_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "reason": "temporary access",
            "client_idempotency_key": "restore-first",
        },
    )
    assert first.status_code == 201
    revoke = client.post(
        f"/api/v1/admin/access/grants/{first.json()['id']}/revoke",
        headers=ORIGIN,
        json={"reason": "access correction"},
    )
    assert revoke.status_code == 200
    assert client.post(
        f"/api/v1/admin/access/grants/{first.json()['id']}/unrevoke",
        headers=ORIGIN,
        json={"reason": "restore"},
    ).status_code == 404
    second = client.post(
        f"/api/v1/admin/access/users/{member_id}/grants",
        headers=ORIGIN,
        json={
            "package_code": "training_coach",
            "term_weeks": 4,
            "ends_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "reason": "restored by new grant",
            "client_idempotency_key": "restore-second",
        },
    )
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]
