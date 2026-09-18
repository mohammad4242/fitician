from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

_SAFE_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_FIXED_WINDOW_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""


class RedisRateLimitUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Redis rate limiter unavailable")


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    count: int
    retry_after_seconds: int


class RedisRateLimiter:
    """Atomic fixed-window limiter backed by the process Redis client."""

    def __init__(self, redis_service: Any, *, key_secret: str) -> None:
        if not key_secret:
            raise ValueError("Rate-limit key secret must not be empty")
        self._redis = redis_service.client
        self._key_secret = key_secret.encode("utf-8")

    async def consume(
        self,
        *,
        namespace: str,
        actor: str,
        operation: str,
        limit: int,
        window_seconds: int,
        now: datetime | None = None,
    ) -> RateLimitResult:
        if limit < 1 or window_seconds < 1:
            raise ValueError("Rate-limit limit and window must be positive")
        _validate_segment(namespace)
        _validate_segment(operation)
        current = now or datetime.now(UTC)
        epoch = int(current.timestamp())
        window_epoch = epoch - (epoch % window_seconds)
        remaining = max(1, window_epoch + window_seconds - epoch)
        actor_hash = hmac.new(
            self._key_secret,
            f"{namespace}|{operation}|{actor}".encode(),
            hashlib.sha256,
        ).hexdigest()
        key = f"fitician:rate:v1:{namespace}:{operation}:{actor_hash}:{window_epoch}"
        try:
            raw_result = await self._redis.eval(
                _FIXED_WINDOW_SCRIPT,
                1,
                key,
                str(remaining),
            )
            count, ttl = _parse_result(raw_result)
        except Exception:
            raise RedisRateLimitUnavailable from None
        retry_after = max(1, ttl) if count > limit else 0
        return RateLimitResult(count <= limit, count, retry_after)


def _validate_segment(value: str) -> None:
    if not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError("Invalid rate-limit key segment")


def _parse_result(raw_result: object) -> tuple[int, int]:
    if not isinstance(raw_result, (list, tuple)) or len(raw_result) < 2:
        raise ValueError("Invalid Redis rate-limit response")
    return int(raw_result[0]), int(raw_result[1])
