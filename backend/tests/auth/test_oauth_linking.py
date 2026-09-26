from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import AuthSession, MobileTokenFamily, User
from tests.auth.test_apple_auth import StubAppleIdentityProvider
from tests.auth.test_google_auth import StubGoogleIdentityProvider

ORIGIN = {"Origin": "http://localhost:5173"}
DEVICE = {"device_id": "linking-test", "platform": "ios", "app_version": "1.0.0"}


@pytest.mark.parametrize("provider", ["google", "apple"])
@pytest.mark.parametrize("mobile", [False, True], ids=["web", "mobile"])
@pytest.mark.parametrize("verified", [False, True], ids=["attacker-preregistered", "owned"])
def test_oauth_linking_requires_previously_verified_local_email(
    client: TestClient, db: Session, provider: str, mobile: bool, verified: bool
) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "member@example.com", "password": "existing password"},
    )
    assert registered.status_code == 201
    user = db.get(User, registered.json()["id"])
    assert user is not None
    original_password_hash = user.password_hash
    app = cast(FastAPI, client.app)
    if verified:
        delivery = app.state.email_provider.verification_deliveries[-1]
        token = parse_qs(urlsplit(delivery.verification_url).query)["token"][0]
        assert (
            client.post(
                "/api/v1/auth/email/verify", headers=ORIGIN, json={"token": token}
            ).status_code
            == 204
        )
    existing_mobile = client.post(
        "/api/v1/auth/mobile/password",
        json={"email": user.email, "password": "existing password", **DEVICE},
    )
    assert existing_mobile.status_code == 200
    client.cookies.clear()
    app.state.google_identity_provider = StubGoogleIdentityProvider()
    app.state.apple_identity_provider = StubAppleIdentityProvider(email="member@example.com")
    payload = (
        {"credential": "signed-google-id-token"}
        if provider == "google"
        else {"identity_token": "signed-apple-id-token", "nonce": "nonce-1"}
    )
    if mobile:
        payload.update(DEVICE)
    response = client.post(
        f"/api/v1/auth/{'mobile/' if mobile else ''}{provider}", headers=ORIGIN, json=payload
    )

    db.refresh(user)
    if verified:
        assert response.status_code == 200
        response_user = response.json()["user"] if mobile else response.json()
        assert response_user["id"] == str(user.id)
        assert getattr(user, f"{provider}_sub") == f"{provider}-sub-1"
        assert user.password_hash == original_password_hash
    else:
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == f"AUTH_{provider.upper()}_ACCOUNT_CONFLICT"
        assert "set-cookie" not in response.headers
        assert "access_token" not in response.json()
        assert getattr(user, f"{provider}_sub") is None
        assert user.email_verified_at is None
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 1
        assert db.scalar(select(func.count()).select_from(MobileTokenFamily)) == 1
    assert db.scalar(select(func.count()).select_from(User)) == 1
