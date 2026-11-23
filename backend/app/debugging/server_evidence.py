"""Passive, selected-occurrence server evidence. No shell, active probes or raw payloads."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.observability.diagnostics_models import DiagnosticEvent, DiagnosticIssue
from app.observability.environment import diagnostics_environment

from .connectors import _authorize_run
from .models import DebugRun, DebugRunEvent, DebugThread
from .privacy import sanitize_payload
from .service import append_event

TOOL = "fitician_server_evidence"
PROVENANCE = "server_observation"


def _value(value: Any) -> Any:
    if isinstance(value, (UUID, datetime)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _job(db: Session, occurrence: DiagnosticEvent) -> list[dict[str, Any]]:
    if occurrence.resource_id is None:
        return []
    if occurrence.operation.startswith("body_analysis"):
        from app.body_analysis.models import BodyAnalysis as Job

        statement = select(
            Job.id,
            Job.status,
            Job.attempt_count,
            Job.available_at,
            Job.locked_at,
            Job.started_at,
            Job.completed_at,
            Job.updated_at,
            Job.error_code,
            Job.provider_request_id,
            Job.model_id,
        ).where(Job.id == occurrence.resource_id)
        kind = "body_analysis"
    elif occurrence.operation.startswith("food_photo"):
        from app.nutrition.models import NutritionFoodPhotoAnalysisJob as FoodJob

        statement = select(
            FoodJob.id,
            FoodJob.status,
            FoodJob.attempt_count,
            FoodJob.max_attempts,
            FoodJob.available_at,
            FoodJob.locked_at,
            FoodJob.started_at,
            FoodJob.completed_at,
            FoodJob.last_error_code,
        ).where(
            or_(FoodJob.id == occurrence.resource_id, FoodJob.estimate_id == occurrence.resource_id)
        )
        kind = "food_photo"
    else:
        return []
    # Select only these columns: never load photo paths, forms, results or error messages.
    row = db.execute(statement).mappings().first()
    return (
        [{"kind": kind, "source": "current_job_columns", **{k: _value(v) for k, v in row.items()}}]
        if row
        else []
    )


def _observations(db: Session, occurrence: DiagnosticEvent) -> list[dict[str, Any]]:
    identity = (
        [DiagnosticEvent.resource_id == occurrence.resource_id] if occurrence.resource_id else []
    )
    for name in ("trace_id", "operation_id", "request_id"):
        if value := getattr(occurrence, name):
            identity.append(getattr(DiagnosticEvent, name) == value)
    scope = DiagnosticEvent.id == occurrence.id
    if identity:
        scope = or_(
            scope,
            and_(
                or_(
                    DiagnosticEvent.issue_id == occurrence.issue_id,
                    DiagnosticEvent.issue_id.is_(None),
                ),
                or_(*identity),
            ),
        )
    columns = [
        getattr(DiagnosticEvent, key)
        for key in (
            "id",
            "timestamp",
            "component",
            "operation",
            "stage",
            "outcome",
            "error_code",
            "build",
            "request_id",
            "operation_id",
            "trace_id",
            "span_id",
            "parent_span_id",
            "resource_id",
            "retry_count",
            "http_status",
            "dropped_count",
            "expected_span_count",
        )
    ]
    rows = db.execute(
        select(*columns)
        .where(
            scope,
            DiagnosticEvent.timestamp >= occurrence.timestamp - timedelta(minutes=15),
            DiagnosticEvent.timestamp <= occurrence.timestamp + timedelta(minutes=15),
        )
        .order_by(DiagnosticEvent.timestamp.desc(), DiagnosticEvent.id.desc())
        .limit(20)
    ).mappings()
    return [{k: _value(v) for k, v in row.items()} for row in rows]


def _infrastructure(db: Session, now: datetime) -> list[dict[str, Any]]:
    rows = db.execute(
        select(
            DiagnosticEvent.id,
            DiagnosticEvent.component,
            DiagnosticEvent.timestamp,
            DiagnosticEvent.outcome,
            DiagnosticEvent.error_code,
        )
        .where(
            DiagnosticEvent.platform == "infrastructure",
            DiagnosticEvent.operation == "infrastructure_probe",
            DiagnosticEvent.timestamp >= now - timedelta(days=1),
            DiagnosticEvent.component.in_(
                (
                    "api",
                    "database",
                    "redis",
                    "ai_agent",
                    "regional_connectivity",
                    "workers",
                    "media_storage",
                    "diagnostics",
                )
            ),
        )
        .distinct(DiagnosticEvent.component)
        .order_by(
            DiagnosticEvent.component,
            DiagnosticEvent.timestamp.desc(),
            DiagnosticEvent.id.desc(),
        )
        .limit(8)
    ).mappings()
    return [
        {
            "event_id": str(row["id"]),
            "component": row["component"],
            "observed_at": row["timestamp"].isoformat(),
            "outcome": row["outcome"],
            "error_code": row["error_code"],
            "current_status": "not_verified",
            "stale": (now - row["timestamp"]).total_seconds() > 120,
            "source": "recorded_infrastructure_probe",
        }
        for row in rows
    ]


def collect(
    db: Session,
    run_id: UUID,
    key: str,
    *,
    process_role: Literal["api", "debug_worker"],
    call_id: UUID | None = None,
    required_lease: UUID | None = None,
) -> dict[str, str]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key):
        raise ValueError("invalid_evidence_key")
    run = db.scalar(select(DebugRun).where(DebugRun.id == run_id).with_for_update())
    if run is None:
        raise ValueError("run_not_found")
    if required_lease is not None and run.lease_token != required_lease:
        raise ValueError("run_lease_lost")
    _authorize_run(db, run)
    identity = f"{call_id}:{key}" if call_id else key
    previous = db.scalar(
        select(DebugRunEvent).where(
            DebugRunEvent.run_id == run.id,
            DebugRunEvent.kind == "tool_completed",
            DebugRunEvent.payload["server_evidence_key"].as_string() == identity,
        )
    )
    if previous:
        return {"evidence_id": str(previous.id), "output": str(previous.payload["output"])}
    thread = db.get(DebugThread, run.thread_id)
    occurrence_id = run.evidence.get("occurrence_id")
    occurrence = db.get(DiagnosticEvent, UUID(occurrence_id)) if occurrence_id else None
    if thread is None or occurrence is None or occurrence.issue_id != thread.issue_id:
        raise ValueError("occurrence_not_found")
    issue = db.get(DiagnosticIssue, thread.issue_id)
    assert issue is not None
    now = datetime.now(UTC)
    commit = os.environ.get("APP_BUILD_SHA", "")
    packet = {
        "schema_version": 1,
        "captured_at": now.isoformat(),
        "environment": diagnostics_environment(),
        "collected_by": process_role,
        "issue_id": str(thread.issue_id),
        "occurrence_id": str(occurrence.id),
        "occurrence_timestamp": occurrence.timestamp.isoformat(),
        "occurrence_release": occurrence.build,
        "release": {
            "reported_commit": commit if re.fullmatch(r"[a-f0-9]{40}", commit) else None,
            "image_digest": None,
            "verification": "process_environment_only",
        },
        "configuration_presence": {
            "sentry_dsn": bool(os.environ.get("SENTRY_DSN")),
            "sentry_sync_credential": bool(os.environ.get("SENTRY_API_TOKEN")),
        },
        "impact": {
            "issue_occurrences": issue.count,
            "known_user_count": db.scalar(
                select(func.count(func.distinct(DiagnosticEvent.user_id))).where(
                    DiagnosticEvent.issue_id == issue.id
                )
            )
            or 0,
        },
        "jobs": _job(db, occurrence),
        "observations": _observations(db, occurrence),
        "infrastructure": _infrastructure(db, now),
        "business_outcome_verified": False,
        "missing": ["host_container_inspection", "raw_service_logs_not_enrolled"],
        "limitations": [
            "Current job state is not historical state at the failure.",
            "Recorded probes do not verify current health or a business outcome.",
            "HTTP acceptance is not background completion.",
            "Diagnostic observations may be sampled or incomplete.",
        ],
    }
    safe = sanitize_payload(packet)
    output = json.dumps(safe, ensure_ascii=False, sort_keys=True)
    if len(output.encode()) > 28000:
        raise ValueError("server_evidence_too_large")
    event = append_event(
        db,
        run,
        "tool_completed",
        {
            "tool": TOOL,
            "provenance": PROVENANCE,
            "server_evidence_key": identity,
            "output": output,
            "evidence_version": hashlib.sha256(output.encode()).hexdigest(),
        },
    )
    return {"evidence_id": str(event.id), "output": output}
