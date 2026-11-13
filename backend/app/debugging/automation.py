"""Durable automation intent. No credentials, shell or external calls in request handlers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.observability.environment import diagnostics_environment

from .ci_contract import validate_snapshot, validation_spec
from .connectors import _authorize_run
from .models import DebugConnector, DebugMessage, DebugOperation, DebugRun, DebugThread
from .service import append_event

ACTIVE = ("queued", "preparing", "dispatching", "uncertain", "running", "deploying", "verifying")


def authorize_operation(db: Session, operation: DebugOperation) -> DebugRun:
    run = db.get(DebugRun, operation.run_id)
    message = db.get(DebugMessage, run.message_id) if run else None
    actor = db.get(User, message.actor_id) if message and message.actor_id else None
    thread = db.get(DebugThread, run.thread_id) if run else None
    if (
        run is None
        or actor is None
        or not actor.is_admin
        or thread is None
        or thread.environment != diagnostics_environment()
        or operation.environment != thread.environment
    ):
        raise ValueError("automation_not_authorized")
    return run


def queue_validation(
    db: Session, run_id: UUID, key: str, request: dict[str, Any]
) -> DebugOperation:
    run = db.scalar(select(DebugRun).where(DebugRun.id == run_id).with_for_update())
    if run is None:
        raise ValueError("run_not_found")
    _authorize_run(db, run)
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key):
        raise ValueError("invalid_validation_request")
    if set(request) != {"profile", "tests", "snapshot"}:
        raise ValueError("invalid_validation_request")
    spec = validation_spec(request["profile"], request["tests"])
    snapshot = validate_snapshot(request["snapshot"])
    if snapshot["files"] and run.action != "prepare_fix":
        raise ValueError("mutation_not_authorized")
    canonical = {
        "profile": spec["profile"],
        "tests": spec["tests"],
        "snapshot": snapshot,
        "purpose": "connection_check"
        if run.config_snapshot.get("mode") == "ci_connection_probe"
        else "repair_validation",
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    existing = db.scalar(
        select(DebugOperation).where(
            DebugOperation.run_id == run.id,
            DebugOperation.submission_key == key,
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
    count = (
        db.scalar(
            select(func.count())
            .select_from(DebugOperation)
            .where(
                DebugOperation.run_id == run.id,
                DebugOperation.state.in_(ACTIVE),
            )
        )
        or 0
    )
    if count >= 16:
        raise ValueError("automation_queue_capacity_reached")
    total = (
        db.scalar(
            select(func.count())
            .select_from(DebugOperation)
            .where(
                DebugOperation.environment == diagnostics_environment(),
                DebugOperation.state.in_(ACTIVE),
            )
        )
        or 0
    )
    if total >= 100:
        raise ValueError("automation_queue_capacity_reached")
    thread = db.get(DebugThread, run.thread_id)
    assert thread is not None
    row = DebugOperation(
        worker_id=worker.id,
        run_id=run.id,
        occurrence_id=UUID(run.evidence["occurrence_id"])
        if run.evidence.get("occurrence_id")
        else None,
        environment=thread.environment,
        kind="validate",
        state="queued",
        submission_key=key,
        request_hash=digest,
        request=canonical,
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
            "kind": row.kind,
            "profile": spec["profile"],
            "snapshot_digest": snapshot["snapshot_digest"],
            "state": row.state,
        },
    )
    return row


def claim_operation(db: Session, worker: DebugConnector) -> DebugOperation | None:
    if (
        worker.kind != "automation"
        or worker.revoked
        or worker.environment != diagnostics_environment()
    ):
        raise ValueError("automation_worker_not_authorized")
    now = datetime.now(UTC)
    row = db.scalar(
        select(DebugOperation)
        .where(
            DebugOperation.environment == diagnostics_environment(),
            DebugOperation.worker_id == worker.id,
            DebugOperation.state.in_(ACTIVE),
            or_(DebugOperation.lease_until.is_(None), DebugOperation.lease_until < now),
        )
        .order_by(
            DebugOperation.lease_until.asc().nullsfirst(),
            DebugOperation.created_at,
            DebugOperation.id,
        )
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if row is None:
        return None
    try:
        run = authorize_operation(db, row)
    except ValueError:
        row.state, row.error_code = "blocked", "automation_not_authorized"
        row.lease_until = None
        return None
    if row.cancel_requested or run.cancel_requested:
        if row.state == "queued":
            row.state = "cancelled"
            return None
        row.cancel_requested = (
            True  # Worker must reconcile any remote action before terminal state.
        )
    if row.state == "dispatching":
        row.state, row.error_code = "uncertain", "dispatch_confirmation_missing"
    elif row.state == "queued":
        row.state = "preparing"
    row.lease_token = uuid4()
    row.lease_until = now + timedelta(seconds=60)
    db.flush()
    return row


def operation_json(row: DebugOperation) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "run_id": str(row.run_id),
        "kind": row.kind,
        "occurrence_id": str(row.occurrence_id) if row.occurrence_id else None,
        "environment": row.environment,
        "state": row.state,
        "error_code": row.error_code,
        "cancel_requested": row.cancel_requested,
        "profile": row.request.get("profile"),
        "purpose": row.request.get("purpose", "repair_validation"),
        "snapshot_digest": (row.request.get("snapshot") or {}).get("snapshot_digest"),
        "result": {k: v for k, v in row.result.items() if not k.startswith("_")},
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def leased_operation(
    db: Session, worker: DebugConnector, operation_id: UUID, lease: UUID, *, terminal: bool = False
) -> DebugOperation:
    row = db.scalar(
        select(DebugOperation)
        .where(
            DebugOperation.id == operation_id,
            DebugOperation.worker_id == worker.id,
            DebugOperation.environment == worker.environment,
        )
        .with_for_update()
    )
    now = datetime.now(UTC)
    if row is None or row.lease_token != lease:
        raise ValueError("automation_lease_lost")
    authorize_operation(db, row)
    if row.state in ACTIVE:
        if row.lease_until is None or row.lease_until < now:
            raise ValueError("automation_lease_lost")
        row.lease_until = now + timedelta(seconds=180)
    elif not terminal:
        raise ValueError("automation_not_active")
    return row


def _preparation(row: DebugOperation, value: dict[str, Any]) -> dict[str, Any]:
    from .github_automation import sha

    fields = {
        "base_commit",
        "candidate_commit",
        "branch",
        "policy_commit",
        "policy_ref",
        "snapshot_digest",
        "tree_digest",
    }
    if set(value) != fields:
        raise ValueError("invalid_automation_receipt")
    snapshot = row.request["snapshot"]
    for key in ("base_commit", "snapshot_digest", "tree_digest"):
        if value[key] != snapshot[key]:
            raise ValueError("automation_snapshot_mismatch")
    for key in ("base_commit", "candidate_commit", "policy_commit"):
        sha(value[key])
    if (
        value["branch"] != "debug/ci-" + str(row.id)
        or value["policy_ref"] != "debug-policy/" + value["policy_commit"]
    ):
        raise ValueError("automation_snapshot_mismatch")
    return value


def _completion(row: DebugOperation, value: dict[str, Any]) -> dict[str, Any]:
    from .ci_contract import validate_report

    if set(value) != {
        "workflow_run_id",
        "workflow_conclusion",
        "artifact_id",
        "artifact_digest",
        "validation",
    }:
        raise ValueError("invalid_automation_receipt")
    if (
        type(value["workflow_run_id"]) is not int
        or value["workflow_run_id"] != row.result.get("workflow_run_id")
        or not isinstance(value["workflow_conclusion"], str)
        or value["workflow_conclusion"]
        not in {
            "success",
            "failure",
            "cancelled",
            "timed_out",
            "neutral",
            "skipped",
            "action_required",
            "startup_failure",
            "stale",
        }
    ):
        raise ValueError("automation_workflow_mismatch")
    if value["workflow_conclusion"] != "success" and value["validation"] is None:
        if value["artifact_id"] is not None or value["artifact_digest"] is not None:
            raise ValueError("invalid_automation_receipt")
        return value
    validation = value["validation"]
    if not isinstance(validation, dict) or set(validation) != {
        "candidate_commit",
        "policy_commit",
        "profile",
        "tests",
        "image",
        "passed",
        "exit_code",
        "exercised",
        "skipped",
        "failures",
        "failed_tests",
        "failed_stage",
        "diagnostics",
    }:
        raise ValueError("invalid_automation_receipt")
    validate_report(
        {
            k: validation[k]
            for k in (
                "exercised",
                "skipped",
                "failures",
                "failed_tests",
                "failed_stage",
                "diagnostics",
            )
        }
    )
    for key in ("candidate_commit", "policy_commit"):
        if validation[key] != row.result.get(key):
            raise ValueError("automation_snapshot_mismatch")
    if (
        validation["profile"] != row.request["profile"]
        or validation["tests"] != row.request["tests"]
    ):
        raise ValueError("automation_snapshot_mismatch")
    if (
        type(value["artifact_id"]) is not int
        or value["artifact_id"] < 1
        or not isinstance(value["artifact_digest"], str)
        or not re.fullmatch(r"sha256:[a-f0-9]{64}", value["artifact_digest"])
        or not isinstance(validation["image"], str)
        or not re.fullmatch(r"sha256:[a-f0-9]{64}", validation["image"])
        or type(validation["exit_code"]) is not int
        or not 0 <= validation["exit_code"] <= 255
        or type(validation["passed"]) is not bool
    ):
        raise ValueError("invalid_automation_receipt")
    expected = (
        validation["exit_code"] == 0 and validation["exercised"] > 0 and validation["failures"] == 0
    )
    if (
        validation["passed"] != expected
        or value["workflow_conclusion"] == "success"
        and not expected
    ):
        raise ValueError("automation_test_result_mismatch")
    return {**value, "artifact_verified": True, "provenance": "enrolled_github_broker"}


def record_progress(
    db: Session,
    worker: DebugConnector,
    operation_id: UUID,
    lease: UUID,
    stage: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    row = leased_operation(db, worker, operation_id, lease, terminal=True)
    if row.kind == "observe":
        from .host_operations import record_observation

        return record_observation(db, worker, operation_id, lease, stage, result)
    if row.kind == "publish_pr":
        from .publication import record_publication

        return record_publication(db, worker, operation_id, lease, stage, result)
    if row.kind != "validate" or len(json.dumps(result).encode()) > 32000:
        raise ValueError("invalid_automation_receipt")
    if stage == "waiting":
        if (
            row.state not in ACTIVE
            or set(result) != {"workflow_status"}
            or not isinstance(result["workflow_status"], str)
            or result["workflow_status"]
            not in {"queued", "in_progress", "waiting", "pending", "requested", "unknown"}
        ):
            raise ValueError("invalid_automation_receipt")
        row.lease_until = datetime.now(UTC) + timedelta(
            seconds=30 if row.state == "uncertain" else 10
        )
        row.result = {**row.result, **result}
        db.flush()
        return {"operation": operation_json(row), "disposition": "recorded"}
    digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    previous = row.result.get("_receipts", {})
    if stage in previous:
        if previous[stage] != digest:
            raise ValueError("automation_receipt_conflict")
        return {
            "operation": operation_json(row),
            "disposition": "reconcile_only"
            if stage in {"dispatch_intent", "cancel_intent"}
            else "recorded",
        }
    if row.state not in ACTIVE:
        raise ValueError("automation_not_active")
    run = db.scalar(select(DebugRun).where(DebugRun.id == row.run_id).with_for_update())
    assert run is not None
    cancelled = row.cancel_requested or run.cancel_requested
    disposition = "recorded"
    safe: dict[str, Any] = {}
    if stage == "prepared":
        if row.state != "preparing" or cancelled:
            raise ValueError("automation_state_conflict")
        safe = _preparation(row, result)
    elif stage == "dispatch_intent":
        if (
            result
            or row.state != "preparing"
            or not row.result.get("candidate_commit")
            or cancelled
        ):
            raise ValueError("automation_state_conflict")
        row.state = "dispatching"
        disposition = "dispatch_once"
    elif stage == "dispatched":
        if (
            set(result) != {"workflow_run_id"}
            or type(result["workflow_run_id"]) is not int
            or result["workflow_run_id"] < 1
            or row.state not in {"dispatching", "uncertain"}
        ):
            raise ValueError("automation_state_conflict")
        safe, row.state, row.error_code = result, "running", None
    elif stage == "cancel_intent":
        if (
            result
            or not cancelled
            or row.state != "running"
            or not row.result.get("workflow_run_id")
        ):
            raise ValueError("automation_state_conflict")
        safe, disposition = {"cancellation_requested_remotely": True}, "cancel_once"
    elif stage == "completed":
        if row.state != "running":
            raise ValueError("automation_state_conflict")
        safe = _completion(row, result)
        row.state = (
            "cancelled"
            if safe["workflow_conclusion"] == "cancelled"
            else "succeeded"
            if safe["workflow_conclusion"] == "success"
            else "failed"
        )
        row.error_code = None if row.state == "succeeded" else "ci_validation_" + row.state
    elif stage == "uncertain":
        if result or row.state not in {"dispatching", "uncertain"}:
            raise ValueError("automation_state_conflict")
        row.state, row.error_code = "uncertain", "dispatch_confirmation_missing"
    elif stage == "failed":
        code = result.get("code")
        if (
            set(result) != {"code"}
            or not isinstance(code, str)
            or code
            not in {
                "github_credential_not_configured",
                "github_rate_limited",
                "github_authorization_rejected",
                "github_request_rejected",
                "github_unreachable",
                "github_invalid_response",
                "github_immutable_ref_conflict",
                "github_incomplete_tree",
                "github_response_too_large",
                "github_snapshot_path_not_regular",
                "github_snapshot_delete_not_found",
                "github_invalid_identity",
                "github_duplicate_dispatch",
                "github_artifact_not_found",
                "github_artifact_invalid",
                "automation_cancelled_before_dispatch",
                "automation_execution_failed",
            }
        ):
            raise ValueError("invalid_automation_receipt")
        row.state, row.error_code = (
            ("cancelled", None)
            if code == "automation_cancelled_before_dispatch"
            else ("blocked", code)
        )
    else:
        raise ValueError("invalid_automation_receipt")
    row.result = {**row.result, **safe, "_receipts": {**previous, stage: digest}}
    if row.state not in ACTIVE:
        row.lease_until = None
    append_event(
        db,
        run,
        "automation_progress",
        {
            "operation_id": str(row.id),
            "kind": row.kind,
            "state": row.state,
            "stage": stage,
            "workflow_run_id": row.result.get("workflow_run_id"),
            "error_code": row.error_code,
        },
    )
    db.flush()
    return {"operation": operation_json(row), "disposition": disposition}


def availability(db: Session) -> dict[str, Any]:
    worker = db.scalar(
        select(DebugConnector)
        .join(User, User.id == DebugConnector.actor_id)
        .where(
            DebugConnector.kind == "automation",
            DebugConnector.revoked.is_(False),
            DebugConnector.environment == diagnostics_environment(),
            User.is_admin.is_(True),
        )
    )
    connected = bool(
        worker and worker.last_seen and worker.last_seen > datetime.now(UTC) - timedelta(seconds=30)
    )
    configured = bool(
        connected
        and worker
        and worker.capabilities.get("github_authenticated")
        and worker.capabilities.get("workflow_installed")
    )
    verified = False
    if configured and worker:
        verified = (
            db.scalar(
                select(DebugOperation.id)
                .where(
                    DebugOperation.worker_id == worker.id,
                    DebugOperation.state == "succeeded",
                    DebugOperation.kind == "validate",
                    DebugOperation.result["artifact_verified"].as_boolean().is_(True),
                    DebugOperation.result["policy_commit"].as_string()
                    == worker.capabilities.get("policy_commit"),
                )
                .limit(1)
            )
            is not None
        )
    return {
        "worker_id": str(worker.id) if worker else None,
        "worker_name": worker.name if worker else None,
        "connected": connected,
        "configured": configured,
        "live_validation_verified": verified,
        "policy_commit": worker.capabilities.get("policy_commit") if worker else None,
        "error_code": worker.capabilities.get("error_code")
        if worker
        else "automation_worker_not_configured",
    }


def queue_connection_probe(
    db: Session, issue_id: UUID, occurrence_id: UUID, actor_id: UUID, key: str
) -> DebugOperation:
    from app.observability.diagnostics_models import DiagnosticEvent
    from app.observability.evidence import evidence_package

    from .ci_contract import _digest
    from .service import get_thread

    thread = get_thread(db, issue_id)
    actor = db.get(User, actor_id)
    occurrence = db.get(DiagnosticEvent, occurrence_id)
    if actor is None or not actor.is_admin or occurrence is None or occurrence.issue_id != issue_id:
        raise ValueError("automation_probe_not_authorized")
    digest = hashlib.sha256(json.dumps([str(actor_id), str(occurrence_id)]).encode()).hexdigest()
    submission = "ci-probe:" + key
    previous = db.scalar(
        select(DebugMessage).where(
            DebugMessage.thread_id == thread.id,
            DebugMessage.submission_key == submission,
        )
    )
    if previous:
        if previous.request_hash != digest:
            raise ValueError("automation_idempotency_conflict")
        existing = db.scalar(
            select(DebugOperation).join(DebugRun).where(DebugRun.message_id == previous.id)
        )
        assert existing is not None
        return existing
    status = availability(db)
    if not status["configured"] or not re.fullmatch(r"[a-f0-9]{40}", status["policy_commit"] or ""):
        raise ValueError("automation_worker_not_ready")
    from .service import ACTIVE as RUN_ACTIVE

    if db.scalar(
        select(DebugRun.id).where(DebugRun.thread_id == thread.id, DebugRun.state.in_(RUN_ACTIVE))
    ):
        raise ValueError("run_already_active")
    message = DebugMessage(
        thread_id=thread.id,
        actor_id=actor_id,
        role="user",
        content="بررسی اتصال CI با تست‌های مستقل؛ اجرای مدل درخواست نشده است.",
        submission_key=submission,
        request_hash=digest,
    )
    db.add(message)
    db.flush()
    evidence = {
        **evidence_package(db, issue_id, occurrence_id),
        "occurrence_id": str(occurrence_id),
    }
    run = DebugRun(
        thread_id=thread.id,
        message_id=message.id,
        state="investigating",
        action="analyze",
        evidence=evidence,
        config_snapshot={
            "enabled": False,
            "mode": "ci_connection_probe",
            "automation_worker_id": status["worker_id"],
            "automation_worker_name": status["worker_name"],
        },
    )
    db.add(run)
    db.flush()
    snapshot = {
        "base_commit": status["policy_commit"],
        "tree_digest": hashlib.sha256(b"").hexdigest(),
        "files": [],
    }
    snapshot["snapshot_digest"] = _digest(snapshot)
    row = queue_validation(
        db,
        run.id,
        "connection-probe",
        {
            "profile": "backend",
            "tests": ["backend/tests/test_debug_ci_contract.py"],
            "snapshot": snapshot,
        },
    )
    run.state = "completed"
    db.add(
        DebugMessage(
            thread_id=thread.id,
            role="system",
            actor_id=None,
            content="درخواست آزمایش اتصال CI ثبت شد؛ نتیجه هنوز تأیید نشده است.",
        )
    )
    return row
