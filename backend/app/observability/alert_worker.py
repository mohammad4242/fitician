"""Independent bounded alert dispatcher. Provider outages never enter a user request."""

from __future__ import annotations

import importlib
import logging
from datetime import UTC, datetime
from threading import Event

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.session import get_engine
from app.jobs.heartbeat import threaded_heartbeat
from app.jobs.runtime import install_sync_signal_handlers

from .alert_delivery import (
    claim_alert,
    claim_receipt,
    complete_alert,
    enqueue_alerts,
    record_receipt,
)
from .alert_sms import FarazAlertSms
from .sentry import flush_sentry, initialize_sentry

logger = logging.getLogger(__name__)


def run_iteration(settings: Settings, provider: FarazAlertSms) -> None:
    engine = get_engine(settings)
    with Session(engine) as db:
        enqueue_alerts(db, settings, now=datetime.now(UTC))
        job = claim_alert(db, settings, now=datetime.now(UTC))
        db.commit()  # Commit the exclusive attempt before any billable provider operation.
    if job:
        result = provider.send(job["text"])
        with Session(engine) as db:
            complete_alert(db, job["attempt_id"], result, now=datetime.now(UTC))
            db.commit()
    with Session(engine) as db:
        receipt_id = claim_receipt(db, now=datetime.now(UTC))
        db.commit()
    if receipt_id:
        observed = provider.reconcile(receipt_id)
        with Session(engine) as db:
            record_receipt(db, receipt_id, observed, now=datetime.now(UTC))
            db.commit()


def main() -> None:
    settings = get_settings()
    if not settings.diagnostics_alert_enabled or not settings.diagnostics_alert_enabled_at:
        raise SystemExit("Diagnostic alerts need explicit enablement and activation time")
    initialize_sentry("diagnostics-alert-worker")
    # Load the application's complete ORM registry, without starting its HTTP lifespan.
    importlib.import_module("app.main")
    stop = Event()
    restore = install_sync_signal_handlers(stop)
    try:
        with (
            httpx.Client(trust_env=False, follow_redirects=False) as client,
            threaded_heartbeat(
                settings.job_heartbeat_path,
                service="diagnostics-alert-worker",
                interval_seconds=settings.job_heartbeat_interval_seconds,
            ),
        ):
            provider = FarazAlertSms(settings, client)
            while not stop.is_set():
                try:
                    run_iteration(settings, provider)
                except Exception:
                    # Never log provider payload, recipient, credentials or an exception body.
                    logger.warning("Diagnostic alert iteration unavailable")
                stop.wait(5)
    finally:
        restore()
        flush_sentry()


if __name__ == "__main__":
    main()
