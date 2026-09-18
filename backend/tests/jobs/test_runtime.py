from __future__ import annotations

import asyncio
import signal
import threading

import pytest

from app.jobs.runtime import (
    cancel_tasks,
    install_async_signal_handlers,
    install_sync_signal_handlers,
    run_until_stopped,
    wait_for_stop,
)


def test_wait_for_stop_returns_false_after_poll_interval() -> None:
    async def exercise() -> bool:
        return await wait_for_stop(asyncio.Event(), 0.001)

    assert asyncio.run(exercise()) is False


def test_run_until_stopped_does_not_start_another_iteration_after_stop() -> None:
    async def exercise() -> int:
        stop_event = asyncio.Event()
        calls = 0

        async def operation() -> None:
            nonlocal calls
            calls += 1
            stop_event.set()

        await run_until_stopped(stop_event, operation, 0.001)
        return calls

    assert asyncio.run(exercise()) == 1


def test_async_signal_handler_sets_stop_event(monkeypatch: pytest.MonkeyPatch) -> None:
    async def exercise() -> bool:
        stop_event = asyncio.Event()
        callbacks: dict[signal.Signals, object] = {}
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(
            loop,
            "add_signal_handler",
            lambda signal_name, callback: callbacks.__setitem__(signal_name, callback),
        )

        install_async_signal_handlers(stop_event)

        callback = callbacks[signal.SIGTERM]
        assert callable(callback)
        callback()
        return stop_event.is_set()

    assert asyncio.run(exercise()) is True


def test_sync_signal_handler_sets_stop_event(monkeypatch: pytest.MonkeyPatch) -> None:
    stop_event = threading.Event()
    handlers: dict[signal.Signals, object] = {}
    monkeypatch.setattr(
        signal,
        "signal",
        lambda signal_name, handler: handlers.__setitem__(signal_name, handler),
    )

    restore = install_sync_signal_handlers(stop_event)

    handler = handlers[signal.SIGTERM]
    assert callable(handler)
    handler(signal.SIGTERM, None)
    assert stop_event.is_set()
    restore()


def test_cancel_tasks_drains_pending_tasks() -> None:
    async def exercise() -> bool:
        started = asyncio.Event()

        async def pending() -> None:
            started.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(pending())
        await started.wait()
        await cancel_tasks([task])
        return task.cancelled()

    assert asyncio.run(exercise()) is True
