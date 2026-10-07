from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth.models import AuthSession, User
from app.config import Settings
from app.database.session import get_db
from app.main import create_app
from app.user_activity.models import UserActivityEvent


def test_register_creates_user_session_and_cookie(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:5173"},
        json={"email": " New@Example.com ", "password": "long password"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert "password_hash" not in response.json()
    assert "fitician_session" in response.cookies
    user = db.scalar(select(User).where(User.email == "new@example.com"))
    assert user is not None
    assert user.password_hash != "long password"
    session = db.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
    assert session is not None
    event = db.scalar(select(UserActivityEvent).where(UserActivityEvent.user_id == user.id))
    assert event is not None
    assert event.event_type == "auth.registered"
    assert event.resource_id == str(session.id)
    assert event.deduplication_key == f"web-auth:{session.id}"
    assert event.safe_metadata == {"platform": "web", "auth_method": "password"}


def test_each_registration_records_a_distinct_explicit_auth_event(
    client: TestClient, db: Session
) -> None:
    headers = {"Origin": "http://localhost:5173"}
    for email in ("one@example.com", "two@example.com"):
        assert (
            client.post(
                "/api/v1/auth/register",
                headers=headers,
                json={"email": email, "password": "long password"},
            ).status_code
            == 201
        )

    events = db.scalars(
        select(UserActivityEvent)
        .join(User, User.id == UserActivityEvent.user_id)
        .where(User.email.in_(["one@example.com", "two@example.com"]))
    ).all()
    assert len(events) == 2
    assert len({event.resource_id for event in events}) == 2
    assert len({event.deduplication_key for event in events}) == 2


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    payload = {"email": "duplicate@example.com", "password": "long password"}
    headers = {"Origin": "http://localhost:5173"}

    assert client.post("/api/v1/auth/register", headers=headers, json=payload).status_code == 201
    response = client.post("/api/v1/auth/register", headers=headers, json=payload)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "AUTH_EMAIL_ALREADY_REGISTERED"
    assert response.json()["detail"]["message"] == "این ایمیل قبلاً ثبت شده است."
    assert response.json()["detail"]["retryable"] is False


def test_register_rejects_invalid_input(client: TestClient) -> None:
    rejected_password = "secret7"
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:5173"},
        json={"email": "invalid", "password": rejected_password},
    )

    assert response.status_code == 422
    assert rejected_password not in response.text
    assert all("input" not in error for error in response.json()["detail"])


def test_register_rejects_admin_status(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:5173"},
        json={
            "email": "escalation@example.com",
            "password": "long password",
            "is_admin": True,
        },
    )

    assert response.status_code == 422
    assert db.scalar(select(User).where(User.email == "escalation@example.com")) is None


def test_register_rejects_untrusted_or_missing_origin(client: TestClient) -> None:
    payload = {"email": "origin@example.com", "password": "long password"}

    assert client.post("/api/v1/auth/register", json=payload).status_code == 403
    assert (
        client.post(
            "/api/v1/auth/register",
            headers={"Origin": "https://evil.example"},
            json=payload,
        ).status_code
        == 403
    )


def test_database_failure_returns_503_and_rolls_back_user(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_commit = db.commit

    def unavailable_commit() -> None:
        raise OperationalError("COMMIT", {}, Exception("database unavailable"))

    monkeypatch.setattr(db, "commit", unavailable_commit)
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:5173"},
        json={"email": "rollback@example.com", "password": "long password"},
    )
    monkeypatch.setattr(db, "commit", original_commit)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["detail"]["retryable"] is True
    assert response.json()["detail"]["request_id"]
    assert db.scalar(select(User).where(User.email == "rollback@example.com")) is None


def test_production_cookie_uses_host_security_prefix(
    db: Session,
    test_settings: Settings,
) -> None:
    production_settings = test_settings.model_copy(
        update={
            "app_env": "production",
            "frontend_origin": "https://fitician.example",
            "cookie_secure": True,
            "session_cookie_name": "__Host-fitician_session",
        }
    )
    app = create_app(production_settings)

    def override_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, base_url="https://testserver") as secure_client:
        response = secure_client.post(
            "/api/v1/auth/register",
            headers={"Origin": "https://fitician.example"},
            json={"email": "secure@example.com", "password": "long password"},
        )

    cookie = response.headers["set-cookie"]
    assert response.status_code == 201
    assert cookie.startswith("__Host-fitician_session=")
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert "Domain=" not in cookie
