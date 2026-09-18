from __future__ import annotations

import asyncio
import logging

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.account_deletion.scheduler import account_deletion_scheduler_loop
from app.body_analysis.admin_config.crypto import CredentialEncryptionError
from app.body_analysis.admin_config.service import sync_agent_service_proxy
from app.config import Settings, get_settings
from app.database.session import get_engine
from app.jobs.heartbeat import async_heartbeat
from app.jobs.runtime import cancel_tasks, install_async_signal_handlers
from app.nutrition.price_scheduler import scheduler_loop
from app.nutrition.retention_scheduler import retention_scheduler_loop
from app.observability.logging import configure_structured_logging

logger = logging.getLogger(__name__)


async def run_scheduler(
    settings: Settings,
    *,
    stop_event: asyncio.Event | None = None,
) -> None:
    configure_structured_logging()
    """Run all periodic loops in one independently deployable process."""
    requested_stop = stop_event or asyncio.Event()
    if stop_event is None:
        install_async_signal_handlers(requested_stop)
    agent_timeout = httpx.Timeout(settings.agent_service_connect_timeout_seconds)
    food_price_timeout = httpx.Timeout(settings.food_price_provider_timeout_seconds)
    async with (
        async_heartbeat(
            settings.job_heartbeat_path,
            service="scheduler",
            interval_seconds=settings.job_heartbeat_interval_seconds,
        ),
        httpx.AsyncClient(timeout=agent_timeout, trust_env=False) as agent_client,
        httpx.AsyncClient(timeout=food_price_timeout, trust_env=False) as food_price_client,
    ):
        try:
            with Session(get_engine(settings)) as db:
                await sync_agent_service_proxy(
                    db,
                    client=agent_client,
                    settings=settings,
                )
        except (CredentialEncryptionError, SQLAlchemyError) as error:
            logger.warning("Agent Service proxy scheduler startup sync failed: %s", error)

        loops: list[asyncio.Task[None]] = [
            asyncio.create_task(
                scheduler_loop(
                    settings,
                    food_price_client,
                    agent_http_client=agent_client,
                    stop_event=requested_stop,
                )
            ),
            asyncio.create_task(retention_scheduler_loop(settings, stop_event=requested_stop)),
        ]
        if settings.account_deletion_enabled:
            loops.append(
                asyncio.create_task(
                    account_deletion_scheduler_loop(settings, stop_event=requested_stop)
                )
            )
        try:
            await asyncio.gather(*loops)
        finally:
            await cancel_tasks(loops)


if __name__ == "__main__":
    asyncio.run(run_scheduler(get_settings()))
