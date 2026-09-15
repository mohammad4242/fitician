from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import AuthSession
from app.auth.security import hash_session_token
from tests.error_assertions import assert_standard_error

ORIGIN = {"Origin": "http://localhost:5173"}


def register(client: TestClient, email: str = "user@example.com") -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": "long password"},
    )
    assert response.status_code == 201


def test_login_and_me_return_public_user(client: TestClient) -> None:
    register(client)
    client.post("/api/v1/auth/logout", headers=ORIGIN)

    login = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": "USER@example.com", "password": "long password"},
    )
    current = client.get("/api/v1/auth/me")

    assert login.status_code == 200
    assert current.status_code == 200
    assert current.json()["email"] == "user@example.com"
    assert current.json()["is_admin"] is False
    assert current.json()["phone_number"] is None
    assert set(current.json()) == {
        "id",
        "email",
        "phone_number",
        "created_at",
        "is_admin",
        "profile_photo_url",
    }
    assert current.json()["profile_photo_url"] is None


def test_login_uses_generic_error_for_unknown_email_and_wrong_password(
    client: TestClient,
) -> None:
    register(client)
    wrong_password = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": "user@example.com", "password": "wrong password"},
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": "unknown@example.com", "password": "wrong password"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    wrong_detail = wrong_password.json()["detail"]
    unknown_detail = unknown_email.json()["detail"]
    assert_standard_error(
        wrong_detail,
        code="AUTH_INVALID_CREDENTIALS",
        message="ایمیل یا رمز عبور درست نیست.",
        retryable=False,
    )
    assert_standard_error(
        unknown_detail,
        code="AUTH_INVALID_CREDENTIALS",
        message="ایمیل یا رمز عبور درست نیست.",
        retryable=False,
    )
    assert wrong_detail["request_id"] != unknown_detail["request_id"]


def test_me_rejects_missing_and_forged_sessions(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.set("fitician_session", "forged")
    forged = client.get("/api/v1/auth/me")

    assert forged.status_code == 401
    assert "Max-Age=0" in forged.headers["set-cookie"]


def test_expired_session_is_deleted(client: TestClient, db: Session) -> None:
    register(client)
    raw_token = client.cookies["fitician_session"]
    stored = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_session_token(raw_token))
    )
    assert stored is not None
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    expired = client.get("/api/v1/auth/me")

    assert expired.status_code == 401
    assert "Max-Age=0" in expired.headers["set-cookie"]
    assert db.get(AuthSession, stored.id) is None


def test_logout_invalidates_current_session(client: TestClient) -> None:
    register(client)

    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
