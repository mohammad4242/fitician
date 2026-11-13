"""Publish only an occurrence-bound, successfully validated immutable repair."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .automation import ACTIVE, authorize_operation, leased_operation, operation_json
from .connectors import _authorize_run
from .models import DebugConnector, DebugOperation, DebugRun
from .privacy import sanitize_text
from .service import append_event


def queue_publication(
    db: Session, run_id: UUID, key: str, validation_id: UUID, title: str, snapshot_digest: str
) -> DebugOperation:
    run = db.scalar(select(DebugRun).where(DebugRun.id == run_id).with_for_update())
    if run is None:
        raise ValueError("run_not_found")
    _authorize_run(db, run)
    if run.action != "prepare_fix":
        raise ValueError("mutation_not_authorized")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key):
        raise ValueError("invalid_publication_request")
    if (
        not isinstance(title, str)
        or sanitize_text(title) != title
        or not re.fullmatch(r"(fix|feat|test|refactor)\([A-Za-z0-9_-]+\): [^\r\n]{5,120}", title)
    ):
        raise ValueError("specific_pr_title_required")
    validation = db.scalar(
        select(DebugOperation).where(DebugOperation.id == validation_id).with_for_update()
    )
    source_run = db.get(DebugRun, validation.run_id) if validation else None
    if (
        validation is None
        or source_run is None
        or source_run.thread_id != run.thread_id
        or validation.kind != "validate"
        or validation.state != "succeeded"
        or validation.request.get("purpose") != "repair_validation"
        or not validation.request.get("snapshot", {}).get("files")
        or validation.result.get("artifact_verified") is not True
        or validation.result.get("workflow_conclusion") != "success"
        or validation.result.get("validation", {}).get("passed") is not True
        or validation.occurrence_id
        != (UUID(run.evidence["occurrence_id"]) if run.evidence.get("occurrence_id") else None)
        or str(validation.worker_id) != run.config_snapshot.get("automation_worker_id")
    ):
        raise ValueError("matching_successful_ci_required")
    authorize_operation(db, validation)
    if snapshot_digest != validation.request["snapshot"]["snapshot_digest"]:
        raise ValueError("automation_snapshot_mismatch")
    worker = db.get(DebugConnector, validation.worker_id)
    if worker is None or worker.revoked or worker.kind != "automation":
        raise ValueError("automation_worker_not_configured")
    request = {
        "validation_id": str(validation.id),
        "title": title,
        "purpose": "repair_publication",
        "snapshot": validation.request["snapshot"],
        "profile": validation.request["profile"],
        "tests": validation.request["tests"],
        "proof": {k: v for k, v in validation.result.items() if not k.startswith("_")},
        "issue_id": run.evidence.get("issue_id"),
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
    active = (
        db.scalar(
            select(func.count())
            .select_from(DebugOperation)
            .where(
                DebugOperation.environment == validation.environment,
                DebugOperation.state.in_(ACTIVE),
            )
        )
        or 0
    )
    if active >= 100:
        raise ValueError("automation_queue_capacity_reached")
    # One publication for each immutable validation, across reconnects and later turns.
    previous = db.scalar(
        select(DebugOperation)
        .where(
            DebugOperation.environment == validation.environment,
            DebugOperation.kind == "publish_pr",
            DebugOperation.request["validation_id"].as_string() == str(validation.id),
        )
        .order_by(DebugOperation.created_at)
    )
    if previous:
        if previous.request_hash != digest:
            raise ValueError("publication_already_requested")
        return previous
    row = DebugOperation(
        run_id=run.id,
        worker_id=worker.id,
        occurrence_id=validation.occurrence_id,
        environment=validation.environment,
        kind="publish_pr",
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
            "kind": row.kind,
            "validation_id": str(validation.id),
            "state": row.state,
        },
    )
    return row


def record_publication(
    db: Session,
    worker: DebugConnector,
    operation_id: UUID,
    lease: UUID,
    stage: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    row = leased_operation(db, worker, operation_id, lease, terminal=True)
    run = authorize_operation(db, row)
    if row.kind != "publish_pr" or len(json.dumps(result).encode()) > 4096:
        raise ValueError("invalid_automation_receipt")
    digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    previous = row.result.get("_receipts", {})
    if stage in previous:
        if previous[stage] != digest:
            raise ValueError("automation_receipt_conflict")
        return {
            "operation": operation_json(row),
            "disposition": "reconcile_only" if stage == "publication_intent" else "recorded",
        }
    if row.state not in ACTIVE:
        raise ValueError("automation_not_active")
    disposition = "recorded"
    if stage == "publication_intent":
        if result or row.state != "preparing" or row.cancel_requested or run.cancel_requested:
            raise ValueError("automation_state_conflict")
        row.state, disposition = "dispatching", "publish_once"
    elif stage == "publication_completed":
        proof = row.request["proof"]
        if row.state not in {"dispatching", "uncertain"} or set(result) != {
            "pr_number",
            "pr_url",
            "candidate_commit",
            "branch",
            "base",
        }:
            raise ValueError("invalid_automation_receipt")
        number = result["pr_number"]
        if (
            type(number) is not int
            or number < 1
            or result["pr_url"] != f"https://github.com/mohammad4242/fitician/pull/{number}"
            or result["candidate_commit"] != proof["candidate_commit"]
            or result["branch"] != proof["branch"]
            or result["base"] != "main"
        ):
            raise ValueError("automation_snapshot_mismatch")
        row.state, row.error_code = "succeeded", None
    elif stage == "uncertain":
        if result or row.state not in {"dispatching", "uncertain"}:
            raise ValueError("automation_state_conflict")
        row.state, row.error_code = "uncertain", "publication_confirmation_missing"
    elif stage == "waiting":
        if (
            set(result) != {"workflow_status"}
            or not isinstance(result["workflow_status"], str)
            or result["workflow_status"] not in {"unknown", "requested"}
        ):
            raise ValueError("invalid_automation_receipt")
        from datetime import UTC, datetime, timedelta

        row.lease_until = datetime.now(UTC) + timedelta(seconds=30)
        db.flush()
        return {"operation": operation_json(row), "disposition": "recorded"}
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
                "github_invalid_identity",
                "github_artifact_not_found",
                "github_artifact_invalid",
                "github_publication_proof_mismatch",
                "github_repair_requires_current_base",
                "github_publication_branch_changed",
                "github_duplicate_publication",
                "github_publication_already_closed",
                "automation_cancelled_before_dispatch",
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
    row.result = {**row.result, **result, "_receipts": {**previous, stage: digest}}
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
            "error_code": row.error_code,
            **(
                {"pr_url": result["pr_url"], "commit": result["candidate_commit"]}
                if stage == "publication_completed"
                else {}
            ),
        },
    )
    db.flush()
    return {"operation": operation_json(row), "disposition": disposition}
