"""Bounded native SDK discovery in the existing sync worker, never a remote issue mirror."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .diagnostics_schemas import EventInput
from .diagnostics_service import record_event
from .environment import diagnostics_environment
from .evidence import persist_evidence
from .evidence_models import (
    DiagnosticDiscoveryCursor,
    DiagnosticExternalEvent,
    DiagnosticExternalIssueLink,
)
from .sentry_sync import SyncFailure, sanitize_remote_evidence

_FATAL_TYPES = {"SIGSEGV", "SIGABRT", "SIGBUS", "SIGILL", "SIGFPE", "EXC_BAD_ACCESS", "EXC_CRASH"}


def fetch_native_page(
    client: httpx.Client,
    organization: str,
    project: str,
    environment: str,
    start: datetime,
    end: datetime,
    cursor: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    if not all(re.fullmatch(r"[A-Za-z0-9_-]{1,100}", v) for v in (organization, project)):
        raise SyncFailure("invalid_target")
    hosts = {"global": "sentry.io", "us": "us.sentry.io", "de": "de.sentry.io"}
    host = hosts.get(os.environ.get("SENTRY_API_REGION", "global"))
    if not host:
        raise SyncFailure("invalid_api_region")
    url = httpx.URL(f"https://{host}/api/0/projects/{organization}/{project}/events/")
    params = {
        "full": "true",
        "per_page": "10",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "environment": environment,
    }
    if cursor:
        if not re.fullmatch(r"[0-9:]{1,256}", cursor):
            raise SyncFailure("invalid_pagination")
        params["cursor"] = cursor
    with client.stream("GET", url, params=params, follow_redirects=False, timeout=10) as response:
        if response.status_code == 429:
            retry = response.headers.get("Retry-After", "60")
            raise SyncFailure(
                "rate_limited", min(86400, max(1, int(retry))) if retry.isdigit() else 60
            )
        if response.status_code != 200:
            raise SyncFailure("upstream_rejected")
        data = bytearray()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > 2_097_152:
                raise SyncFailure("response_too_large")
        page = json.loads(data)
        if (
            not isinstance(page, list)
            or len(page) > 10
            or not all(isinstance(v, dict) for v in page)
        ):
            raise SyncFailure("invalid_response")
        next_link = response.links.get("next")
        next_cursor = None
        if next_link and next_link.get("results") == "true":
            target = httpx.URL(next_link.get("url", ""))
            next_cursor = target.params.get("cursor")
            if (
                target.scheme != "https"
                or target.host != host
                or target.port not in {None, 443}
                or target.path != url.path
                or target.username
                or target.password
                or not next_cursor
                or not re.fullmatch(r"[0-9:]{1,256}", next_cursor)
                or next_cursor == cursor
            ):
                raise SyncFailure("invalid_pagination")
        # Never follow the returned URL; only use its bounded cursor with the fixed endpoint.
        return page, next_cursor


def import_native_event(
    db: Session,
    remote: dict[str, Any],
    organization: str,
    project: str,
    environment: str,
    start: datetime,
    end: datetime,
) -> bool:
    raw_tags = remote.get("tags")
    if not isinstance(raw_tags, list):
        return False
    tags = {
        v["key"]: v["value"]
        for v in raw_tags[:128]
        if isinstance(v, dict) and isinstance(v.get("key"), str) and isinstance(v.get("value"), str)
    }
    event_id = str(remote.get("eventID", ""))
    group = str(remote.get("groupID") or "")
    if (
        remote.get("platform") != "native"
        or tags.get("environment") != environment
        or "diagnostic_event_id" in tags
        or tags.get("level") not in {"error", "fatal"}
        or not re.fullmatch(r"[a-f0-9]{32}", event_id)
        or (bool(group) and not re.fullmatch(r"[0-9]{1,30}", group))
    ):
        return False
    try:
        occurred = datetime.fromisoformat(str(remote.get("dateCreated", "")).replace("Z", "+00:00"))
        if occurred.tzinfo is None or not start <= occurred <= end:
            return False
    except ValueError:
        return False
    safe = sanitize_remote_evidence(remote, expected_commit=None)
    values = safe["exceptions"]
    native = next((v for v in values if v["type"] in _FATAL_TYPES), None)
    if native is None:
        return False
    local_id = uuid5(
        NAMESPACE_URL, f"fitician:sentry-native:{organization}:{project}:{environment}:{event_id}"
    )
    claimed = db.scalar(
        insert(DiagnosticExternalEvent)
        .values(
            project_id=project,
            external_event_id=event_id,
            environment=environment,
            sync_state="observed" if group else "pending",
            observed_at=datetime.now(UTC),
            external_issue_id=group or None,
        )
        .on_conflict_do_nothing(index_elements=["project_id", "external_event_id"])
        .returning(DiagnosticExternalEvent.id)
    )
    if claimed is None:
        return False
    contexts = remote.get("contexts")
    os_context = contexts.get("os") if isinstance(contexts, dict) else None
    os_name = os_context.get("name") if isinstance(os_context, dict) else None
    platform = {"Android": "android", "iOS": "ios"}.get(str(os_name), "unknown")
    source = next((f for f in native["frames"] if f.get("filename") and f.get("lineno")), None)
    event = record_event(
        db,
        EventInput(
            event_id=local_id,
            component="mobile_native",
            operation="application_runtime",
            stage="native_crash",
            platform=platform,
            category="application_bug",
            severity="critical",
            error_code="NATIVE_CRASH",
            exception_type=native["type"],
            outcome="failure",
            build=safe["release_commit"],
            source_location=f"{source['filename']}:{source['lineno']}" if source else None,
        ),
        occurred_at=occurred,
    )
    persist_evidence(
        db, event, {"values": values}, event_id, project=project, provenance="sentry_native_capture"
    )
    row = db.get(DiagnosticExternalEvent, claimed)
    assert row is not None
    row.local_event_id = event.id
    safe["release_match"] = True if event.build else None
    row.source_evidence = safe
    if group:
        db.execute(
            insert(DiagnosticExternalIssueLink)
            .values(
                issue_id=event.issue_id,
                project_id=project,
                external_issue_id=group,
                environment=environment,
            )
            .on_conflict_do_nothing(
                index_elements=["issue_id", "project_id", "external_issue_id", "environment"]
            )
        )
    return True


def discover_native_page(
    db: Session,
    client: httpx.Client,
    organization: str,
    project: str,
    environment: str,
) -> bool:
    if environment != diagnostics_environment():
        raise SyncFailure("scope_mismatch")
    now = datetime.now(UTC)
    db.execute(
        insert(DiagnosticDiscoveryCursor)
        .values(
            organization=organization,
            project_id=project,
            environment=environment,
            next_attempt_at=now,
        )
        .on_conflict_do_nothing(index_elements=["organization", "project_id", "environment"])
    )
    state = db.scalar(
        select(DiagnosticDiscoveryCursor)
        .where(
            DiagnosticDiscoveryCursor.organization == organization,
            DiagnosticDiscoveryCursor.project_id == project,
            DiagnosticDiscoveryCursor.environment == environment,
            DiagnosticDiscoveryCursor.next_attempt_at <= now,
        )
        .with_for_update(skip_locked=True)
    )
    if state is None:
        db.rollback()
        return False
    if state.scan_start is None or state.scan_end is None:
        state.scan_start = (
            (state.watermark - timedelta(minutes=2))
            if state.watermark
            else now - timedelta(hours=24)
        )
        state.scan_end = now
    token, identity = uuid4(), state.id
    state.lease_token = token
    state.next_attempt_at = now + timedelta(seconds=60)
    start, end, cursor = state.scan_start, state.scan_end, state.cursor
    db.commit()  # Persist fencing and progress before I/O; never keep a DB lock across HTTP.
    try:
        page, next_cursor = fetch_native_page(
            client, organization, project, environment, start, end, cursor
        )
        failure = None
        retry_after = 0
    except (SyncFailure, httpx.HTTPError, ValueError) as error:
        page, next_cursor = [], cursor
        failure = error.code if isinstance(error, SyncFailure) else "transport_failed"
        retry_after = error.retry_after if isinstance(error, SyncFailure) else 0
    state = db.scalar(
        select(DiagnosticDiscoveryCursor)
        .where(
            DiagnosticDiscoveryCursor.id == identity,
        )
        .with_for_update()
    )
    if state is None or state.lease_token != token:
        db.rollback()
        return True
    if failure:
        state.failures = min(12, state.failures + 1)
        state.next_attempt_at = now + timedelta(
            seconds=max(retry_after, min(3600, 30 * 2**state.failures))
        )
    else:
        for remote in page:
            state.imported_count += int(
                import_native_event(db, remote, organization, project, environment, start, end)
            )
        state.cursor = next_cursor
        state.last_success_at = now
        state.failures = 0
        state.next_attempt_at = now + timedelta(seconds=15 if next_cursor else 60)
        if next_cursor is None:
            state.watermark = end
            state.scan_start = state.scan_end = None
    state.last_error_code = failure
    state.lease_token = None
    db.commit()  # Occurrences and the page cursor advance atomically.
    return True
