from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

from app.jobs import heartbeat


def test_heartbeat_probe_rejects_stale_or_wrong_service(tmp_path: Path) -> None:
    path = tmp_path / "heartbeat.json"
    heartbeat.write_heartbeat(path, service="body-analysis-worker")

    assert heartbeat.heartbeat_is_healthy(
        path,
        max_age_seconds=10,
        expected_service="body-analysis-worker",
    )
    assert not heartbeat.heartbeat_is_healthy(
        path,
        max_age_seconds=10,
        expected_service="scheduler",
    )

    stale = time.time() - 20
    os.utime(path, (stale, stale))
    assert not heartbeat.heartbeat_is_healthy(
        path,
        max_age_seconds=10,
        expected_service="body-analysis-worker",
    )


def test_async_heartbeat_runs_on_the_worker_event_loop(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def exercise() -> None:
        writes = 0
        second_write = asyncio.Event()
        real_write = heartbeat.write_heartbeat

        def observe(path: Path, *, service: str) -> None:
            nonlocal writes
            writes += 1
            real_write(path, service=service)
            if writes >= 2:
                second_write.set()

        monkeypatch.setattr(heartbeat, "write_heartbeat", observe)
        path = tmp_path / "async.json"
        async with heartbeat.async_heartbeat(
            path,
            service="scheduler",
            interval_seconds=0.01,
        ):
            await asyncio.wait_for(second_write.wait(), timeout=1)

        payload = json.loads(path.read_text())
        assert payload["service"] == "scheduler"
        assert writes >= 2

    asyncio.run(exercise())


def test_threaded_heartbeat_continues_while_worker_is_blocked(
    tmp_path: Path,
    monkeypatch,
) -> None:
    writes = 0
    real_write = heartbeat.write_heartbeat

    def observe(path: Path, *, service: str) -> None:
        nonlocal writes
        writes += 1
        real_write(path, service=service)

    monkeypatch.setattr(heartbeat, "write_heartbeat", observe)
    path = tmp_path / "thread.json"
    with heartbeat.threaded_heartbeat(
        path,
        service="notification-worker",
        interval_seconds=0.01,
    ):
        deadline = time.monotonic() + 1
        while writes < 2 and time.monotonic() < deadline:
            time.sleep(0.005)

    assert writes >= 2
