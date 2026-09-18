from __future__ import annotations

import asyncio

from app.cache.keys import cache_key, generation_key
from app.cache.service import CacheService
from app.config import Settings


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.expirations: dict[str, int] = {}
        self.eval_calls: list[tuple[str, list[str], list[str]]] = []
        self.unavailable = False

    def _check(self) -> None:
        if self.unavailable:
            raise ConnectionError("redis unavailable")

    async def get(self, key: str) -> bytes | None:
        self._check()
        return self.values.get(key)

    async def set(
        self,
        key: str,
        value: bytes,
        *,
        ex: int,
        nx: bool = False,
    ) -> bool:
        self._check()
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.expirations[key] = ex
        return True

    async def incr(self, key: str) -> int:
        self._check()
        value = int(self.values.get(key, b"0")) + 1
        self.values[key] = str(value).encode()
        return value

    async def eval(self, script: str, numkeys: int, *keys_and_args: str) -> int:
        self._check()
        keys = list(keys_and_args[:numkeys])
        args = list(keys_and_args[numkeys:])
        self.eval_calls.append((script, keys, args))
        if self.values.get(keys[0]) == args[0].encode():
            del self.values[keys[0]]
            return 1
        return 0


class FakeRedisService:
    def __init__(self, client: FakeRedis) -> None:
        self.client = client


def _service(fake: FakeRedis) -> CacheService:
    settings = Settings(
        _env_file=None,
        cache_default_ttl_seconds=300,
        cache_lock_ttl_seconds=5,
        cache_lock_wait_ms=1,
    )
    return CacheService(FakeRedisService(fake), settings)  # type: ignore[arg-type]


def test_cache_key_is_versioned_and_does_not_expose_identity() -> None:
    key = cache_key("exercise-list", {"page": 1, "search": "bench"}, generation=4)

    assert key.startswith("fitician:cache:v1:exercise-list:g4:")
    assert "bench" not in key
    assert generation_key("exercise-list") == "fitician:cache:v1:exercise-list:generation"


def test_cache_miss_loads_once_then_hit_avoids_loader() -> None:
    fake = FakeRedis()
    service = _service(fake)
    calls = 0

    async def loader() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"items": ["bench"], "total": 1}

    first = asyncio.run(service.get_or_load("exercise-list", {"page": 1}, loader))
    second = asyncio.run(service.get_or_load("exercise-list", {"page": 1}, loader))

    assert first.value == second.value == {"items": ["bench"], "total": 1}
    assert first.hit is False
    assert second.hit is True
    assert calls == 1
    assert first.ttl_seconds == 300


def test_namespace_invalidation_changes_key_without_scanning() -> None:
    fake = FakeRedis()
    service = _service(fake)

    old_key = cache_key("exercise-list", {"page": 1}, generation=0)
    asyncio.run(service.set_raw(old_key, {"value": "old"}, ttl_seconds=300))
    assert asyncio.run(service.invalidate("exercise-list")) is True

    calls = 0

    async def loader() -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"value": "new"}

    result = asyncio.run(service.get_or_load("exercise-list", {"page": 1}, loader))

    assert result.value == {"value": "new"}
    assert result.hit is False
    assert calls == 1
    assert old_key in fake.values


def test_corrupt_json_is_discarded_and_reloaded() -> None:
    fake = FakeRedis()
    service = _service(fake)
    key = cache_key("exercise-list", {"page": 1}, generation=0)
    fake.values[key] = b"not-json"
    calls = 0

    async def loader() -> dict[str, bool]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    result = asyncio.run(service.get_or_load("exercise-list", {"page": 1}, loader))

    assert result.value == {"ok": True}
    assert result.hit is False
    assert calls == 1


def test_redis_failure_falls_back_to_loader() -> None:
    fake = FakeRedis()
    fake.unavailable = True
    service = _service(fake)

    result = asyncio.run(
        service.get_or_load("exercise-list", {"page": 1}, lambda: {"ok": True})
    )

    assert result.value == {"ok": True}
    assert result.hit is False
    assert result.redis_available is False


def test_lock_release_uses_owner_token() -> None:
    fake = FakeRedis()
    service = _service(fake)
    fake.values["fitician:cache:v1:exercise-list:lock"] = b"owner"

    assert asyncio.run(service.release_lock("fitician:cache:v1:exercise-list:lock", "owner"))
    assert fake.eval_calls
    assert "compare-and-delete" in fake.eval_calls[0][0]
