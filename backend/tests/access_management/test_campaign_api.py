from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access_management.models import AccessCampaign
from app.auth.models import User

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


def register_admin(client: TestClient, db: Session, email: str) -> User:
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


def test_admin_can_create_update_activate_and_deactivate_campaign(
    client: TestClient, db: Session
) -> None:
    register_admin(client, db, "campaign-api-admin@example.com")
    payload = {
        "code": "spring-promotion",
        "name": "Spring promotion",
        "description": "Selected members",
        "kind": "manual_promotion",
        "package_code": "complete",
        "duration_days": 60,
        "term_weeks": 8,
        "is_active": False,
        "max_total_redemptions": 10,
    }

    created = client.post("/api/v1/admin/access/campaigns", headers=ORIGIN, json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["code"] == "spring-promotion"
    assert body["redemption_count"] == 0
    assert body["package_code"] == "complete"

    updated = client.patch(
        f"/api/v1/admin/access/campaigns/{body['id']}",
        headers=ORIGIN,
        json={
            "name": "Spring support promotion",
            "available_from": datetime(2026, 9, 15, tzinfo=UTC).isoformat(),
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Spring support promotion"

    activated = client.post(
        f"/api/v1/admin/access/campaigns/{body['id']}/activate",
        headers=ORIGIN,
    )
    deactivated = client.post(
        f"/api/v1/admin/access/campaigns/{body['id']}/deactivate",
        headers=ORIGIN,
    )
    assert activated.status_code == deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    listed = client.get("/api/v1/admin/access/campaigns")
    assert listed.status_code == 200
    assert any(item["code"] == "spring-promotion" for item in listed.json())
    assert (
        db.scalar(select(AccessCampaign).where(AccessCampaign.code == "spring-promotion"))
        is not None
    )


def test_campaign_mutations_require_admin_and_trusted_origin(client: TestClient) -> None:
    member = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "campaign-api-member@example.com", "password": PASSWORD},
    )
    assert member.status_code == 201
    assert client.get("/api/v1/admin/access/campaigns").status_code == 403
    assert (
        client.post(
            "/api/v1/admin/access/campaigns",
            headers=ORIGIN,
            json={
                "code": "untrusted-campaign",
                "name": "Untrusted",
                "kind": "manual_promotion",
                "package_code": "complete",
                "duration_days": 30,
                "term_weeks": 8,
            },
        ).status_code
        == 403
    )


def test_campaign_patch_cannot_change_activation_state(client: TestClient, db: Session) -> None:
    admin = register_admin(client, db, "campaign-patch-state-admin@example.com")
    created = client.post(
        "/api/v1/admin/access/campaigns",
        headers=ORIGIN,
        json={
            "code": "patch-state-campaign",
            "name": "Patch state",
            "kind": "manual_promotion",
            "package_code": "complete",
            "duration_days": 56,
            "term_weeks": 8,
        },
    )
    assert created.status_code == 201

    patched = client.patch(
        f"/api/v1/admin/access/campaigns/{created.json()['id']}",
        headers=ORIGIN,
        json={"is_active": True},
    )

    assert patched.status_code == 422
    assert admin.is_admin is True


def test_admin_can_manually_redeem_only_a_manual_campaign_with_reason(
    client: TestClient,
    db: Session,
) -> None:
    admin = register_admin(client, db, "campaign-redeem-admin@example.com")
    member_response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "campaign-redeem-member@example.com", "password": PASSWORD},
    )
    assert member_response.status_code == 201
    member_id = member_response.json()["id"]
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": admin.email, "password": PASSWORD},
    )
    campaign = client.post(
        "/api/v1/admin/access/campaigns",
        headers=ORIGIN,
        json={
            "code": "manual-redeem-api",
            "name": "Manual redeem",
            "kind": "manual_promotion",
            "package_code": "training",
            "duration_days": 30,
            "term_weeks": 4,
            "is_active": True,
        },
    )
    assert campaign.status_code == 201
    path = f"/api/v1/admin/access/users/{member_id}/campaigns/{campaign.json()['id']}/redeem"

    missing_reason = client.post(path, headers=ORIGIN, json={})
    redeemed = client.post(path, headers=ORIGIN, json={"reason": "beta tester"})
    retry = client.post(path, headers=ORIGIN, json={"reason": "retry"})

    assert missing_reason.status_code == 422
    assert redeemed.status_code == 200
    assert retry.status_code == 200
    assert redeemed.json()["grant"]["id"] == retry.json()["grant"]["id"]
