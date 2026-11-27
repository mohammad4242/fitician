"""Administrator reviews are separate from the agent's ability to propose a finding."""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.admin.dependencies import AdminUser, require_admin
from app.auth.dependencies import DatabaseSession, require_authenticated_mutation

from .findings import FindingReview, list_findings, verify_finding

router = APIRouter(dependencies=[Depends(require_admin)])


class VerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    actor_id: UUID
    method: Literal["reviewed_regression_comparison"]
    note: str
    before_test_id: UUID
    after_test_id: UUID
    created_at: datetime


class TestProofSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    passed: bool
    command: str


class ReviewResponse(BaseModel):
    id: UUID
    state: Literal["reviewed_finding"]


class FindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    run_id: UUID
    classification: Literal["observed_fact", "hypothesis", "next_check"]
    text: str
    evidence_ids: list[UUID]
    occurrence_id: UUID | None
    evidence_version: str | None
    provenance: str
    stale: bool
    model: str | None
    created_at: datetime
    verification: VerificationResponse | None
    can_verify: bool
    test_evidence: list[TestProofSummary]


class FindingsPage(BaseModel):
    findings: list[FindingResponse]
    next_offset: int | None


@router.get("/issues/{issue_id}/findings", response_model=FindingsPage)
def findings(
    issue_id: UUID,
    db: DatabaseSession,
    occurrence_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> dict[str, Any]:
    try:
        return list_findings(db, issue_id, occurrence_id, limit, offset)
    except ValueError as error:
        raise HTTPException(404, detail={"code": str(error)}) from None


@router.post(
    "/issues/{issue_id}/findings/{finding_id}/verify",
    response_model=ReviewResponse,
    dependencies=[Depends(require_authenticated_mutation)],
)
def verify(
    issue_id: UUID,
    finding_id: UUID,
    payload: FindingReview,
    actor: AdminUser,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str, Header(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    ],
) -> dict[str, str]:
    try:
        event = verify_finding(db, issue_id, finding_id, actor.id, idempotency_key, payload)
        db.commit()
        return {"id": str(event.id), "state": "reviewed_finding"}
    except ValueError as error:
        db.rollback()
        raise HTTPException(
            404 if str(error).endswith("not_found") else 409, detail={"code": str(error)}
        ) from None
