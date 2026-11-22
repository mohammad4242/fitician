"""Opt-in lightweight remote model dispatch in the existing Iran scheduler; no local model loop."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from sqlalchemy.orm import Session

from app.config import Settings
from app.database.session import get_engine
from app.jobs.heartbeat import async_heartbeat

from .service import claim_run
from .worker import execute_run

logger = logging.getLogger(__name__)


async def wait_for_stop(stop_event: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def remote_dispatch_loop(settings: Settings, *, stop_event: asyncio.Event) -> None:
    settings = settings.model_copy(
        update={
            "db_pool_size": 1,
            "db_max_overflow": 0,
            "db_pool_timeout_seconds": 1.0,
            "db_statement_timeout_ms": 2000,
        }
    )
    path = settings.job_heartbeat_path.with_name("debug-dispatch.json")
    while not stop_event.is_set():
        try:
            async with async_heartbeat(path, service="debug-dispatch", interval_seconds=5):
                while not stop_event.is_set():
                    with Session(get_engine(settings)) as db:
                        # Both complete model turns execute on the explicit remote target.
                        # No provider credential or model/tool loop runs in this scheduler.
                        run = claim_run(db)
                        identity = (run.id, run.lease_token) if run else None
                        db.commit()
                    if identity and identity[1]:
                        # Exactly one remote run per loop; existing durable call journal,
                        # timeout, revocation and cancellation checks remain authoritative.
                        await execute_run(settings, identity[0], identity[1])
                    else:
                        await wait_for_stop(stop_event, 2)
        except Exception:
            with suppress(OSError):
                path.unlink(missing_ok=True)
            logger.warning("Remote debug dispatch unavailable")
            await wait_for_stop(stop_event, 10)
        finally:
            # A stopped dispatcher must not retain a fresh-looking role heartbeat.
            with suppress(OSError):
                path.unlink(missing_ok=True)
