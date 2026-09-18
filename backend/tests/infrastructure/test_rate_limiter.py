from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from app.infrastructure.rate_limiter import (
    RedisRateLimiter,
    RedisRateLimitUnavailable,
)


class FakeRedis:
    def __init__(self, result: list[int] | None = None, error: Exception | None = None) -> None:
        self.result = result or [1, 60]
        self.error = error
        self.calls: list[tuple[str, int, str, list[object]]] = []

    async def eval(self, script: str, numkeys: int, key: str, *args: object) -> list[int]:
        if self.error is not None:
            raise self.error
        self.calls.append((script, numkeys, key, list(args)))
        return self.result


def _limiter(redis: FakeRedis) -> RedisRateLimiter:
    service = type("RedisServiceStub", (), {"client": redis})()
    return RedisRateLimiter(service, key_secret="rate-limit-test-secret")


def test_redis_rate_limiter_uses_hashed_fixed_window_key() -> None:
    redis = FakeRedis(result=[1, 123])
    limiter = _limiter(redis)
    now = datetime(2026, 9, 18, 12, 34, 56, tzinfo=UTC)

    result = asyncio.run(
        limiter.consume(
            namespace="auth",
            actor="email:user@example.com",
            operation="password",
            limit=5,
            window_seconds=3600,
            now=now,
        )
    )

    assert result.allowed is True
    assert result.count == 1
    assert result.retry_after_seconds == 0
    assert len(redis.calls) == 1
    script, numkeys, key, args = redis.calls[0]
    assert "INCR" in script
    assert numkeys == 1
    assert key.startswith("fitician:rate:v1:auth:password:")
    assert "user@example.com" not in key
    assert key.rsplit(":", 1)[-1].isdigit()
    assert 0 < int(args[0]) <= 3600


def test_redis_rate_limiter_returns_retry_after_when_limit_is_exceeded() -> None:
    redis = FakeRedis(result=[6, 42])
    limiter = _limiter(redis)

    result = asyncio.run(
        limiter.consume(
            namespace="nutrition",
            actor="user:123",
            operation="food-photo",
            limit=5,
            window_seconds=60,
            now=datetime(2026, 9, 18, 12, 34, 56, tzinfo=UTC),
        )
    )

    assert result.allowed is False
    assert result.count == 6
    assert result.retry_after_seconds == 42


def test_redis_rate_limiter_redacts_redis_failures() -> None:
    limiter = _limiter(FakeRedis(error=ConnectionError("redis-password=secret")))

    with pytest.raises(RedisRateLimitUnavailable) as error:
        asyncio.run(
            limiter.consume(
                namespace="auth",
                actor="ip:127.0.0.1",
                operation="password",
                limit=5,
                window_seconds=60,
            )
        )

    assert "secret" not in repr(error.value)
