"""Replay the published regression scope at a verified deployed commit in isolated Actions.

This is source regression evidence. It cannot replay private production inputs, authorize
deployment, establish production business resolution or change the issue lifecycle.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .automation import ACTIVE
from .ci_contract import validation_spec
from .deployment import _admin, _hash, _recent_host, _scoped
from .models import DebugConnector, DebugOperation, DebugRun
from .service import append_event


def queue_replay(
    db: Session,
    issue_id: UUID,
    deployment_id: UUID,
    observation_id: UUID,
    actor_id: UUID,
    key: str,
) -> DebugOperation:
    _admin(db, actor_id)
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,80}", key):
        raise ValueError("invalid_replay_request")
    deployment = _scoped(db, issue_id, deployment_id)
    if (
        deployment.kind != "deploy"
        or deployment.state != "succeeded"
        or deployment.result.get("deployed") is not True
        or deployment.cancel_requested
    ):
        raise ValueError("verified_deployment_required")
    submission = "replay:" + str(actor_id) + ":" + key
    previous = db.scalar(
        select(DebugOperation).where(
            DebugOperation.run_id == deployment.run_id, DebugOperation.submission_key == submission
        )
    )
    if previous:
        if (
            previous.kind != "replay"
            or previous.request.get("deployment_id") != str(deployment.id)
            or previous.request.get("observation_id") != str(observation_id)
        ):
            raise ValueError("automation_idempotency_conflict")
        return previous
    publication = _scoped(db, issue_id, UUID(deployment.request["publication_id"]))
    if (
        publication.kind != "publish_pr"
        or publication.state != "succeeded"
        or publication.occurrence_id != deployment.occurrence_id
    ):
        raise ValueError("successful_repair_publication_required")
    spec = validation_spec(publication.request["profile"], publication.request["tests"])
    if spec["profile"] == "migrations":
        raise ValueError("business_regression_profile_required")
    observation = _scoped(db, issue_id, observation_id)
    packet = _recent_host(observation)
    readback = deployment.result["readback"]
    grant = deployment.result["grant"]
    if (
        observation.occurrence_id != deployment.occurrence_id
        or packet.get("target_environment") != deployment.target_environment
        or readback["target_environment"] != deployment.target_environment
        or readback["commit"] != grant["commit"]
        or readback["manifest_sha256"] != grant["manifest_sha256"]
    ):
        raise ValueError("replay_target_changed")
    services = {row["service"]: row for row in packet["services"]}
    for name, service in readback["services"].items():
        expected = readback["images"][service["image_role"]]["image_id"]
        if services.get(name, {}).get("image_id") != expected:
            raise ValueError("replay_target_changed")
    worker = db.get(DebugConnector, deployment.worker_id)
    if worker is None or worker.revoked or worker.kind != "automation":
        raise ValueError("automation_worker_not_configured")
    request = {
        "purpose": "controlled_release_replay",
        "deployment_id": str(deployment.id),
        "observation_id": str(observation.id),
        "baseline_sha256": packet["baseline_sha256"],
        "target_environment": deployment.target_environment,
        "release_commit": grant["commit"],
        "manifest_sha256": grant["manifest_sha256"],
        "deployment_artifact_digest": deployment.result["artifact_digest"],
        "deployment_artifact_id": deployment.result["artifact_id"],
        "profile": spec["profile"],
        "tests": spec["tests"],
        "requested_by": str(actor_id),
    }
    digest = _hash(request)
    if db.scalar(
        select(DebugOperation.id)
        .where(
            DebugOperation.kind == "replay",
            DebugOperation.state.in_(ACTIVE),
            DebugOperation.request["deployment_id"].as_string() == str(deployment.id),
            DebugOperation.environment == deployment.environment,
        )
        .limit(1)
    ):
        raise ValueError("replay_already_active")
    if (
        db.scalar(
            select(func.count())
            .select_from(DebugOperation)
            .where(
                DebugOperation.environment == deployment.environment,
                DebugOperation.state.in_(ACTIVE),
            )
        )
        or 0
    ) >= 100:
        raise ValueError("automation_queue_capacity_reached")
    run = db.get(DebugRun, deployment.run_id)
    assert run is not None
    if run.cancel_requested:
        raise ValueError("run_no_longer_authorized")
    row = DebugOperation(
        run_id=run.id,
        worker_id=worker.id,
        occurrence_id=deployment.occurrence_id,
        environment=deployment.environment,
        target_environment=deployment.target_environment,
        kind="replay",
        state="queued",
        submission_key=submission,
        request_hash=digest,
        request=request,
        result={"verified_resolved": False, "production_business_outcome_verified": False},
    )
    db.add(row)
    db.flush()
    append_event(
        db,
        run,
        "replay_queued",
        {
            "operation_id": str(row.id),
            "deployment_id": str(deployment.id),
            "actor_id": str(actor_id),
            "occurrence_id": str(row.occurrence_id),
            "release_commit": request["release_commit"],
            "profile": spec["profile"],
        },
    )
    return row


def preparation(row: DebugOperation, value: dict[str, Any]) -> dict[str, Any]:
    if (
        set(value) != {"candidate_commit", "policy_commit"}
        or value["candidate_commit"] != row.request["release_commit"]
        or not isinstance(value["policy_commit"], str)
        or not re.fullmatch("[a-f0-9]{40}", value["policy_commit"])
    ):
        raise ValueError("automation_snapshot_mismatch")
    return value
