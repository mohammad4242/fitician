from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.account_deletion.scheduler import account_deletion_scheduler_loop
from app.body_analysis.admin_config.crypto import CredentialEncryptionError
from app.body_analysis.admin_config.service import sync_agent_service_proxy
from app.config import Settings, get_settings
from app.database.session import get_engine
from app.nutrition.price_scheduler import scheduler_loop
from app.nutrition.retention_scheduler import retention_scheduler_loop

logger = logging.getLogger(__name__)


async def run_scheduler(settings: Settings) -> None:
    """Run all periodic loops in one independently deployable process."""
    agent_timeout = httpx.Timeout(settings.agent_service_connect_timeout_seconds)
    food_price_timeout = httpx.Timeout(settings.food_price_provider_timeout_seconds)
    async with (
        httpx.AsyncClient(timeout=agent_timeout, trust_env=False) as agent_client,
        httpx.AsyncClient(timeout=food_price_timeout, trust_env=False) as food_price_client,
    ):
        try:
            with Session(get_engine(settings.database_url)) as db:
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
                )
            ),
            asyncio.create_task(retention_scheduler_loop(settings)),
        ]
        if settings.account_deletion_enabled:
            loops.append(asyncio.create_task(account_deletion_scheduler_loop(settings)))
        try:
            await asyncio.gather(*loops)
        finally:
            for task in loops:
                task.cancel()
            with suppress(asyncio.CancelledError):
                await asyncio.gather(*loops)


if __name__ == "__main__":
    asyncio.run(run_scheduler(get_settings()))
