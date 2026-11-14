"""Explicit administrator deployment actions; deliberately absent from the model catalog."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from app.admin.dependencies import AdminUser, require_admin
from app.auth.dependencies import DatabaseSession, require_authenticated_mutation

from .automation import operation_json
from .connector_schemas import OperationResponse
from .deployment import authorize_deployment, queue_deployment

router = APIRouter(dependencies=[Depends(require_admin), Depends(require_authenticated_mutation)])
Key = Annotated[str, Header(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")]


class DeploymentPreviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    publication_id: UUID
    observation_id: UUID
    ci_run_id: int = Field(gt=0)


class DeploymentAuthorizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def failure(db: DatabaseSession, error: ValueError | IntegrityError) -> HTTPException:
    db.rollback()
    if isinstance(error, IntegrityError):
        return HTTPException(409, detail={"code": "deployment_target_busy"})
    code = str(error)
    return HTTPException(404 if code.endswith("not_found") else 409, detail={"code": code})


@router.post("/issues/{issue_id}/deployments", response_model=OperationResponse)
def preview_deployment(
    issue_id: UUID,
    payload: DeploymentPreviewInput,
    actor: AdminUser,
    db: DatabaseSession,
    idempotency_key: Key,
) -> dict[str, Any]:
    try:
        row = queue_deployment(
            db,
            issue_id,
            payload.publication_id,
            payload.observation_id,
            actor.id,
            idempotency_key,
            payload.ci_run_id,
        )
        db.commit()
        return operation_json(row)
    except (ValueError, IntegrityError) as error:
        raise failure(db, error) from None


@router.post(
    "/issues/{issue_id}/deployments/{operation_id}/authorize", response_model=OperationResponse
)
def approve_deployment(
    issue_id: UUID,
    operation_id: UUID,
    payload: DeploymentAuthorizationInput,
    actor: AdminUser,
    db: DatabaseSession,
    idempotency_key: Key,
) -> dict[str, Any]:
    try:
        row = authorize_deployment(
            db, issue_id, operation_id, actor.id, idempotency_key, payload.preview_sha256
        )
        db.commit()
        return operation_json(row)
    except (ValueError, IntegrityError) as error:
        raise failure(db, error) from None
