"""Artifact-bound deployment review. Models and broker receipts cannot create grants."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.observability.environment import diagnostics_environment

from .automation import ACTIVE, authorize_operation, leased_operation, operation_json
from .models import DebugConnector, DebugOperation, DebugRun, DebugThread
from .release_contract import validate_release
from .service import append_event


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _scoped(db: Session, issue_id: UUID, operation_id: UUID) -> DebugOperation:
    row = db.scalar(
        select(DebugOperation)
        .join(DebugRun)
        .join(DebugThread)
        .where(
            DebugOperation.id == operation_id,
            DebugThread.issue_id == issue_id,
            DebugThread.environment == diagnostics_environment(),
            DebugOperation.environment == diagnostics_environment(),
        )
        .with_for_update(of=DebugOperation)
    )
    if row is None:
        raise ValueError("operation_not_found")
    authorize_operation(db, row)
    return row


def _admin(db: Session, actor_id: UUID) -> None:
    actor = db.get(User, actor_id)
    if actor is None or not actor.is_admin:
        raise ValueError("deployment_not_authorized")


def _recent_host(observation: DebugOperation) -> dict[str, Any]:
    try:
        packet = observation.result["observation"]
        captured = datetime.fromisoformat(packet["captured_at"])
        valid = (
            observation.kind == "observe"
            and observation.state == "succeeded"
            and observation.result.get("artifact_verified") is True
            and packet["complete"] is True
            and captured.tzinfo is not None
            and abs((datetime.now(UTC) - captured).total_seconds()) <= 900
            and re.fullmatch("[a-f0-9]{64}", packet["baseline_sha256"])
        )
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        raise ValueError("matching_host_observation_required")
    return cast(dict[str, Any], packet)


def queue_deployment(
    db: Session,
    issue_id: UUID,
    publication_id: UUID,
    observation_id: UUID,
    actor_id: UUID,
    key: str,
    ci_run_id: int,
) -> DebugOperation:
    _admin(db, actor_id)
    if (
        not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", key)
        or type(ci_run_id) is not int
        or ci_run_id < 1
    ):
        raise ValueError("invalid_deployment_request")
    publication = _scoped(db, issue_id, publication_id)
    if (
        publication.kind != "publish_pr"
        or publication.state != "succeeded"
        or type(publication.result.get("pr_number")) is not int
        or publication.result["pr_number"] < 1
    ):
        raise ValueError("successful_repair_publication_required")
    observation = _scoped(db, issue_id, observation_id)
    packet = _recent_host(observation)
    target = observation.request.get("target_environment")
    if (
        target not in {"production-iran", "production-germany"}
        or packet.get("target_environment") != target
        or observation.occurrence_id != publication.occurrence_id
    ):
        raise ValueError("matching_host_observation_required")
    worker = db.get(DebugConnector, publication.worker_id)
    if worker is None or worker.revoked or worker.kind != "automation":
        raise ValueError("automation_worker_not_configured")
    request = {
        "purpose": "repair_deployment",
        "publication_id": str(publication.id),
        "observation_id": str(observation.id),
        "pr_number": publication.result["pr_number"],
        "candidate_commit": publication.result["candidate_commit"],
        "ci_run_id": ci_run_id,
        "target_environment": target,
        "deploy_kind": "full" if target == "production-iran" else "agent",
        "baseline_sha256": packet["baseline_sha256"],
        "requested_by": str(actor_id),
        # Schema-changing releases still require the separate reviewed migration path.
        "allow_schema_migrations": False,
    }
    digest = _hash(request)
    submission = "deployment:" + str(actor_id) + ":" + key
    existing = db.scalar(
        select(DebugOperation).where(
            DebugOperation.run_id == publication.run_id, DebugOperation.submission_key == submission
        )
    )
    if existing:
        if existing.request_hash != digest:
            raise ValueError("automation_idempotency_conflict")
        return existing
    if db.scalar(
        select(DebugOperation.id)
        .where(
            DebugOperation.environment == publication.environment,
            DebugOperation.kind == "deploy",
            DebugOperation.target_environment == target,
            DebugOperation.state.in_((*ACTIVE, "awaiting_authorization")),
        )
        .limit(1)
    ):
        raise ValueError("deployment_target_busy")
    row = DebugOperation(
        run_id=publication.run_id,
        worker_id=worker.id,
        occurrence_id=publication.occurrence_id,
        environment=publication.environment,
        kind="deploy",
        target_environment=target,
        state="queued",
        submission_key=submission,
        request_hash=digest,
        request=request,
        result={},
    )
    db.add(row)
    db.flush()
    run = db.get(DebugRun, row.run_id)
    assert run is not None
    append_event(
        db,
        run,
        "deployment_preview_queued",
        {
            "operation_id": str(row.id),
            "actor_id": str(actor_id),
            "target_environment": target,
            "ci_run_id": ci_run_id,
        },
    )
    return row


def authorize_deployment(
    db: Session, issue_id: UUID, operation_id: UUID, actor_id: UUID, key: str, preview_sha256: str
) -> DebugOperation:
    _admin(db, actor_id)
    row = _scoped(db, issue_id, operation_id)
    if row.kind != "deploy" or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,80}", key):
        raise ValueError("deployment_not_authorized")
    if preview_sha256 != row.result.get("preview_sha256"):
        raise ValueError("deployment_preview_changed")
    if grant := row.result.get("grant"):
        if grant["submission_key"] == key and grant["actor_id"] == str(actor_id):
            return row
        raise ValueError("deployment_already_authorized")
    if row.state != "awaiting_authorization" or row.cancel_requested:
        raise ValueError("deployment_not_awaiting_authorization")
    observation = _scoped(db, issue_id, UUID(row.request["observation_id"]))
    if _recent_host(observation)["baseline_sha256"] != row.request["baseline_sha256"]:
        raise ValueError("deployment_target_changed")
    # Any subsequently recorded target change invalidates the old preview.
    latest = db.scalar(
        select(DebugOperation)
        .where(
            DebugOperation.kind == "observe",
            DebugOperation.state == "succeeded",
            DebugOperation.environment == row.environment,
            DebugOperation.request["target_environment"].as_string() == row.target_environment,
        )
        .order_by(DebugOperation.created_at.desc())
        .limit(1)
    )
    if (
        latest
        and latest.result.get("observation", {}).get("baseline_sha256")
        != row.request["baseline_sha256"]
    ):
        raise ValueError("deployment_target_changed")
    proof = row.result["preview"]
    grant = {
        "actor_id": str(actor_id),
        "submission_key": key,
        "authorized_at": int(datetime.now(UTC).timestamp()),
        "expires_at": int(datetime.now(UTC).timestamp()) + 1800,
        "action": "regional_release",
        "commit": proof["manifest"]["commit"],
        "ci_run_id": row.request["ci_run_id"],
        "manifest_sha256": proof["manifest_sha256"],
        "target_environment": row.target_environment,
        "deploy_kind": row.request["deploy_kind"],
        "baseline_sha256": row.request["baseline_sha256"],
        "allow_schema_migrations": False,
        "preview_sha256": preview_sha256,
    }
    row.result = {**row.result, "grant": grant}
    row.state, row.lease_until = "queued", None
    run = db.get(DebugRun, row.run_id)
    assert run is not None
    append_event(db, run, "deployment_authorized", {"operation_id": str(row.id), **grant})
    db.flush()
    return row


def require_grant(db: Session, row: DebugOperation) -> dict[str, Any]:
    grant = row.result.get("grant")
    if not grant or grant["preview_sha256"] != row.result.get("preview_sha256"):
        raise ValueError("deployment_not_authorized")
    _admin(db, UUID(grant["actor_id"]))
    if grant["expires_at"] <= int(datetime.now(UTC).timestamp()):
        raise ValueError("deployment_authorization_expired")
    return cast(dict[str, Any], grant)


def validate_readback(row: DebugOperation, value: dict[str, Any]) -> dict[str, Any]:
    try:
        if set(value) != {"artifact_id", "artifact_digest", "readback"}:
            raise ValueError
        proof = value["readback"]
        grant = row.result["grant"]
        manifest = row.result["preview"]["manifest"]
        roles = (
            {"agent-service": "agent"}
            if row.target_environment == "production-germany"
            else {
                **{
                    name: "backend"
                    for name in (
                        "backend",
                        "backend-2",
                        "food-photo-worker",
                        "body-analysis-worker",
                        "notification-worker",
                        "scheduler",
                    )
                },
                "frontend": "frontend",
            }
        )
        if (
            type(value["artifact_id"]) is not int
            or value["artifact_id"] < 1
            or not re.fullmatch("sha256:[a-f0-9]{64}", value["artifact_digest"])
            or set(proof)
            != {
                "schema_version",
                "operation_id",
                "target_environment",
                "commit",
                "manifest_sha256",
                "ci_run_id",
                "captured_at",
                "images",
                "services",
                "provenance",
                "business_outcome_verified",
            }
            or proof["schema_version"] != 1
            or proof["operation_id"] != str(row.id)
            or proof["target_environment"] != row.target_environment
            or proof["commit"] != grant["commit"]
            or proof["ci_run_id"] != grant["ci_run_id"]
            or proof["manifest_sha256"] != grant["manifest_sha256"]
            or proof["provenance"] != "fixed_running_image_guard"
            or proof["business_outcome_verified"] is not False
            or proof["images"] != {role: manifest["images"][role] for role in set(roles.values())}
            or set(proof["services"]) != set(roles)
        ):
            raise ValueError
        captured = datetime.fromisoformat(proof["captured_at"])
        if (
            captured.tzinfo is None
            or captured.timestamp() < grant["authorized_at"] - 60
            or captured.timestamp() > datetime.now(UTC).timestamp() + 60
        ):
            raise ValueError
        for name, role in roles.items():
            service = proof["services"][name]
            if (
                set(service) != {"container_id", "image_role", "healthy"}
                or not re.fullmatch("[a-f0-9]{12,64}", service["container_id"])
                or service["image_role"] != role
                or service["healthy"] is not True
            ):
                raise ValueError
        return value
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError("deployment_readback_invalid") from None


def record_deployment(
    db: Session,
    worker: DebugConnector,
    operation_id: UUID,
    lease: UUID,
    stage: str,
    value: dict[str, Any],
) -> dict[str, Any]:
    row = leased_operation(db, worker, operation_id, lease, terminal=True)
    if row.kind != "deploy" or len(json.dumps(value).encode()) > 24000:
        raise ValueError("invalid_automation_receipt")
    receipts = row.result.get("_receipts", {})
    digest = _hash(value)
    if stage in receipts:
        if receipts[stage] != digest:
            raise ValueError("automation_receipt_conflict")
        return {
            "operation": operation_json(row),
            "disposition": "reconcile_only"
            if stage in {"dispatch_intent", "cancel_intent"}
            else "recorded",
        }
    safe: dict[str, Any] = {}
    disposition = "recorded"
    if stage == "deployment_prepared":
        if (
            row.state != "preparing"
            or row.result.get("grant")
            or set(value)
            != {
                "manifest",
                "manifest_sha256",
                "artifact_id",
                "artifact_digest",
                "policy_commit",
                "pr_number",
            }
        ):
            raise ValueError("invalid_automation_receipt")
        validate_release(
            value["manifest"], commit=value["policy_commit"], ci_run_id=row.request["ci_run_id"]
        )
        if (
            not re.fullmatch("[a-f0-9]{64}", str(value["manifest_sha256"]))
            or not re.fullmatch("sha256:[a-f0-9]{64}", str(value["artifact_digest"]))
            or type(value["artifact_id"]) is not int
            or value["artifact_id"] < 1
            or value["pr_number"] != row.request["pr_number"]
            or row.cancel_requested
        ):
            raise ValueError("invalid_automation_receipt")
        safe = {
            "preview": value,
            "preview_sha256": _hash([row.request, value]),
            "deployed": False,
            "verified_resolved": False,
        }
        row.state = "awaiting_authorization"
    elif stage == "dispatch_intent":
        require_grant(db, row)
        if value or row.state != "preparing" or row.cancel_requested:
            raise ValueError("deployment_not_authorized")
        row.state, disposition = "dispatching", "dispatch_once"
    elif stage == "dispatched":
        if (
            row.state not in {"dispatching", "uncertain"}
            or set(value) != {"workflow_run_id"}
            or type(value["workflow_run_id"]) is not int
            or value["workflow_run_id"] < 1
        ):
            raise ValueError("invalid_automation_receipt")
        safe, row.state = value, "running"
        row.error_code = None
    elif stage == "uncertain":
        if value or row.state not in {"dispatching", "uncertain"}:
            raise ValueError("automation_state_conflict")
        row.state, row.error_code = "uncertain", "dispatch_confirmation_missing"
    elif stage == "cancel_intent":
        run = db.get(DebugRun, row.run_id)
        if (
            value
            or row.state != "running"
            or not (row.cancel_requested or (run and run.cancel_requested))
        ):
            raise ValueError("automation_state_conflict")
        safe, disposition = {"cancellation_requested_remotely": True}, "cancel_once"
    elif stage == "deployment_completed":
        if (
            row.state != "running"
            or set(value) != {"workflow_run_id", "workflow_conclusion"}
            or value["workflow_run_id"] != row.result.get("workflow_run_id")
            or value["workflow_conclusion"]
            not in {
                "success",
                "failure",
                "cancelled",
                "timed_out",
                "startup_failure",
                "action_required",
                "skipped",
                "stale",
                "neutral",
            }
        ):
            raise ValueError("invalid_automation_receipt")
        safe = {
            **value,
            "workflow_completed": True,
            "deployed": False,
            "verified_resolved": False,
            "verification_state": "running_release_unverified",
        }
        row.error_code = None
        # A green workflow is insufficient evidence of the actual running release.
        row.state = "verifying" if value["workflow_conclusion"] == "success" else "failed"
        if value["workflow_conclusion"] == "cancelled":
            row.state = "cancelled"
    elif stage == "deployment_verified":
        if row.state != "verifying" or row.result.get("workflow_conclusion") != "success":
            raise ValueError("automation_state_conflict")
        safe = {
            **validate_readback(row, value),
            "deployed": True,
            "verified_resolved": False,
            "verification_state": "deployed_business_outcome_unverified",
        }
        row.state = "succeeded"
        row.error_code = None
    elif stage == "failed":
        codes = {
            "deployment_not_authorized",
            "deployment_authorization_expired",
            "deployment_readback_invalid",
            "github_release_not_ready",
            "github_invalid_identity",
            "github_artifact_invalid",
            "github_artifact_not_found",
            "github_mutation_uncertain",
            "github_unreachable",
            "github_rate_limited",
            "github_authorization_rejected",
            "github_request_rejected",
            "github_response_too_large",
            "github_invalid_response",
            "github_duplicate_dispatch",
            "automation_cancelled_before_dispatch",
            "automation_execution_failed",
        }
        if set(value) != {"code"} or value["code"] not in codes or row.state not in ACTIVE:
            raise ValueError("invalid_automation_receipt")
        if row.state in {"dispatching", "uncertain", "running", "verifying"}:
            # The remote release may still be mutating. Preserve the target reservation
            # until its identity/conclusion/readback can actually be reconciled.
            if row.error_code != value["code"]:
                run = db.get(DebugRun, row.run_id)
                assert run is not None
                append_event(
                    db,
                    run,
                    "deploy_reconcile_blocked",
                    {"operation_id": str(row.id), "code": value["code"], "state": row.state},
                )
            row.error_code = value["code"]
            row.lease_until = datetime.now(UTC) + timedelta(seconds=30)
            db.flush()
            return {"operation": operation_json(row), "disposition": "reconcile_only"}
        row.state = (
            "cancelled" if value["code"] == "automation_cancelled_before_dispatch" else "blocked"
        )
        row.error_code = value["code"]
    elif stage == "waiting":
        if (
            set(value) != {"workflow_status"}
            or value["workflow_status"] not in {"unknown", "requested"}
            or row.state not in ACTIVE
        ):
            raise ValueError("invalid_automation_receipt")
        row.lease_until = datetime.now(UTC) + timedelta(seconds=15)
        db.flush()
        return {"operation": operation_json(row), "disposition": "recorded"}
    else:
        raise ValueError("invalid_automation_receipt")
    row.result = {**row.result, **safe, "_receipts": {**receipts, stage: digest}}
    if row.state not in ACTIVE:
        row.lease_until = None
    run = db.get(DebugRun, row.run_id)
    assert run is not None
    append_event(
        db,
        run,
        "deploy_" + stage.removeprefix("deployment_"),
        {
            "operation_id": str(row.id),
            "target_environment": row.target_environment,
            "occurrence_id": str(row.occurrence_id),
            "state": row.state,
            "result": safe,
        },
    )
    db.flush()
    return {"operation": operation_json(row), "disposition": disposition}
