"""Issue/occurrence-scoped read-only host jobs; never deployment or arbitrary shell authority."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.observability.diagnostics_models import DiagnosticEvent
from app.observability.environment import diagnostics_environment

from .automation import ACTIVE, leased_operation, operation_json
from .connectors import _authorize_run
from .models import DebugConnector, DebugOperation, DebugRun
from .service import append_event

WORKFLOW = "debug-server-observation.yml"


def queue_observation(db: Session, run_id: UUID, key: str, target: str) -> DebugOperation:
    if target not in {"production-iran", "production-germany"}:
        raise ValueError("observation_target_not_authorized")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key):
        raise ValueError("invalid_observation_request")
    run = db.scalar(select(DebugRun).where(DebugRun.id == run_id).with_for_update())
    if run is None:
        raise ValueError("run_not_found")
    _authorize_run(db, run)
    occurrence = (
        db.get(DiagnosticEvent, UUID(run.evidence["occurrence_id"]))
        if run.evidence.get("occurrence_id")
        else None
    )
    if occurrence is None:
        raise ValueError("occurrence_not_found")
    request = {
        "purpose": "server_observation",
        "target_environment": target,
        "trace_id": occurrence.trace_id
        if occurrence.trace_id and re.fullmatch("[a-f0-9]{32}", occurrence.trace_id)
        else None,
    }
    digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    existing = db.scalar(
        select(DebugOperation).where(
            DebugOperation.run_id == run.id, DebugOperation.submission_key == key
        )
    )
    if existing:
        if existing.request_hash != digest:
            raise ValueError("automation_idempotency_conflict")
        return existing
    worker_id = run.config_snapshot.get("automation_worker_id")
    worker = db.get(DebugConnector, UUID(worker_id)) if worker_id else None
    if (
        worker is None
        or worker.kind != "automation"
        or worker.revoked
        or worker.environment != diagnostics_environment()
    ):
        raise ValueError("automation_worker_not_configured")
    if (
        db.scalar(
            select(func.count())
            .select_from(DebugOperation)
            .where(
                DebugOperation.environment == worker.environment, DebugOperation.state.in_(ACTIVE)
            )
        )
        or 0
    ) >= 100:
        raise ValueError("automation_queue_capacity_reached")
    row = DebugOperation(
        run_id=run.id,
        worker_id=worker.id,
        occurrence_id=occurrence.id,
        environment=worker.environment,
        kind="observe",
        state="queued",
        submission_key=key,
        request_hash=digest,
        request=request,
        result={},
    )
    db.add(row)
    db.flush()
    append_event(
        db,
        run,
        "automation_queued",
        {
            "operation_id": str(row.id),
            "kind": "observe",
            "target_environment": target,
            "occurrence_id": str(occurrence.id),
        },
    )
    return row


def validate_observation(packet: Any, request: dict[str, Any]) -> dict[str, Any]:
    """Rebuild an allowlisted packet before persistence/model access; ignore free-text fields."""
    try:
        if (
            not isinstance(packet, dict)
            or len(json.dumps(packet).encode()) > 28000
            or packet["schema_version"] != 1
            or packet["target_environment"] != request["target_environment"]
            or packet["provenance"] != "fixed_read_only_host_collector"
            or packet["business_outcome_verified"] is not False
        ):
            raise ValueError
        captured = datetime.fromisoformat(packet["captured_at"])
        if captured.tzinfo is None or abs((datetime.now(UTC) - captured).total_seconds()) > 900:
            raise ValueError
        names = (
            {"agent-service"}
            if request["target_environment"] == "production-germany"
            else {
                "backend",
                "backend-2",
                "frontend",
                "db",
                "redis",
                "body-analysis-worker",
                "food-photo-worker",
                "notification-worker",
                "scheduler",
                "caddy",
            }
        )
        rows = packet["services"]
        allowed = names | (
            {"debug-worker", "diagnostics-sync-worker", "diagnostics-alert-worker"}
            if request["target_environment"] == "production-iran"
            else set()
        )
        if (
            not isinstance(rows, list)
            or not names <= {r["service"] for r in rows} <= allowed
            or len(rows) != len({r["service"] for r in rows})
        ):
            raise ValueError
        names = {r["service"] for r in rows}
        safe = []
        total_logs = 0
        for row in rows:
            value: dict[str, Any] = {"service": row["service"]}
            status = row["status"]
            if status not in {
                "created",
                "running",
                "restarting",
                "exited",
                "paused",
                "removing",
                "dead",
                "unavailable",
            }:
                raise ValueError
            value["status"] = status
            for key, pattern in {
                "container_id": "[a-f0-9]{64}",
                "image_id": "sha256:[a-f0-9]{64}",
                "commit": "[a-f0-9]{40}",
            }.items():
                item = row.get(key)
                if item is not None and (
                    not isinstance(item, str) or not re.fullmatch(pattern, item)
                ):
                    raise ValueError
                value[key] = item
            if row.get("health") not in {None, "healthy", "unhealthy", "starting"}:
                raise ValueError
            restart = row.get("restart_count", 0)
            if type(restart) is not int or not 0 <= restart <= 10**9:
                raise ValueError
            value.update(
                health=row.get("health"),
                restart_count=restart,
                release_provenance="image_label" if value["commit"] else "unknown",
            )
            logs = row.get("logs", [])
            if not isinstance(logs, list):
                raise ValueError
            total_logs += len(logs)
            if total_logs > 20 or (logs and request.get("trace_id") is None):
                raise ValueError
            value["logs"] = []
            for entry in logs:
                if (
                    not isinstance(entry, dict)
                    or entry.get("trace_id") != request["trace_id"]
                    or set(entry)
                    - {"trace_id", "request_id", "operation_id", "job_id", "error_code", "level"}
                ):
                    raise ValueError
                for key, item in entry.items():
                    pattern = (
                        "[a-f0-9]{32}"
                        if key == "trace_id"
                        else "[A-Z][A-Z0-9_]{2,63}"
                        if key == "error_code"
                        else "(DEBUG|INFO|WARNING|ERROR|CRITICAL)"
                        if key == "level"
                        else "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
                    )
                    if not isinstance(item, str) or not re.fullmatch(pattern, item):
                        raise ValueError
                value["logs"].append(dict(entry))
            state = row.get("logs_state")
            if state not in {
                "correlation_required",
                "not_collected",
                "filtered_json_only",
                "unavailable_or_limit_exceeded",
            }:
                raise ValueError
            value["logs_state"] = state
            safe.append(value)
        revision = packet["database_revision"]
        if (
            not isinstance(revision, list)
            or len(revision) > 4
            or any(
                not isinstance(v, str) or not re.fullmatch("[A-Za-z0-9_]{1,64}", v)
                for v in revision
            )
        ):
            raise ValueError
        identity = [
            {key: r.get(key) for key in ("service", "container_id", "image_id")} for r in safe
        ]
        identity.sort(key=lambda r: str(r["service"]))
        baseline = hashlib.sha256(
            json.dumps([identity, sorted(revision)], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if (
            packet["baseline_sha256"] != baseline
            or type(packet["complete"]) is not bool
            or not isinstance(packet["missing_services"], list)
            or not set(packet["missing_services"]) <= names
            or packet["complete"] != (not packet["missing_services"])
            or any(
                (not r["container_id"] or not r["image_id"] or r["status"] == "unavailable")
                and r["service"] not in packet["missing_services"]
                for r in safe
            )
            or (
                request["target_environment"] == "production-iran"
                and not revision
                and "db" not in packet["missing_services"]
            )
        ):
            raise ValueError
        capacity = packet.get("capacity", {})
        if not isinstance(capacity, dict):
            raise ValueError
        resources = {}
        for key, limit in {"cpu_count": 4096, "root_disk_free_bytes": 2**60}.items():
            if (item := capacity.get(key)) is not None:
                if type(item) is not int or not 0 <= item <= limit:
                    raise ValueError
                resources[key] = item
        memory = capacity.get("memory", {})
        if not isinstance(memory, dict):
            raise ValueError
        safe_memory = {}
        for key in ("MemTotal", "MemAvailable"):
            if (item := memory.get(key)) is not None:
                if type(item) is not int or not 0 <= item <= 2**60:
                    raise ValueError
                safe_memory[key] = item
        return {
            "schema_version": 1,
            "target_environment": request["target_environment"],
            "captured_at": captured.isoformat(),
            "services": safe,
            "database_revision": revision,
            "baseline_sha256": baseline,
            "complete": packet["complete"],
            "missing_services": packet["missing_services"],
            "capacity": {**resources, "memory": safe_memory},
            "provenance": "enrolled_github_host_observation",
            "business_outcome_verified": False,
        }
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("invalid_host_observation") from None


def record_observation(
    db: Session,
    worker: DebugConnector,
    operation_id: UUID,
    lease: UUID,
    stage: str,
    value: dict[str, Any],
) -> dict[str, Any]:
    row = leased_operation(db, worker, operation_id, lease, terminal=True)
    if row.kind != "observe" or len(json.dumps(value).encode()) > 32000:
        raise ValueError("invalid_automation_receipt")
    run = db.get(DebugRun, row.run_id)
    assert run is not None
    digest = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    receipts = row.result.get("_receipts", {})
    if stage in receipts:
        if receipts[stage] != digest:
            raise ValueError("automation_receipt_conflict")
        return {
            "operation": operation_json(row),
            "disposition": "reconcile_only"
            if stage in {"dispatch_intent", "cancel_intent"}
            else "recorded",
        }
    if row.state not in ACTIVE:
        raise ValueError("automation_not_active")
    disposition = "recorded"
    safe: dict[str, Any] = {}
    cancelled = row.cancel_requested or run.cancel_requested
    if stage == "observation_prepared":
        if (
            row.state != "preparing"
            or cancelled
            or set(value) != {"policy_commit"}
            or not re.fullmatch("[a-f0-9]{40}", str(value["policy_commit"]))
        ):
            raise ValueError("automation_state_conflict")
        safe = value
    elif stage == "dispatch_intent":
        if value or row.state != "preparing" or not row.result.get("policy_commit") or cancelled:
            raise ValueError("automation_state_conflict")
        row.state = "dispatching"
        disposition = "dispatch_once"
    elif stage == "dispatched":
        if (
            row.state not in {"dispatching", "uncertain"}
            or set(value) != {"workflow_run_id"}
            or type(value["workflow_run_id"]) is not int
            or value["workflow_run_id"] < 1
        ):
            raise ValueError("automation_state_conflict")
        row.state = "running"
        safe = value
        row.error_code = None
    elif stage == "uncertain":
        if value or row.state not in {"dispatching", "uncertain"}:
            raise ValueError("automation_state_conflict")
        row.state = "uncertain"
        row.error_code = "dispatch_confirmation_missing"
    elif stage == "cancel_intent":
        if value or not cancelled or row.state != "running":
            raise ValueError("automation_state_conflict")
        safe = {"cancellation_requested_remotely": True}
        disposition = "cancel_once"
    elif stage == "observation_completed":
        if (
            row.state != "running"
            or set(value)
            != {
                "workflow_run_id",
                "workflow_conclusion",
                "artifact_id",
                "artifact_digest",
                "observation",
            }
            or value["workflow_run_id"] != row.result.get("workflow_run_id")
        ):
            raise ValueError("automation_state_conflict")
        conclusion = value["workflow_conclusion"]
        if conclusion == "success":
            if (
                type(value["artifact_id"]) is not int
                or value["artifact_id"] < 1
                or not re.fullmatch("sha256:[a-f0-9]{64}", str(value["artifact_digest"]))
            ):
                raise ValueError("invalid_automation_receipt")
            safe = {
                **value,
                "observation": validate_observation(value["observation"], row.request),
                "artifact_verified": True,
            }
            row.state = "succeeded"
        elif conclusion in {
            "failure",
            "cancelled",
            "timed_out",
            "startup_failure",
            "action_required",
            "skipped",
            "stale",
            "neutral",
        }:
            safe = {"workflow_run_id": value["workflow_run_id"], "workflow_conclusion": conclusion}
            row.state = "cancelled" if conclusion == "cancelled" else "failed"
        else:
            raise ValueError("invalid_automation_receipt")
    elif stage == "waiting":
        if set(value) != {"workflow_status"} or value["workflow_status"] not in {
            "unknown",
            "requested",
            "queued",
            "in_progress",
            "waiting",
            "pending",
        }:
            raise ValueError("invalid_automation_receipt")
        row.lease_until = datetime.now(UTC) + timedelta(seconds=15)
        db.flush()
        return {"operation": operation_json(row), "disposition": "recorded"}
    elif stage == "failed":
        if set(value) != {"code"} or value["code"] not in {
            "github_credential_not_configured",
            "github_rate_limited",
            "github_authorization_rejected",
            "github_request_rejected",
            "github_unreachable",
            "github_invalid_response",
            "github_response_too_large",
            "github_invalid_identity",
            "github_duplicate_dispatch",
            "github_artifact_not_found",
            "github_artifact_invalid",
            "automation_cancelled_before_dispatch",
            "automation_execution_failed",
            "github_observation_workflow_not_installed",
        }:
            raise ValueError("invalid_automation_receipt")
        row.state = (
            "cancelled" if value["code"] == "automation_cancelled_before_dispatch" else "blocked"
        )
        row.error_code = value["code"]
    else:
        raise ValueError("invalid_automation_receipt")
    row.result = {**row.result, **safe, "_receipts": {**receipts, stage: digest}}
    if row.state not in ACTIVE:
        row.lease_until = None
    event = append_event(
        db,
        run,
        "host_" + stage.removeprefix("observation_"),
        {
            "operation_id": str(row.id),
            "state": row.state,
            "target_environment": row.request["target_environment"],
            "occurrence_id": str(row.occurrence_id),
            "result": safe,
        },
    )
    if stage == "observation_completed" and row.state == "succeeded":
        row.result = {**row.result, "evidence_id": str(event.id)}
    db.flush()
    return {"operation": operation_json(row), "disposition": disposition}
