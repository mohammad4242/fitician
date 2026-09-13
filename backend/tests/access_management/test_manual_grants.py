from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.models import UserAccessGrant

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
    body = register(client, "manual-grant-admin@example.com")
    admin = db.get(User, body["id"])
    assert admin is not None
    admin.is_admin = True
    db.flush()
    return admin


def test_admin_grant_is_package_only_finite_reasoned_and_idempotent(
    client: TestClient,
    db: Session,
) -> None:
    member = register(client, "manual-grant-member@example.com")
    member_id = member["id"]
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)
    starts_at = datetime.now(UTC)
    ends_at = starts_at + timedelta(weeks=4)
    payload = {
        "package_code": "training",
        "term_weeks": 4,
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "reason": " beta tester ",
        "client_idempotency_key": "manual-training-1",
    }

    first = client.post(
        f"/api/v1/admin/access/users/{member_id}/grants",
        headers=ORIGIN,
        json=payload,
    )
    second = client.post(
        f"/api/v1/admin/access/users/{member_id}/grants",
        headers=ORIGIN,
        json=payload,
    )

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    grant = db.get(UserAccessGrant, first.json()["id"])
    assert grant is not None
    assert grant.package_code is AccessPackageCode.TRAINING
    assert grant.source is GrantSource.ADMIN
    assert grant.ends_at is not None
    assert (
        db.scalar(
            select(func.count())
            .select_from(UserAccessGrant)
            .where(
                UserAccessGrant.user_id == member_id, UserAccessGrant.source == GrantSource.ADMIN
            )
        )
        == 1
    )


def test_admin_grant_idempotency_supports_server_default_start(
    client: TestClient,
    db: Session,
) -> None:
    member = register(client, "manual-grant-default-start@example.com")
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)
    payload = {
        "package_code": "complete_care",
        "term_weeks": 8,
        "ends_at": (datetime.now(UTC) + timedelta(weeks=8)).isoformat(),
        "reason": "support entitlement",
        "client_idempotency_key": "default-start-1",
    }

    first = client.post(
        f"/api/v1/admin/access/users/{member['id']}/grants",
        headers=ORIGIN,
        json=payload,
    )
    second = client.post(
        f"/api/v1/admin/access/users/{member['id']}/grants",
        headers=ORIGIN,
        json=payload,
    )

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_admin_grant_rejects_free_arbitrary_entitlements_missing_reason_and_indefinite_access(
    client: TestClient,
    db: Session,
) -> None:
    member = register(client, "manual-grant-validation-member@example.com")
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)
    path = f"/api/v1/admin/access/users/{member['id']}/grants"
    common = {
        "starts_at": datetime.now(UTC).isoformat(),
        "ends_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        "reason": "support",
        "client_idempotency_key": "validation-key",
    }

    free = client.post(path, headers=ORIGIN, json={**common, "package_code": "free"})
    arbitrary = client.post(
        path,
        headers=ORIGIN,
        json={
            **common,
            "package_code": "training",
            "term_weeks": 4,
            "entitlements": ["body_analysis.run"],
        },
    )
    missing_reason = client.post(
        path,
        headers=ORIGIN,
        json={**common, "package_code": "training", "term_weeks": 4, "reason": "   "},
    )
    indefinite = client.post(
        path,
        headers=ORIGIN,
        json={
            "package_code": "training",
            "term_weeks": 4,
            "starts_at": datetime.now(UTC).isoformat(),
            "reason": "support",
            "client_idempotency_key": "indefinite-key",
        },
    )
    null_reason = client.post(
        path,
        headers=ORIGIN,
        json={**common, "package_code": "training", "term_weeks": 4, "reason": None},
    )
    null_key = client.post(
        path,
        headers=ORIGIN,
        json={
            **common,
            "package_code": "training",
            "term_weeks": 4,
            "client_idempotency_key": None,
        },
    )

    assert free.status_code == arbitrary.status_code == missing_reason.status_code == 422
    assert indefinite.status_code == 422
    assert null_reason.status_code == null_key.status_code == 422
