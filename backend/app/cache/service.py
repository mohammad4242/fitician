from __future__ import annotations

import asyncio
import inspect
import json
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from app.config import Settings

from .keys import cache_key, generation_key

T = TypeVar("T")
Loader = Callable[[], T | Awaitable[T]]
Serializer = Callable[[T], object]
Deserializer = Callable[[object], T]

_MISSING = object()
_RELEASE_LOCK_SCRIPT = """-- compare-and-delete
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


@dataclass(frozen=True, slots=True)
class CacheResult[T]:
    value: T
    hit: bool
    redis_available: bool
    ttl_seconds: int


class CacheService:
    def __init__(self, redis_service: Any, settings: Settings, metrics: Any | None = None) -> None:
        self._redis = redis_service.client
        self._metrics = metrics
        self._default_ttl_seconds = settings.cache_default_ttl_seconds
        self._lock_ttl_seconds = settings.cache_lock_ttl_seconds
        self._lock_wait_seconds = settings.cache_lock_wait_ms / 1000

    async def get_or_load(
        self,
        namespace: str,
        identity: object,
        loader: Loader[T],
        *,
        ttl_seconds: int | None = None,
        serialize: Serializer[T] | None = None,
        deserialize: Deserializer[T] | None = None,
    ) -> CacheResult[T]:
        ttl = ttl_seconds or self._default_ttl_seconds
        if ttl <= 0:
            raise ValueError("Cache TTL must be positive")
        encode = serialize or cast(Serializer[T], _identity)
        decode = deserialize or cast(Deserializer[T], _identity)

        generation, redis_available = await self._generation(namespace)
        key = cache_key(namespace, identity, generation=generation)
        cached = await self._get_decoded(key, decode)
        if cached is not _MISSING:
            self._record_cache(namespace, hit=True, redis_available=redis_available)
            return CacheResult(cast(T, cached), True, redis_available, ttl)

        lock_key = f"{key}:lock"
        owner = secrets.token_urlsafe(18)
        acquired = await self._acquire_lock(lock_key, owner)
        if acquired is True:
            try:
                value = await _resolve(loader)
                await self.set_raw(key, encode(value), ttl_seconds=ttl)
                self._record_cache(namespace, hit=False, redis_available=redis_available)
                return CacheResult(value, False, redis_available, ttl)
            finally:
                await self.release_lock(lock_key, owner)
        if acquired is None:
            value = await _resolve(loader)
            self._record_cache(namespace, hit=False, redis_available=False)
            return CacheResult(value, False, False, ttl)

        await asyncio.sleep(self._lock_wait_seconds)
        cached_after_wait = await self._get_decoded(key, decode)
        if cached_after_wait is not _MISSING:
            self._record_cache(namespace, hit=True, redis_available=True)
            return CacheResult(cast(T, cached_after_wait), True, True, ttl)
        value = await _resolve(loader)
        await self.set_raw(key, encode(value), ttl_seconds=ttl)
        self._record_cache(namespace, hit=False, redis_available=True)
        return CacheResult(value, False, True, ttl)

    def _record_cache(self, namespace: str, *, hit: bool, redis_available: bool) -> None:
        recorder = getattr(self._metrics, "record_cache", None)
        if recorder is not None:
            recorder(namespace=namespace, hit=hit, redis_available=redis_available)

    async def set_raw(self, key: str, value: object, *, ttl_seconds: int) -> bool:
        try:
            encoded = json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            result = await self._redis.set(key, encoded, ex=ttl_seconds)
            return bool(result)
        except Exception:  # noqa: BLE001 - cache failure must not break the request
            return False

    async def invalidate(self, namespace: str) -> bool:
        try:
            await self._redis.incr(generation_key(namespace))
            return True
        except Exception:  # noqa: BLE001 - cache failure must not break mutations
            return False

    async def release_lock(self, key: str, owner: str) -> bool:
        try:
            result = await self._redis.eval(_RELEASE_LOCK_SCRIPT, 1, key, owner)
            return bool(result)
        except Exception:  # noqa: BLE001 - best-effort cleanup
            return False

    async def _generation(self, namespace: str) -> tuple[int, bool]:
        try:
            value = await self._redis.get(generation_key(namespace))
            if value is None:
                return 0, True
            return int(value), True
        except Exception:  # noqa: BLE001 - Redis is an optional dependency
            return 0, False

    async def _get_decoded(
        self,
        key: str,
        deserialize: Deserializer[T],
    ) -> object:
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return _MISSING
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return deserialize(json.loads(raw))
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
            await self._delete(key)
            return _MISSING
        except Exception:  # noqa: BLE001 - Redis is an optional dependency
            return _MISSING

    async def _acquire_lock(self, key: str, owner: str) -> bool | None:
        try:
            result = await self._redis.set(
                key,
                owner.encode("utf-8"),
                ex=self._lock_ttl_seconds,
                nx=True,
            )
            return bool(result)
        except Exception:  # noqa: BLE001 - caller falls back to the loader
            return None

    async def _delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception:  # noqa: BLE001 - best effort only
            pass


async def _resolve[T](loader: Loader[T]) -> T:
    value = loader()
    if inspect.isawaitable(value):
        return await value
    return value


def _identity[T](value: T) -> T:
    return value
