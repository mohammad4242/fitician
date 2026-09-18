from __future__ import annotations

import inspect
import time
from dataclasses import dataclass

import redis.asyncio as redis_async

from app.config import Settings


@dataclass(frozen=True, slots=True)
class RedisPingResult:
    available: bool
    latency_ms: float | None
    error: str | None = None


class RedisService:
    """Own one bounded async Redis client for the lifetime of one API process."""

    def __init__(self, settings: Settings) -> None:
        password = (
            settings.redis_password.get_secret_value()
            if settings.redis_password is not None
            else None
        )
        self._client = redis_async.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=password,
            max_connections=settings.redis_max_connections,
            socket_connect_timeout=settings.redis_connect_timeout_seconds,
            socket_timeout=settings.redis_socket_timeout_seconds,
            health_check_interval=settings.redis_health_check_interval_seconds,
            decode_responses=False,
        )
        self._closed = False
        self._endpoint = f"{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"

    @property
    def client(self) -> redis_async.Redis:
        return self._client

    async def ping(self) -> RedisPingResult:
        if getattr(self, "_closed", False):
            return RedisPingResult(False, None, "RedisClosed")
        started = time.perf_counter()
        try:
            await self._client.ping()
        except Exception as error:  # noqa: BLE001 - diagnostics must never break the API
            return RedisPingResult(False, None, type(error).__name__)
        return RedisPingResult(True, (time.perf_counter() - started) * 1000)

    async def close(self) -> None:
        if getattr(self, "_closed", False):
            return
        self._closed = True
        close = getattr(self._client, "aclose", None)
        if close is None:
            close = getattr(self._client, "close", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    def __repr__(self) -> str:
        return f"RedisService(endpoint={getattr(self, '_endpoint', 'unknown')!r})"


def create_redis_service(settings: Settings) -> RedisService:
    return RedisService(settings)
