from __future__ import annotations

import asyncio

from sqlalchemy import create_engine

from app.config import Settings
from app.scheduler import worker


def test_scheduler_runs_periodic_loops_once_in_dedicated_process(
    monkeypatch,
) -> None:
    started: list[str] = []

    async def fake_sync(*args, **kwargs) -> None:
        return None

    async def fake_price(*args, **kwargs) -> None:
        started.append("price")

    async def fake_retention(*args, **kwargs) -> None:
        started.append("retention")

    async def fake_account(*args, **kwargs) -> None:
        started.append("account")

    monkeypatch.setattr(worker, "sync_agent_service_proxy", fake_sync)
    monkeypatch.setattr(worker, "scheduler_loop", fake_price)
    monkeypatch.setattr(worker, "retention_scheduler_loop", fake_retention)
    monkeypatch.setattr(worker, "account_deletion_scheduler_loop", fake_account)
    monkeypatch.setattr(worker, "get_engine", lambda _url: create_engine("sqlite://"))

    settings = Settings(
        database_url="sqlite://",
        app_env="test",
        account_deletion_enabled=True,
        _env_file=None,
    )
    asyncio.run(worker.run_scheduler(settings))

    assert started == ["price", "retention", "account"]
