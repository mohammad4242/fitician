from collections.abc import Iterator
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.models import AuthOperationRateLimit, AuthSession, EmailVerificationToken, User
from app.auth.security import hash_password, hash_rate_limit_actor
from app.config import Settings, get_settings
from app.database.session import get_db
from app.infrastructure.rate_limiter import RateLimitResult, RedisRateLimitUnavailable
from app.main import create_app

ORIGIN = {"Origin": "http://localhost:5173"}


@pytest.fixture
def durable_signup_limits(
    client: TestClient, db: Session, test_settings: Settings
) -> Iterator[Settings]:
    secret = str(uuid4())
    settings = test_settings.model_copy(update={"phone_otp_hmac_secret": SecretStr(secret)})
    app = cast(FastAPI, client.app)
    app.dependency_overrides[get_settings] = lambda: settings
    engine = db.get_bind().engine
    # Match production: limiter commits must outlive request transaction rollbacks.
    app.state.rate_limit_session_factory = lambda: Session(engine)
    try:
        yield settings
    finally:
        with Session(engine) as cleanup:
            actors = [
                hash_rate_limit_actor(actor, secret)
                for actor in (
                    "ip:testclient",
                    "email:member@example.com",
                    "email:first@example.com",
                    "email:second@example.com",
                )
            ]
            cleanup.execute(
                delete(AuthOperationRateLimit).where(AuthOperationRateLimit.actor_hash.in_(actors))
            )
            cleanup.commit()


@pytest.mark.parametrize("redis_down", [False, True])
def test_signup_ip_limit_is_shared_across_replicas_before_expensive_work(
    client: TestClient,
    db: Session,
    durable_signup_limits: Settings,
    monkeypatch: pytest.MonkeyPatch,
    redis_down: bool,
) -> None:
    settings = durable_signup_limits.model_copy(update={"auth_register_ip_limit": 1})
    app = cast(FastAPI, client.app)
    app.dependency_overrides[get_settings] = lambda: settings
    replica = create_app(settings)
    replica.dependency_overrides[get_db] = lambda: db
    replica.state.rate_limit_session_factory = app.state.rate_limit_session_factory
    if redis_down:
        app.state.rate_limiter = Mock(consume=AsyncMock(side_effect=RedisRateLimitUnavailable))
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={"email": "first@example.com", "password": "long password"},
        ).status_code
        == 201
    )
    hashing = Mock(wraps=hash_password)
    monkeypatch.setattr(service, "hash_password", hashing)
    with TestClient(replica) as second:
        replica.state.rate_limiter = (
            Mock(consume=AsyncMock(side_effect=RedisRateLimitUnavailable)) if redis_down else None
        )
        response = second.post(
            "/api/v1/auth/register",
            headers={**ORIGIN, "X-Forwarded-For": "192.0.2.100"},
            json={"email": "second@example.com", "password": "long password"},
        )
        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) > 0
        assert response.json()["detail"]["code"] == "AUTH_RATE_LIMITED"
        hashing.assert_not_called()
        assert replica.state.email_provider.verification_deliveries == []
    for model in (User, AuthSession, EmailVerificationToken):
        assert db.scalar(select(func.count()).select_from(model)) == 1


def test_signup_email_limit_normalizes_case_and_survives_duplicate_rollback(
    client: TestClient,
    db: Session,
    durable_signup_limits: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    durable_signup_limits.auth_register_ip_limit = 10
    durable_signup_limits.auth_register_identifier_limit = 2
    app = cast(FastAPI, client.app)
    for email, expected in (("member@example.com", 201), ("Member@Example.com", 409)):
        assert (
            client.post(
                "/api/v1/auth/register",
                headers=ORIGIN,
                json={"email": email, "password": "long password"},
            ).status_code
            == expected
        )
    hashing = Mock(wraps=hash_password)
    monkeypatch.setattr(service, "hash_password", hashing)
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "MEMBER@example.com", "password": "long password"},
    )
    assert response.status_code == 429
    hashing.assert_not_called()
    assert len(app.state.email_provider.verification_deliveries) == 1
    assert db.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize("backend", ["redis", "all-unavailable"])
def test_signup_limiter_denial_fails_closed_before_hashing_writes_or_delivery(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, backend: str
) -> None:
    app = cast(FastAPI, client.app)
    consume = AsyncMock(
        return_value=RateLimitResult(allowed=False, count=99, retry_after_seconds=17)
    )
    if backend == "all-unavailable":
        consume.side_effect = RedisRateLimitUnavailable
        monkeypatch.setattr(
            "app.auth.router.consume_auth_rate_limit", Mock(side_effect=SQLAlchemyError)
        )
    app.state.rate_limiter = Mock(consume=consume)
    hashing = Mock(wraps=hash_password)
    monkeypatch.setattr(service, "hash_password", hashing)
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "limited@example.com", "password": "long password"},
    )
    assert response.status_code == (503 if backend == "all-unavailable" else 429)
    if backend == "redis":
        assert response.headers["Retry-After"] == "17"
    hashing.assert_not_called()
    assert consume.await_args is not None
    assert consume.await_args.kwargs["namespace"] == "auth"
    assert app.state.email_provider.verification_deliveries == []
    for model in (User, AuthSession, EmailVerificationToken):
        assert db.scalar(select(func.count()).select_from(model)) == 0
