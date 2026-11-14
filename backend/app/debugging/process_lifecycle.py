"""Dedicated private telemetry and bounded signal shutdown for isolated services."""

from __future__ import annotations

import asyncio
import os
import re
import signal
from collections.abc import Coroutine
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .connector import read_private_configuration


def initialize_telemetry(path: Path, service: str) -> str:
    if not path.exists():
        return "disabled"
    try:
        value = read_private_configuration(path)
        if set(value) != {"dsn", "environment"}:
            raise ValueError
        dsn, environment = value["dsn"], value["environment"]
        if not isinstance(dsn, str) or not isinstance(environment, str):
            raise ValueError
        target = urlsplit(dsn)
        if (
            target.scheme != "https"
            or not target.hostname
            or not target.hostname.endswith(".sentry.io")
            or not target.username
            or target.password
            or target.port not in {None, 443}
            or target.query
            or target.fragment
            or not re.fullmatch(r"/[0-9]+", target.path)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", environment)
        ):
            raise ValueError
        from app.observability.sentry import initialize_sentry

        os.environ["SENTRY_DSN"] = dsn
        os.environ["DIAGNOSTICS_ENVIRONMENT"] = environment
        os.environ["APP_BUILD_SHA"] = os.environ.get("FITICIAN_RUNTIME_COMMIT", "")
        return (
            "initialized"
            if initialize_sentry(service, http_server=False)
            else "initialization_failed"
        )
    except (OSError, ValueError, KeyError, TypeError):
        return "configuration_rejected"


async def serve_until_stopped(service: Coroutine[Any, Any, None]) -> None:
    from app.observability.sentry import flush_sentry

    task = asyncio.create_task(service)
    loop = asyncio.get_running_loop()
    for event in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(event, task.cancel)
    try:
        await task
    except asyncio.CancelledError:
        pass
    finally:
        for event in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(event)
        # Existing SDK policy bounds its queue flush to two seconds, even during an outage.
        await asyncio.to_thread(flush_sentry)
