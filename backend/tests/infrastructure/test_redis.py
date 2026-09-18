from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.config import Settings
from app.infrastructure import redis as redis_module
from app.main import create_app


class StubRedisClient:
    def __init__(self, *, ping_error: Exception | None = None) -> None:
        self.ping_error = ping_error
        self.ping_calls = 0
        self.close_calls = 0

    async def ping(self) -> bool:
        self.ping_calls += 1
        if self.ping_error is not None:
            raise self.ping_error
        return True

    async def aclose(self) -> None:
        self.close_calls += 1


def test_redis_service_uses_bounded_pool_and_timeouts(monkeypatch: Any) -> None:
    captured: dict[str, object] = {}
    client = StubRedisClient()

    def build_client(**kwargs: object) -> StubRedisClient:
        captured.update(kwargs)
        return client

    monkeypatch.setattr(redis_module.redis_async, "Redis", build_client)
    settings = Settings(
        _env_file=None,
        redis_host="redis.internal",
        redis_port=6380,
        redis_db=3,
        redis_password="redis-secret",
        redis_max_connections=7,
        redis_connect_timeout_seconds=1.5,
        redis_socket_timeout_seconds=2.5,
        redis_health_check_interval_seconds=15,
    )

    service = redis_module.RedisService(settings)

    assert service.client is client
    assert captured == {
        "host": "redis.internal",
        "port": 6380,
        "db": 3,
        "password": "redis-secret",
        "max_connections": 7,
        "socket_connect_timeout": 1.5,
        "socket_timeout": 2.5,
        "health_check_interval": 15,
        "decode_responses": False,
    }
    assert "redis-secret" not in repr(service)


def test_redis_ping_is_diagnostic_and_redacts_provider_error() -> None:
    client = StubRedisClient(ping_error=RuntimeError("password=redis-secret host=redis.internal"))
    service = redis_module.RedisService.__new__(redis_module.RedisService)
    service._client = client

    result = __import__("asyncio").run(service.ping())

    assert result.available is False
    assert result.error == "RuntimeError"
    assert "redis-secret" not in repr(result)


def test_redis_service_closes_owned_client() -> None:
    client = StubRedisClient()
    service = redis_module.RedisService.__new__(redis_module.RedisService)
    service._client = client

    __import__("asyncio").run(service.close())
    __import__("asyncio").run(service.close())

    assert client.close_calls == 1


def test_api_health_remains_available_when_redis_is_unavailable(monkeypatch: Any) -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        cookie_secure=False,
        session_cookie_name="fitician_session",
    )
    service = redis_module.RedisService.__new__(redis_module.RedisService)
    service._client = StubRedisClient(ping_error=ConnectionError("redis unavailable"))
    monkeypatch.setattr("app.main.create_redis_service", lambda _: service)

    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/healthz")
        readiness = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert readiness.status_code == 200
    assert readiness.json()["checks"]["redis"] == "degraded"
    assert service._client.ping_calls == 1
    assert service._client.close_calls == 1
