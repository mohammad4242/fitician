from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.rate_limiter import RateLimitResult, RedisRateLimitUnavailable
from app.rate_limits.dependency import (
    DistributedRateLimitUnavailable,
    enforce_distributed_rate_limit,
)
from app.rate_limits.service import (
    DistributedRateLimitExceeded,
    consume_rate_limit,
    hash_actor,
)


def test_actor_hash_is_keyed_and_does_not_contain_raw_actor() -> None:
    actor = "ip:203.0.113.10"
    hashed = hash_actor(actor, "secret")

    assert hashed != actor
    assert len(hashed) == 64
    assert hash_actor(actor, "secret") == hashed
    assert hash_actor(actor, "other-secret") != hashed


def test_postgres_fallback_enforces_window_limit(db) -> None:
    for _ in range(2):
        consume_rate_limit(
            db,
            namespace="application",
            actor="user:member-1",
            operation="body_analysis",
            limit=2,
            window_seconds=3600,
            hmac_secret="test-secret",
        )

    with pytest.raises(DistributedRateLimitExceeded) as error:
        consume_rate_limit(
            db,
            namespace="application",
            actor="user:member-1",
            operation="body_analysis",
            limit=2,
            window_seconds=3600,
            hmac_secret="test-secret",
        )

    assert error.value.retry_after_seconds > 0


def test_postgres_fallback_keeps_operations_and_actors_separate(db) -> None:
    consume_rate_limit(
        db,
        namespace="application",
        actor="user:member-1",
        operation="body_analysis",
        limit=1,
        window_seconds=3600,
        hmac_secret="test-secret",
    )
    consume_rate_limit(
        db,
        namespace="application",
        actor="user:member-1",
        operation="workout_generation",
        limit=1,
        window_seconds=3600,
        hmac_secret="test-secret",
    )
    consume_rate_limit(
        db,
        namespace="application",
        actor="user:member-2",
        operation="body_analysis",
        limit=1,
        window_seconds=3600,
        hmac_secret="test-secret",
    )


def test_distributed_dependency_uses_both_ip_and_user_actors() -> None:
    calls: list[str] = []

    class Limiter:
        async def consume(self, **kwargs):
            calls.append(kwargs["actor"])
            return RateLimitResult(True, 1, 0)

    request = SimpleNamespace(
        client=SimpleNamespace(host="198.51.100.20"),
        app=SimpleNamespace(state=SimpleNamespace(rate_limiter=Limiter())),
    )

    async def exercise() -> None:
        await enforce_distributed_rate_limit(
            request,
            object(),
            SimpleNamespace(),
            namespace="application",
            operation="body_analysis",
            limit=5,
            window_seconds=3600,
            user_id=uuid4(),
        )

    asyncio.run(exercise())

    assert calls[0] == "ip:198.51.100.20"
    assert calls[1].startswith("user:")


def test_distributed_dependency_fails_closed_when_both_backends_fail(monkeypatch) -> None:
    class Limiter:
        async def consume(self, **kwargs):
            raise RedisRateLimitUnavailable

    request = SimpleNamespace(
        client=SimpleNamespace(host="198.51.100.20"),
        app=SimpleNamespace(state=SimpleNamespace(rate_limiter=Limiter())),
    )

    def fail_engine(_settings):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr("app.rate_limits.dependency.get_engine", fail_engine)

    async def exercise() -> None:
        await enforce_distributed_rate_limit(
            request,
            object(),
            SimpleNamespace(phone_otp_hmac_secret=SimpleNamespace(get_secret_value=lambda: "x")),
            namespace="application",
            operation="body_analysis",
            limit=5,
            window_seconds=3600,
            user_id=uuid4(),
        )

    with pytest.raises(DistributedRateLimitUnavailable):
        asyncio.run(exercise())
