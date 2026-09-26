from typing import cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.models import (
    AuthSession,
    MobileAccessToken,
    MobileRefreshToken,
    MobileTokenFamily,
    User,
)
from app.auth.security import hash_password

LOGIN_ENDPOINTS = ("/api/v1/auth/login", "/api/v1/auth/mobile/password")
PUBLIC_DUMMY_PASSWORD = "fitician-dummy-password-value"


def _login(client: TestClient, endpoint: str, password: str) -> Response:
    payload = {"email": "member@example.com", "password": password}
    headers = {}
    if endpoint == "/api/v1/auth/mobile/password":
        payload.update(device_id="security-test-device", platform="android", app_version="1.0")
    else:
        headers["Origin"] = "http://localhost:5173"
    return cast(Response, client.post(endpoint, headers=headers, json=payload))


@pytest.mark.parametrize("endpoint", LOGIN_ENDPOINTS)
@pytest.mark.parametrize("identity", ["google", "apple", "phone"])
@pytest.mark.parametrize("is_admin", [False, True])
def test_passwordless_accounts_reject_password_login_even_when_dummy_hash_matches(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    identity: str,
    is_admin: bool,
) -> None:
    user = User(
        email="member@example.com",
        password_hash=None,
        google_sub="google-security-test" if identity == "google" else None,
        apple_sub="apple-security-test" if identity == "apple" else None,
        phone_number="+989123456789" if identity == "phone" else None,
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    # A matching timing-only hash must never become an authentication credential.
    monkeypatch.setattr(service, "DUMMY_PASSWORD_HASH", hash_password(PUBLIC_DUMMY_PASSWORD))

    response = _login(client, endpoint, PUBLIC_DUMMY_PASSWORD)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert "set-cookie" not in response.headers
    assert "access_token" not in response.json()
    assert "refresh_token" not in response.json()
    for token_model in (AuthSession, MobileTokenFamily, MobileAccessToken, MobileRefreshToken):
        assert db.scalar(select(func.count()).select_from(token_model)) == 0
    assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize("endpoint", LOGIN_ENDPOINTS)
@pytest.mark.parametrize("password", ["member-owned-password", PUBLIC_DUMMY_PASSWORD])
def test_password_login_accepts_a_real_stored_password(
    client: TestClient,
    db: Session,
    endpoint: str,
    password: str,
) -> None:
    user = User(email="member@example.com", password_hash=hash_password(password))
    db.add(user)
    db.commit()

    response = _login(client, endpoint, password)

    assert response.status_code == 200
    body = response.json()
    if endpoint == "/api/v1/auth/mobile/password":
        assert body["user"]["id"] == str(user.id)
        assert body["access_token"]
        assert body["refresh_token"]
    else:
        assert body["id"] == str(user.id)
        assert "fitician_session" in response.cookies


@pytest.mark.parametrize("endpoint", LOGIN_ENDPOINTS)
def test_unknown_accounts_reject_the_public_dummy_password(
    client: TestClient,
    endpoint: str,
) -> None:
    response = _login(client, endpoint, PUBLIC_DUMMY_PASSWORD)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert "set-cookie" not in response.headers
