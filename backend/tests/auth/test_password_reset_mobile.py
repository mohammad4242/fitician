from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.models import (
    AuthSession,
    MobileAccessToken,
    MobileRefreshToken,
    MobileTokenFamily,
    PasswordResetToken,
    User,
)
from app.auth.security import verify_password

ORIGIN = {"Origin": "http://localhost:5173"}


def _login(
    client: TestClient, email: str, device: str, password: str = "old password"
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/mobile/password",
        json={
            "email": email,
            "password": password,
            "device_id": device,
            "platform": "ios",
            "app_version": "1",
        },
    )
    assert response.status_code == 200
    return cast(dict[str, str], response.json())


def _setup_reset(client: TestClient) -> str:
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={"email": "reset@example.com", "password": "old password"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/auth/forgot-password",
            headers=ORIGIN,
            json={"email": "reset@example.com"},
        ).status_code
        == 202
    )
    delivery = cast(FastAPI, client.app).state.email_provider.deliveries[-1]
    return cast(str, parse_qs(urlsplit(delivery.reset_url).query)["token"][0])


def test_password_reset_revokes_every_device_and_rotated_generation(
    client: TestClient, db: Session
) -> None:
    reset_token = _setup_reset(client)
    tokens = [_login(client, "reset@example.com", device) for device in ("phone", "tablet")]
    rotated = client.post(
        "/api/v1/auth/mobile/refresh", json={"refresh_token": tokens[0]["refresh_token"]}
    )
    assert rotated.status_code == 200
    tokens.append(rotated.json())
    user = db.scalar(select(User).where(User.email == "reset@example.com"))
    assert user is not None
    cookie = client.cookies.get("fitician_session")
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={"email": "other@example.com", "password": "old password"},
        ).status_code
        == 201
    )
    other = _login(client, "other@example.com", "other-phone")

    reset = client.post(
        "/api/v1/auth/reset-password",
        headers=ORIGIN,
        json={"token": reset_token, "password": "new password"},
    )
    assert reset.status_code == 204
    client.cookies.clear()
    for token in tokens:
        assert (
            client.get(
                "/api/v1/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/mobile/refresh", json={"refresh_token": token["refresh_token"]}
            ).status_code
            == 401
        )
    assert (
        client.get("/api/v1/auth/me", headers={"Cookie": f"fitician_session={cookie}"}).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {other['access_token']}"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/mobile/refresh", json={"refresh_token": other["refresh_token"]}
        ).status_code
        == 200
    )
    db.expire_all()
    families = db.scalars(
        select(MobileTokenFamily).where(MobileTokenFamily.user_id == user.id)
    ).all()
    assert len(families) == 2
    assert all(f.revoked_at is not None and f.revoke_reason == "password_reset" for f in families)
    for model in (MobileAccessToken, MobileRefreshToken):
        stored = db.scalars(
            select(model).where(model.family_id.in_([f.id for f in families]))
        ).all()
        assert len(stored) == 3
        assert (
            db.scalar(
                select(func.count())
                .select_from(model)
                .where(model.family_id.in_([f.id for f in families]), model.revoked_at.is_(None))
            )
            == 0
        )
    assert db.scalar(select(AuthSession).where(AuthSession.user_id == user.id)) is None
    _login(client, "reset@example.com", "new-phone", "new password")


@pytest.mark.parametrize("token_valid", [False, True], ids=["invalid-token", "commit-failure"])
def test_failed_reset_preserves_password_and_sessions(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, token_valid: bool
) -> None:
    reset_token = _setup_reset(client)
    mobile = _login(client, "reset@example.com", "phone")
    if token_valid:

        def fail_commit() -> None:
            raise SQLAlchemyError("simulated commit failure")

        monkeypatch.setattr(db, "commit", fail_commit)
    response = client.post(
        "/api/v1/auth/reset-password",
        headers=ORIGIN,
        json={"token": reset_token if token_valid else "invalid", "password": "new password"},
    )
    assert response.status_code == (503 if token_valid else 400)
    db.expire_all()
    user = db.scalar(select(User).where(User.email == "reset@example.com"))
    assert user is not None and user.password_hash is not None
    assert verify_password("old password", user.password_hash)
    assert db.scalar(select(PasswordResetToken).where(PasswordResetToken.used_at.is_(None)))
    assert client.get("/api/v1/auth/me").status_code == 200
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {mobile['access_token']}"}
        ).status_code
        == 200
    )
