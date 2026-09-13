from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.admin.dependencies import require_admin
from app.admin_audit.enums import AdminAuditAction
from app.admin_audit.schemas import AdminAuditEventResponse
from app.admin_audit.service import list_admin_audit_events
from app.auth.dependencies import DatabaseSession

router = APIRouter(
    prefix="/api/v1/admin/audit",
    tags=["admin-audit"],
    dependencies=[Depends(require_admin)],
)


def _read_events(
    db: DatabaseSession,
    action: AdminAuditAction | None,
    actor_user_id: UUID | None,
    target_user_id: UUID | None,
    resource_type: str | None,
    from_datetime: datetime | None,
    to_datetime: datetime | None,
    limit: int,
    offset: int,
) -> list[AdminAuditEventResponse]:
    return list_admin_audit_events(
        db,
        action=action,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        resource_type=resource_type,
        from_datetime=from_datetime,
        to_datetime=to_datetime,
        limit=limit,
        offset=offset,
    )


@router.get("", response_model=list[AdminAuditEventResponse])
@router.get("/events", response_model=list[AdminAuditEventResponse])
def read_audit_events(
    db: DatabaseSession,
    action: AdminAuditAction | None = None,
    actor_user_id: UUID | None = None,
    target_user_id: UUID | None = None,
    resource_type: Annotated[str | None, Query(max_length=100)] = None,
    from_datetime: datetime | None = None,
    to_datetime: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminAuditEventResponse]:
    return _read_events(
        db,
        action,
        actor_user_id,
        target_user_id,
        resource_type,
        from_datetime,
        to_datetime,
        limit,
        offset,
    )
