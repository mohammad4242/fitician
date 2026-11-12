"""Evidence package construction never includes request bodies or exception messages."""

from __future__ import annotations

import hashlib
import json
import os
import re
import traceback
from typing import Any
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.observability.environment import diagnostics_environment

from .diagnostics_models import DiagnosticEvent
from .diagnostics_schemas import EventInput
from .evidence_models import DiagnosticEvidenceSnapshot, DiagnosticExternalEvent


def exception_evidence(error: BaseException) -> dict[str, Any]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen and len(chain) < 16:
        seen.add(id(current))
        chain.append(current)
        current = current.__cause__ or (
            None if current.__suppress_context__ else current.__context__
        )
    values = []
    for item in reversed(chain):
        frames = []
        for frame in traceback.extract_tb(item.__traceback__)[-100:]:
            match = re.search(r"(?:^|/)(app/[^?#]+)$", frame.filename.replace("\\", "/"))
            safe: dict[str, Any] = {
                "function": re.sub(r"[^A-Za-z0-9_.$<>-]", "_", frame.name)[:160],
                "lineno": max(1, frame.lineno or 1),
            }
            if (
                match
                and re.fullmatch(r"app/[A-Za-z0-9_./-]+", match[1])
                and ".." not in match[1].split("/")
            ):
                safe["filename"] = match[1][:240]
            frames.append(safe)
        values.append(
            {"type": re.sub(r"[^A-Za-z0-9_.]", "_", type(item).__name__)[:100], "frames": frames}
        )
    return {"values": values}


def persist_evidence(
    db: Session,
    event: DiagnosticEvent,
    evidence: dict[str, Any],
    sentry_event_id: str | None,
    *,
    project: str | None = None,
    provenance: str = "local_exception",
) -> None:
    if event.issue_id is None:
        return
    payload = {
        "schema_version": 1,
        "provenance": provenance,
        "event_id": str(event.id),
        "issue_id": str(event.issue_id),
        "release_commit": event.build,
        "exception": evidence,
        "request_id": event.request_id,
        "operation_id": event.operation_id,
        "trace_id": event.trace_id,
        "resource_id": str(event.resource_id) if event.resource_id else None,
        "attempt": event.retry_count,
        "stage": event.stage,
        "component": event.component,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    project = project or os.environ.get("SENTRY_PROJECT", "")
    environment = diagnostics_environment()
    if sentry_event_id and re.fullmatch(r"[a-z0-9_-]{1,100}", project):
        db.execute(
            insert(DiagnosticExternalEvent)
            .values(
                project_id=project,
                external_event_id=sentry_event_id,
                local_event_id=event.id,
                environment=environment,
                sync_state="pending",
            )
            .on_conflict_do_nothing(index_elements=["project_id", "external_event_id"])
        )
    db.execute(
        insert(DiagnosticEvidenceSnapshot)
        .values(
            event_id=event.id,
            issue_id=event.issue_id,
            evidence_version=digest,
            redaction_version="allowlist-v1",
            payload=payload,
            sentry_event_id=sentry_event_id,
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
    )


def evidence_package(
    db: Session, issue_id: UUID, occurrence_id: UUID | None = None
) -> dict[str, Any]:
    from sqlalchemy import select

    statement = select(DiagnosticEvidenceSnapshot).where(
        DiagnosticEvidenceSnapshot.issue_id == issue_id
    )
    if occurrence_id is not None:
        statement = statement.where(DiagnosticEvidenceSnapshot.event_id == occurrence_id)
    snapshot = db.scalar(statement.order_by(DiagnosticEvidenceSnapshot.created_at.desc()).limit(1))
    if snapshot is None:
        return {
            "issue_id": str(issue_id),
            "snapshot": None,
            "missing": ["exception_stack"],
            "provenance": "unavailable",
        }
    external = db.scalar(
        select(DiagnosticExternalEvent)
        .where(
            DiagnosticExternalEvent.local_event_id == snapshot.event_id,
            DiagnosticExternalEvent.external_event_id == snapshot.sentry_event_id,
        )
        .limit(1)
    )
    org = os.environ.get("SENTRY_ORG", "")
    issue_url = (
        f"https://{org}.sentry.io/issues/{external.external_issue_id}/"
        if external
        and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", org)
        and re.fullmatch(r"[0-9]{1,30}", external.external_issue_id or "")
        else None
    )
    return {
        "external_issue_url": issue_url,
        "external_source": external.source_evidence if external else None,
        "sync_state": external.sync_state if external else "not_configured",
        "external_issue_id": external.external_issue_id if external else None,
        "last_sync_at": external.updated_at.isoformat() if external else None,
        "sync_error": external.last_error_code if external else None,
        "issue_id": str(issue_id),
        "evidence_id": str(snapshot.id),
        "evidence_version": hashlib.sha256(
            (
                snapshot.evidence_version
                + json.dumps(external.source_evidence if external else None, sort_keys=True)
            ).encode()
        ).hexdigest(),
        "snapshot": snapshot.payload,
        "sentry_event_id": snapshot.sentry_event_id,
        "delivery": "observed"
        if external and external.observed_at
        else "unconfirmed"
        if snapshot.sentry_event_id
        else "unknown",
        "created_at": snapshot.created_at.isoformat(),
        "missing": []
        if snapshot.payload.get("exception", {}).get("values")
        or (external and external.source_evidence)
        else ["exception_stack"],
    }


def attach_exception(event: EventInput, error: BaseException) -> EventInput:
    """Capture externally before any diagnostics DB write, while keeping local evidence."""
    from uuid import uuid4

    from .diagnostics_schemas import ExceptionEvidence
    from .diagnostics_service import _EXPECTED_CATEGORIES
    from .sentry import capture_operational_exception

    if event.category in _EXPECTED_CATEGORIES or event.severity not in {"error", "critical"}:
        return event
    event_id = event.event_id or uuid4()
    sentry_id = capture_operational_exception(error, str(event_id))
    return event.model_copy(
        update={
            "event_id": event_id,
            "sentry_event_id": sentry_id,
            "exception_evidence": ExceptionEvidence.model_validate(exception_evidence(error)),
        }
    )
