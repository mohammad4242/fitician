"""Bounded exact-event polling: no broad log export and no webhook authority."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .diagnostics_models import DiagnosticEvent
from .evidence_models import DiagnosticExternalEvent, DiagnosticExternalIssueLink


class SyncFailure(Exception):
    def __init__(self, code: str, retry_after: int = 0) -> None:
        self.retry_after = retry_after
        self.code = code
        super().__init__(code)


def fetch_event(
    client: httpx.Client, organization: str, project: str, event_id: str
) -> dict[str, Any]:
    if not all(
        re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) for value in (organization, project)
    ) or not re.fullmatch(r"[a-f0-9]{32}", event_id):
        raise SyncFailure("invalid_target")
    # Host is fixed; neither logs nor issue content may supply a destination URL.
    url = f"https://sentry.io/api/0/projects/{organization}/{project}/events/{event_id}/"
    with client.stream("GET", url, follow_redirects=False, timeout=10) as response:
        if response.status_code == 429:
            raw_retry = response.headers.get("Retry-After", "60")
            retry = min(86400, max(1, int(raw_retry))) if raw_retry.isdigit() else 60
            raise SyncFailure("rate_limited", retry)
        if response.status_code == 404:
            raise SyncFailure("pending_ingestion")
        if response.status_code != 200:
            raise SyncFailure("upstream_rejected")
        content = bytearray()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            if len(content) > 1_048_576:
                raise SyncFailure("response_too_large")
        result = json.loads(content)
        if not isinstance(result, dict):
            raise SyncFailure("invalid_response")
        return result


def synchronize_one(
    db: Session, client: httpx.Client, organization: str, project: str, environment: str
) -> bool:
    now = datetime.now(UTC)
    row = db.scalar(
        select(DiagnosticExternalEvent)
        .where(
            DiagnosticExternalEvent.project_id == project,
            DiagnosticExternalEvent.environment == environment,
            DiagnosticExternalEvent.sync_state.in_(["pending", "retrying", "syncing"]),
            DiagnosticExternalEvent.attempts < 12,
            or_(
                DiagnosticExternalEvent.next_attempt_at.is_(None),
                DiagnosticExternalEvent.next_attempt_at <= now,
            ),
        )
        .order_by(DiagnosticExternalEvent.updated_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if row is None:
        return False
    row_id = row.id
    token = uuid4()
    row.lease_token = token
    row.sync_state = "syncing"
    row.attempts += 1
    row.next_attempt_at = now + timedelta(seconds=60)
    event_id = row.external_event_id
    db.commit()  # No DB lock/transaction spans the external request.
    retry_after = 0
    try:
        remote = fetch_event(client, organization, project, event_id)
        tags = {
            item.get("key"): item.get("value")
            for item in remote.get("tags", [])
            if isinstance(item, dict)
        }
        if (
            str(remote.get("eventID", remote.get("id", ""))) != event_id
            or tags.get("environment") != environment
            or tags.get("diagnostic_event_id") != str(row.local_event_id)
        ):
            raise SyncFailure("scope_mismatch")
        external_issue_id = str(remote.get("groupID", ""))
        if not re.fullmatch(r"[0-9]{1,100}", external_issue_id):
            raise SyncFailure("pending_grouping")
        failure = None
    except (SyncFailure, httpx.HTTPError, ValueError) as error:
        failure = error.code if isinstance(error, SyncFailure) else "transport_failed"
        retry_after = error.retry_after if isinstance(error, SyncFailure) else 0
        external_issue_id = ""
    row = db.scalar(
        select(DiagnosticExternalEvent)
        .where(DiagnosticExternalEvent.id == row_id)
        .with_for_update()
    )
    if row is None or row.lease_token != token:
        db.rollback()
        return True
    if failure:
        row.sync_state = "exhausted" if row.attempts >= 12 else "retrying"
        row.next_attempt_at = now + timedelta(
            seconds=max(retry_after, min(3600, 30 * 2**row.attempts))
        )
    else:
        row.external_issue_id = external_issue_id
        row.sync_state = "observed"
        row.observed_at = datetime.now(UTC)
        event = db.get(DiagnosticEvent, row.local_event_id) if row.local_event_id else None
        if event is not None and event.issue_id is not None:
            db.execute(
                insert(DiagnosticExternalIssueLink)
                .values(
                    issue_id=event.issue_id,
                    project_id=project,
                    external_issue_id=external_issue_id,
                    environment=environment,
                )
                .on_conflict_do_nothing(
                    index_elements=["issue_id", "project_id", "external_issue_id", "environment"]
                )
            )
    row.last_error_code = failure
    row.lease_token = None
    db.commit()
    return True


def main() -> None:
    from pathlib import Path
    from threading import Event

    from app.config import get_settings
    from app.database.session import get_engine
    from app.jobs.heartbeat import threaded_heartbeat
    from app.jobs.runtime import install_sync_signal_handlers
    from app.observability.sentry import initialize_sentry

    initialize_sentry("diagnostics-sync-worker")
    stop = Event()
    restore = install_sync_signal_handlers(stop)
    settings = get_settings()
    organization = os.environ.get("SENTRY_ORG", "")
    project = os.environ.get("SENTRY_PROJECT", "")
    environment = os.environ.get("SENTRY_ENVIRONMENT", "development")
    api_token = os.environ.get("SENTRY_API_TOKEN", "")
    if not all((organization, project, api_token)):
        raise SystemExit("Sentry synchronization is not configured")
    try:
        with (
            threaded_heartbeat(
                Path(os.environ.get("JOB_HEARTBEAT_PATH", "/run/fitician/heartbeat.json")),
                service="diagnostics-sync-worker",
                interval_seconds=5,
            ),
            httpx.Client(
                headers={"Authorization": f"Bearer {api_token}"}, trust_env=False
            ) as client,
        ):
            while not stop.is_set():
                try:
                    with Session(get_engine(settings)) as db:
                        worked = synchronize_one(db, client, organization, project, environment)
                except Exception:
                    worked = False
                stop.wait(1 if worked else 10)
    finally:
        restore()


if __name__ == "__main__":
    main()
