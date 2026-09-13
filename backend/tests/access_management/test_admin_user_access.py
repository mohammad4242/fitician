from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.service import grant_package
from app.profile.models import UserProfile

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
    body = register(client, "access-search-admin@example.com")
    admin = db.get(User, body["id"])
    assert admin is not None
    admin.is_admin = True
    db.flush()
    return admin


def test_admin_can_search_by_email_phone_display_name_and_uuid(
    client: TestClient,
    db: Session,
) -> None:
    member = register(client, "searchable@example.com")
    user = db.get(User, member["id"])
    assert user is not None
    user.phone_number = "+989123456789"
    db.add(UserProfile(user_id=user.id, display_name="Ali Searchable"))
    db.flush()
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)

    for query in ("searchable@EXAMPLE.COM", "09123456789", "ali searchable", str(user.id)):
        response = client.get("/api/v1/admin/access/users", params={"q": query})
        assert response.status_code == 200
        assert any(item["user_id"] == str(user.id) for item in response.json())


def test_user_access_detail_is_safe_and_includes_snapshot_and_all_grants(
    client: TestClient,
    db: Session,
) -> None:
    member = register(client, "detail-access@example.com")
    user = db.get(User, member["id"])
    assert user is not None
    db.add(UserProfile(user_id=user.id, display_name="Detail Member"))
    db.flush()
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)

    response = client.get(f"/api/v1/admin/access/users/{user.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["member"]["display_name"] == "Detail Member"
    assert "password_hash" not in response.text
    assert "google_sub" not in response.text
    assert "apple_sub" not in response.text
    assert "session" not in response.text.lower()
    assert "entitlement_snapshot" in body
    assert body["grants"]


def test_member_summary_only_reports_current_paid_access_end(
    client: TestClient,
    db: Session,
) -> None:
    member = register(client, "paid-access-summary@example.com")
    member_id = member["id"]
    now = datetime.now(UTC)
    grant_package(
        db,
        member_id,
        AccessPackageCode.TRAINING,
        source=GrantSource.SUBSCRIPTION,
        starts_at=now - timedelta(days=10),
        ends_at=now - timedelta(days=1),
        term_weeks=4,
        idempotency_key="expired-paid-summary",
    )
    db.commit()
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    make_admin(client, db)

    response = client.get(f"/api/v1/admin/access/users/{member_id}")

    assert response.status_code == 200
    assert response.json()["member"]["paid_access_end"] is None
