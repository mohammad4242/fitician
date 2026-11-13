"""Citable findings use the existing immutable run-event journal, never model confidence."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.observability.diagnostics_models import DiagnosticEvent, DiagnosticIssue
from app.observability.environment import diagnostics_environment
from app.observability.evidence import evidence_package

from .models import DebugOperation, DebugRun, DebugRunEvent, DebugThread
from .privacy import sanitize_text
from .service import append_event


class FindingProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    classification: Literal["observed_fact", "hypothesis", "next_check"]
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[UUID] = Field(min_length=1, max_length=8)


class FindingReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    before_test_id: UUID
    after_test_id: UUID
    evidence_version: str = Field(pattern=r"^[a-f0-9]{64}$")
    note: str = Field(min_length=8, max_length=2000)


def proposal_payload(db: Session, run: DebugRun, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        proposal = FindingProposal.model_validate(payload)
    except ValidationError:
        raise ValueError("finding_not_supported") from None
    text = sanitize_text(proposal.text).strip()
    if not text:
        raise ValueError("finding_not_supported")
    references = list(dict.fromkeys(str(identifier) for identifier in proposal.evidence_ids))
    occurrence = run.evidence.get("occurrence_id")
    known = {run.evidence.get("evidence_id"), occurrence}
    for identifier in references:
        if identifier in known:
            continue
        event = db.get(DebugRunEvent, UUID(identifier))
        if event is not None and event.run_id == run.id and event.kind == "host_completed":
            operation = db.scalar(
                select(DebugOperation).where(
                    DebugOperation.run_id == run.id,
                    DebugOperation.kind == "observe",
                    DebugOperation.state == "succeeded",
                    DebugOperation.result["evidence_id"].as_string() == identifier,
                )
            )
            if (
                operation is not None
                and str(operation.id) == event.payload.get("operation_id")
                and operation.result.get("artifact_verified") is True
            ):
                continue
        if (
            event is None
            or event.run_id != run.id
            or event.kind != "tool_completed"
            or event.payload.get("provenance") not in {"connector_tool", "server_observation"}
            or not event.payload.get("output")
        ):
            raise ValueError("finding_evidence_not_found")
    return {
        "classification": proposal.classification,
        "text": text,
        "evidence_ids": references,
        "occurrence_id": occurrence,
        "evidence_version": run.evidence.get("evidence_version"),
        "provenance": "debug_agent_proposal",
    }


def scoped_finding(db: Session, issue_id: UUID, finding_id: UUID) -> tuple[DebugRunEvent, DebugRun]:
    row = db.execute(
        select(DebugRunEvent, DebugRun)
        .join(DebugRun)
        .join(DebugThread)
        .where(
            DebugRunEvent.id == finding_id,
            DebugRunEvent.kind == "finding_proposed",
            DebugThread.issue_id == issue_id,
            DebugThread.environment == diagnostics_environment(),
        )
    ).first()
    if row is None:
        raise ValueError("finding_not_found")
    return row[0], row[1]


def _test_proof(db: Session, run: DebugRun, identifier: UUID, passed: bool) -> dict[str, Any]:
    event = db.get(DebugRunEvent, identifier)
    if (
        event is None
        or event.run_id != run.id
        or event.kind != "tool_completed"
        or event.payload.get("tool") != "fitician_run_tests"
        or event.payload.get("provenance") != "connector_tool"
    ):
        raise ValueError("regression_evidence_required")
    try:
        proof = json.loads(event.payload["output"])
        valid = (
            isinstance(proof, dict)
            and proof.get("passed") is passed
            and type(proof.get("exit_code")) is int
            and (proof["exit_code"] == 0 if passed else proof["exit_code"] > 0)
            and re.fullmatch(r"[a-f0-9]{64}", proof.get("tree_digest", ""))
            and re.fullmatch(r"sha256:[a-f0-9]{64}", proof.get("image", ""))
            and isinstance(proof.get("command"), list)
            and proof["command"]
            and re.search(r"Ran [1-9][0-9]* tests?", proof.get("output", ""))
        )
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        raise ValueError("regression_evidence_required")
    return cast(dict[str, Any], proof)


def verify_finding(
    db: Session, issue_id: UUID, finding_id: UUID, actor_id: UUID, key: str, review: FindingReview
) -> DebugRunEvent:
    proposal, original = scoped_finding(db, issue_id, finding_id)
    if proposal.payload.get("classification") == "next_check":
        raise ValueError("finding_not_supported")
    run = db.scalar(select(DebugRun).where(DebugRun.id == original.id).with_for_update())
    assert run is not None
    actor = db.get(User, actor_id)
    if actor is None or not actor.is_admin:
        raise ValueError("finding_review_not_authorized")
    safe = review.model_dump(mode="json")
    safe["note"] = sanitize_text(review.note).strip()
    digest = hashlib.sha256(
        json.dumps([str(finding_id), safe], sort_keys=True).encode()
    ).hexdigest()
    for previous in db.scalars(
        select(DebugRunEvent).where(
            DebugRunEvent.run_id == run.id, DebugRunEvent.kind == "finding_verified"
        )
    ):
        if previous.payload.get("submission_key") == key:
            if previous.payload.get("request_hash") != digest:
                raise ValueError("idempotency_conflict")
            return previous
        if previous.payload.get("finding_id") == str(finding_id):
            raise ValueError("finding_already_reviewed")
    occurrence = proposal.payload.get("occurrence_id")
    current = evidence_package(db, issue_id, UUID(occurrence) if occurrence else None)
    if (
        current.get("evidence_version") != review.evidence_version
        or proposal.payload.get("evidence_version") != review.evidence_version
    ):
        raise ValueError("finding_evidence_stale")
    if run.state != "completed" or run.action != "prepare_fix":
        raise ValueError("completed_repair_required")
    before = _test_proof(db, run, review.before_test_id, False)
    after = _test_proof(db, run, review.after_test_id, True)
    first = db.get(DebugRunEvent, review.before_test_id)
    second = db.get(DebugRunEvent, review.after_test_id)
    assert first is not None and second is not None
    if (
        first.sequence >= second.sequence
        or before["command"] != after["command"]
        or before["image"] != after["image"]
        or before["tree_digest"] == after["tree_digest"]
    ):
        raise ValueError("matching_regression_comparison_required")
    return append_event(
        db,
        run,
        "finding_verified",
        {
            **safe,
            "finding_id": str(finding_id),
            "actor_id": str(actor_id),
            "method": "reviewed_regression_comparison",
            "submission_key": key,
            "request_hash": digest,
            "provenance": "administrator_review",
        },
    )


def list_findings(
    db: Session, issue_id: UUID, occurrence_id: UUID | None, limit: int, offset: int
) -> dict[str, Any]:
    if db.get(DiagnosticIssue, issue_id) is None:
        raise ValueError("issue_not_found")
    if occurrence_id is not None:
        occurrence = db.get(DiagnosticEvent, occurrence_id)
        if occurrence is None or occurrence.issue_id != issue_id:
            raise ValueError("occurrence_not_found")
    current = evidence_package(db, issue_id, occurrence_id)
    selected = (
        str(occurrence_id) if occurrence_id else (current.get("snapshot") or {}).get("event_id")
    )
    statement = (
        select(DebugRunEvent, DebugRun)
        .join(DebugRun)
        .join(DebugThread)
        .where(
            DebugRunEvent.kind == "finding_proposed",
            DebugThread.issue_id == issue_id,
            DebugThread.environment == diagnostics_environment(),
        )
    )
    if selected:
        statement = statement.where(DebugRun.evidence["occurrence_id"].as_string() == selected)
    rows = db.execute(
        statement.order_by(DebugRunEvent.created_at.desc(), DebugRunEvent.id.desc())
        .limit(limit + 1)
        .offset(offset)
    ).all()
    run_ids = [run.id for _, run in rows[:limit]]
    reviews = {
        event.payload["finding_id"]: event
        for event in db.scalars(
            select(DebugRunEvent).where(
                DebugRunEvent.run_id.in_(run_ids), DebugRunEvent.kind == "finding_verified"
            )
        )
    }
    tests: dict[UUID, list[dict[str, Any]]] = {}
    for event in db.scalars(
        select(DebugRunEvent)
        .where(DebugRunEvent.run_id.in_(run_ids), DebugRunEvent.kind == "tool_completed")
        .order_by(DebugRunEvent.sequence)
        .limit(1280)
    ):
        if event.payload.get("tool") != "fitician_run_tests":
            continue
        run = next(item for _, item in rows[:limit] if item.id == event.run_id)
        try:
            value = json.loads(event.payload.get("output", ""))
            passed = value.get("passed")
            if type(passed) is not bool:
                continue
            proof = _test_proof(db, run, event.id, passed)
        except (ValueError, TypeError, AttributeError):
            continue
        tests.setdefault(run.id, []).append(
            {
                "id": str(event.id),
                "passed": passed,
                "command": " ".join(str(value) for value in proof["command"])[:320],
            }
        )
    result = []
    for event, run in rows[:limit]:
        verification = reviews.get(str(event.id))
        stale = not event.payload.get("evidence_version") or (
            event.payload.get("evidence_version") != current.get("evidence_version")
        )
        result.append(
            {
                "id": str(event.id),
                "run_id": str(run.id),
                **{
                    key: event.payload.get(key)
                    for key in (
                        "classification",
                        "text",
                        "evidence_ids",
                        "occurrence_id",
                        "evidence_version",
                        "provenance",
                    )
                },
                "stale": stale,
                "can_verify": not stale
                and verification is None
                and run.state == "completed"
                and run.action == "prepare_fix"
                and event.payload.get("classification") != "next_check",
                "test_evidence": tests.get(run.id, []),
                "model": run.config_snapshot.get("agent_model_id")
                or run.config_snapshot.get("primary_model_id"),
                "created_at": event.created_at.isoformat(),
                "verification": (
                    {
                        "id": str(verification.id),
                        "created_at": verification.created_at.isoformat(),
                        **{
                            k: verification.payload[k]
                            for k in (
                                "actor_id",
                                "method",
                                "note",
                                "before_test_id",
                                "after_test_id",
                            )
                        },
                    }
                    if verification
                    else None
                ),
            }
        )
    return {"findings": result, "next_offset": offset + limit if len(rows) > limit else None}
