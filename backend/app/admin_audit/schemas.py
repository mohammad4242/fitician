from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.admin_audit.enums import AdminAuditAction


class AdminAuditActorSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    display_name: str | None
    email: str | None
    phone_number: str | None


class AdminAuditEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    action: AdminAuditAction
    actor: AdminAuditActorSummary | None
    target: AdminAuditActorSummary | None
    resource_type: str
    resource_key: str
    reason: str | None
    before_state: dict[str, object] | None
    after_state: dict[str, object] | None
    created_at: datetime
