import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.config import Settings
from app.infrastructure.rate_limiter import RedisRateLimitUnavailable
from app.nutrition.router import _consume_nutrition_rate_limit


def test_nutrition_database_fallback_never_commits_request_session(
    monkeypatch: Any,
    test_settings: Settings,
) -> None:
    class UnavailableLimiter:
        async def consume(self, **_: object) -> None:
            raise RedisRateLimitUnavailable

    class RequestSession:
        def commit(self) -> None:
            raise AssertionError("request-owned session was committed")

        def rollback(self) -> None:
            raise AssertionError("request-owned session was rolled back")

    fallback_session = SimpleNamespace()

    @contextmanager
    def fallback_session_context(
        _: Settings, *, session_factory: object = None
    ) -> Iterator[SimpleNamespace]:
        yield fallback_session

    calls: list[object] = []
    monkeypatch.setattr("app.nutrition.router.isolated_session", fallback_session_context)
    monkeypatch.setattr(
        "app.nutrition.router.consume_rate_limit",
        lambda db, **_: calls.append(db),
    )
    state = SimpleNamespace(rate_limiter=UnavailableLimiter())
    request = SimpleNamespace(app=SimpleNamespace(state=state))

    asyncio.run(
        _consume_nutrition_rate_limit(
            request,  # type: ignore[arg-type]
            RequestSession(),  # type: ignore[arg-type]
            uuid4(),
            test_settings,
            operation="food_photo",
            limit=5,
        )
    )

    assert calls == [fallback_session]
