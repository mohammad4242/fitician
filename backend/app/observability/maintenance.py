"""Opt-in, bounded Iran maintenance; no model, repository or shell execution here."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Mapping
from contextlib import ExitStack, suppress
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.session import get_engine
from app.jobs.heartbeat import write_heartbeat
from app.observability.environment import diagnostics_environment

from .alert_sms import FarazAlertSms
from .alert_worker import run_iteration
from .sentry_discovery import discover_native_page
from .sentry_sync import synchronize_one

logger = logging.getLogger(__name__)


class Maintenance:
    def __init__(self, settings: Settings, *, environ: Mapping[str, str] | None = None):
        self.settings = settings.model_copy(
            update={
                "db_pool_size": 1,
                "db_max_overflow": 0,
                "db_pool_timeout_seconds": 1.0,
                "db_statement_timeout_ms": 2000,
            }
        )
        self.environ = os.environ if environ is None else environ
        self.organization = self.environ.get("SENTRY_ORG", "")
        self.projects = list(
            dict.fromkeys(
                v
                for v in (
                    self.environ.get("SENTRY_PROJECT", ""),
                    self.environ.get("SENTRY_WEB_PROJECT", ""),
                    self.environ.get("SENTRY_MOBILE_PROJECT", ""),
                )
                if v
            )
        )
        self.states: dict[str, str] = {}
        self.due: dict[str, float] = {}
        self.index = 0
        self.stack = ExitStack()
        limits = httpx.Limits(max_connections=1, max_keepalive_connections=1)
        self.sync_client = self.stack.enter_context(
            httpx.Client(
                headers={"Authorization": "Bearer " + self.environ.get("SENTRY_API_TOKEN", "")},
                proxy=self.environ.get("SENTRY_HTTPS_PROXY") or None,
                limits=limits,
                trust_env=False,
                follow_redirects=False,
                timeout=10,
            )
        )
        # Never reuse the Sentry bearer/proxy client for FarazSMS.
        self.sms_client = self.stack.enter_context(
            httpx.Client(
                limits=limits,
                trust_env=False,
                follow_redirects=False,
                timeout=10,
            )
        )

    def __enter__(self) -> Maintenance:
        return self

    def __exit__(self, *args: Any) -> None:
        self.stack.close()

    def sync_once(self) -> None:
        mobile = self.environ.get("SENTRY_MOBILE_PROJECT", "")
        actions = [(project, False) for project in self.projects]
        if mobile:
            actions.append((mobile, True))
        project, discovery = actions[self.index % len(actions)]
        self.index += 1
        with Session(get_engine(self.settings)) as db:
            if discovery:
                discover_native_page(
                    db, self.sync_client, self.organization, project, diagnostics_environment()
                )
            else:
                synchronize_one(
                    db, self.sync_client, self.organization, project, diagnostics_environment()
                )

    def alert_once(self) -> None:
        run_iteration(self.settings, FarazAlertSms(self.settings, self.sms_client))

    def tick(self) -> None:
        for role, ready, action in [
            (
                "diagnostics-sync-worker",
                bool(self.organization and self.projects and self.environ.get("SENTRY_API_TOKEN")),
                self.sync_once,
            ),
            (
                "diagnostics-alert-worker",
                bool(
                    self.settings.diagnostics_alert_enabled
                    and self.settings.diagnostics_alert_enabled_at
                ),
                self.alert_once,
            ),
        ]:
            path = self.settings.job_heartbeat_path.with_name(role + ".json")
            if not ready:
                self.states[role] = (
                    "disabled"
                    if role.endswith("alert-worker") and not self.settings.diagnostics_alert_enabled
                    else "unconfigured"
                )
                continue
            if time.monotonic() < self.due.get(role, 0):
                continue
            try:
                action()
                write_heartbeat(path, service=role)
            except Exception:
                self.states[role] = "unavailable"
                with suppress(OSError):
                    path.unlink(missing_ok=True)
                # Fixed message, no SQL/provider exception text, no recursive error capture.
                logger.warning("Diagnostics maintenance role unavailable", extra={"service": role})
                self.due[role] = time.monotonic() + 10
            else:
                self.states[role] = "active"
                self.due[role] = time.monotonic() + 5


async def diagnostics_maintenance_loop(settings: Settings, *, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            with Maintenance(settings) as maintenance:
                while not stop_event.is_set():
                    # One bounded tick; wait for ambiguous SMS dispatch before cancelling.
                    task = asyncio.create_task(asyncio.to_thread(maintenance.tick))
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        await task
                        raise
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=1)
                    except TimeoutError:
                        pass
        except Exception:
            # Invalid external configuration must not stop existing business loops.
            logger.warning("Diagnostics maintenance configuration unavailable")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=10)
            except TimeoutError:
                pass
