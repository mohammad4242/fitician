from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_audit.enums import AdminAuditAction
from app.admin_audit.models import AdminAuditEvent
from app.auth.models import User

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


def register_admin(client, db: Session, email: str) -> User:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    user = db.get(User, response.json()["id"])
    assert user is not None
    user.is_admin = True
    db.flush()
    return user


def test_audit_api_is_admin_only(client) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "audit-member@example.com", "password": PASSWORD},
    )
    assert registered.status_code == 201

    response = client.get("/api/v1/admin/audit/events")

    assert response.status_code == 403


def test_audit_api_lists_filters_and_redacts_sensitive_fields(client, db: Session) -> None:
    admin = register_admin(client, db, "audit-admin@example.com")
    created = client.post(
        "/api/v1/admin/access/campaigns",
        headers=ORIGIN,
        json={
            "code": "audit-manual-campaign",
            "name": "Audit manual campaign",
            "kind": "manual_promotion",
            "package_code": "complete",
            "duration_days": 56,
            "term_weeks": 8,
        },
    )
    assert created.status_code == 201

    all_events = client.get("/api/v1/admin/audit/events")
    filtered = client.get(
        "/api/v1/admin/audit/events",
        params={
            "action": AdminAuditAction.ACCESS_CAMPAIGN_CREATED.value,
            "actor_user_id": str(admin.id),
            "resource_type": "access_campaign",
        },
    )

    assert all_events.status_code == filtered.status_code == 200
    body = filtered.json()
    assert len(body) == 1
    assert body[0]["action"] == "access.campaign.created"
    assert body[0]["actor"]["user_id"] == str(admin.id)
    assert body[0]["resource_key"] == created.json()["id"]
    assert "password_hash" not in all_events.text
    assert "google_sub" not in all_events.text
    assert "apple_sub" not in all_events.text
    assert "session_token" not in all_events.text

    stored = db.scalar(
        select(AdminAuditEvent).where(
            AdminAuditEvent.resource_key == created.json()["id"],
        )
    )
    assert stored is not None


def test_audit_api_returns_newest_first(client, db: Session) -> None:
    register_admin(client, db, "audit-order-admin@example.com")
    for suffix in ("one", "two"):
        response = client.post(
            "/api/v1/admin/access/campaigns",
            headers=ORIGIN,
            json={
                "code": f"audit-order-{suffix}",
                "name": suffix,
                "kind": "manual_promotion",
                "package_code": "complete",
                "duration_days": 56,
                "term_weeks": 8,
            },
        )
        assert response.status_code == 201

    events = client.get("/api/v1/admin/audit/events", params={"limit": 2})

    assert events.status_code == 200
    assert len(events.json()) == 2
    assert events.json()[0]["created_at"] >= events.json()[1]["created_at"]
