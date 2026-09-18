from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import Any

from app.admin.router import _invalidate_exercise_cache
from app.cache.service import CacheResult
from app.exercises.enums import MediaPresentation
from tests.exercises.test_exercise_api import prepare_catalog


class RecordingCache:
    def __init__(self) -> None:
        self.entries: dict[str, object] = {}
        self.calls: list[tuple[str, object, int | None]] = []
        self.invalidations: list[str] = []

    async def get_or_load(
        self,
        namespace: str,
        identity: object,
        loader: Callable[[], object | Awaitable[object]],
        *,
        ttl_seconds: int | None = None,
        **_: Any,
    ) -> CacheResult[object]:
        key = repr((namespace, identity))
        self.calls.append((namespace, identity, ttl_seconds))
        if key in self.entries:
            return CacheResult(self.entries[key], True, True, ttl_seconds or 0)
        value = loader()
        if inspect.isawaitable(value):
            value = await value
        self.entries[key] = value
        return CacheResult(value, False, True, ttl_seconds or 0)

    async def invalidate(self, namespace: str) -> bool:
        self.invalidations.append(namespace)
        self.entries.clear()
        return True


def test_public_exercise_list_uses_global_cache(client: Any, db: Any) -> None:
    prepare_catalog(client, db, email="exercise-cache-list@example.com")
    cache = RecordingCache()
    client.app.state.cache = cache

    first = client.get("/api/v1/exercises?page_size=5")
    second = client.get("/api/v1/exercises?page_size=5")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(cache.calls) == 2
    assert cache.calls[0][0] == "exercises"
    assert cache.calls[0][2] == 300


def test_public_exercise_detail_cache_separates_media_presentation(client: Any, db: Any) -> None:
    prepare_catalog(client, db, email="exercise-cache-detail@example.com")
    cache = RecordingCache()
    client.app.state.cache = cache

    male = client.get(
        "/api/v1/exercises/dumbbell-bench-press",
        params={"presentation": MediaPresentation.MALE.value},
    )
    female = client.get(
        "/api/v1/exercises/dumbbell-bench-press",
        params={"presentation": MediaPresentation.FEMALE.value},
    )

    assert male.status_code == female.status_code == 200
    assert len(cache.calls) == 2
    assert cache.calls[0][0] == cache.calls[1][0] == "exercises"
    assert cache.calls[0][1] != cache.calls[1][1]
    assert cache.calls[0][2] == cache.calls[1][2] == 600


def test_exercise_mutation_invalidation_is_best_effort() -> None:
    cache = RecordingCache()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(cache=cache)))

    import asyncio

    asyncio.run(_invalidate_exercise_cache(request))

    assert cache.invalidations == ["exercises"]
