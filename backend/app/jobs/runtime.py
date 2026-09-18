from __future__ import annotations

import asyncio
import signal
import threading
from collections.abc import Awaitable, Callable
from contextlib import suppress
from types import FrameType
from typing import Any, cast


def install_async_signal_handlers(stop_event: asyncio.Event) -> None:
    """Wake an async worker when the container asks it to stop.

    Tests and non-main-thread callers can safely use this helper: unsupported
    signal registration is ignored and the event remains usable explicitly.
    """

    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        stop_event.set()

    for signal_name in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError, RuntimeError, ValueError):
            loop.add_signal_handler(signal_name, request_stop)


def install_sync_signal_handlers(stop_event: threading.Event) -> Callable[[], None]:
    """Install signal handlers for a synchronous worker and return cleanup."""

    previous: dict[signal.Signals, object] = {}

    def request_stop(_signum: int, _frame: FrameType | None) -> None:
        stop_event.set()

    for signal_name in (signal.SIGINT, signal.SIGTERM):
        with suppress(OSError, RuntimeError, ValueError):
            previous[signal_name] = signal.getsignal(signal_name)
            signal.signal(signal_name, request_stop)

    def restore() -> None:
        for signal_name, handler in previous.items():
            with suppress(OSError, RuntimeError, ValueError):
                signal.signal(signal_name, cast(signal.Handlers, handler))

    return restore


async def wait_for_stop(stop_event: asyncio.Event, timeout_seconds: float) -> bool:
    """Wait for stop or timeout; return whether shutdown was requested."""

    try:
        await asyncio.wait_for(stop_event.wait(), timeout=timeout_seconds)
    except TimeoutError:
        return False
    return True


async def cancel_tasks(tasks: list[asyncio.Task[Any]]) -> None:
    """Cancel and drain tasks without hiding their cancellation."""

    for task in tasks:
        task.cancel()
    if tasks:
        with suppress(asyncio.CancelledError):
            await asyncio.gather(*tasks)


async def run_until_stopped(
    stop_event: asyncio.Event,
    operation: Callable[[], Awaitable[None]],
    poll_seconds: float,
) -> None:
    """Run a polling operation until a shutdown event is set."""

    while not stop_event.is_set():
        await operation()
        if await wait_for_stop(stop_event, poll_seconds):
            break
