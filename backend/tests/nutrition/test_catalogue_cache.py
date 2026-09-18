from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.cache.service import CacheResult
from app.nutrition.router import _invalidate_nutrition_cache
from app.profile.enums import ProductMode
from app.profile.models import UserProfile
from tests.nutrition.test_meal_catalogue import _add_required_imported_foods

ORIGIN = {"Origin": "http://localhost:5173"}


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


def _register(
    client: TestClient,
    db: Session,
    email: str,
    *,
    mode: ProductMode | None = None,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": "long password"},
    )
    assert response.status_code == 201
    if mode is not None:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        db.add(UserProfile(user_id=user.id, product_mode=mode))
        db.commit()


def test_verified_foods_use_global_cache(client: TestClient, db: Session) -> None:
    _register(client, db, "nutrition-food-cache@example.com")
    cache = RecordingCache()
    client.app.state.cache = cache

    first = client.get("/api/v1/nutrition/foods")
    second = client.get("/api/v1/nutrition/foods")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(cache.calls) == 2
    assert cache.calls[0][0] == "nutrition_foods"
    assert cache.calls[0][2] == 300


def test_member_food_catalogue_cache_identity_contains_filters(
    client: TestClient, db: Session
) -> None:
    _register(client, db, "nutrition-food-page-cache@example.com", mode=ProductMode.NUTRITION)
    cache = RecordingCache()
    client.app.state.cache = cache

    first = client.get(
        "/api/v1/nutrition/food-catalogue",
        params={"q": "Rice", "category": "grains", "page": 1, "page_size": 12},
    )
    second = client.get(
        "/api/v1/nutrition/food-catalogue",
        params={"q": "Rice", "category": "grains", "page": 1, "page_size": 12},
    )

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(cache.calls) == 2
    assert cache.calls[0][0] == "nutrition_food_catalogue"
    assert cache.calls[0][1]["q"] == "Rice"


def test_member_meal_catalogue_uses_verified_global_cache(client: TestClient, db: Session) -> None:
    from app.nutrition.food_catalogue import seed_base_iranian_food_catalogue
    from app.nutrition.meal_catalogue import seed_meal_catalogue

    seed_base_iranian_food_catalogue(db)
    _add_required_imported_foods(db)
    seed_meal_catalogue(db)
    _register(client, db, "nutrition-meal-cache@example.com")
    cache = RecordingCache()
    client.app.state.cache = cache

    first = client.get("/api/v1/nutrition/meal-catalogue", params={"category": "breakfast"})
    second = client.get("/api/v1/nutrition/meal-catalogue", params={"category": "breakfast"})

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(cache.calls) == 2
    assert cache.calls[0][0] == "nutrition_meals"
    assert cache.calls[0][1]["visibility"] == "verified"


def test_nutrition_catalogue_invalidation_is_best_effort() -> None:
    cache = RecordingCache()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(cache=cache)))

    asyncio.run(
        _invalidate_nutrition_cache(
            request,
            "nutrition_foods",
            "nutrition_food_catalogue",
            "nutrition_meals",
        )
    )

    assert cache.invalidations == [
        "nutrition_foods",
        "nutrition_food_catalogue",
        "nutrition_meals",
    ]


def test_admin_food_retirement_invalidates_member_catalogue_caches(
    client: TestClient, db: Session
) -> None:
    _register(client, db, "nutrition-food-invalidation@example.com")
    user = db.scalar(
        select(User).where(User.email == "nutrition-food-invalidation@example.com")
    )
    assert user is not None
    user.is_admin = True
    db.commit()
    cache = RecordingCache()
    client.app.state.cache = cache

    response = client.delete(
        "/api/v1/nutrition/admin/foods/chicken-breast",
        headers=ORIGIN,
    )

    assert response.status_code == 204
    assert cache.invalidations == [
        "nutrition_foods",
        "nutrition_food_catalogue",
        "nutrition_meals",
    ]
