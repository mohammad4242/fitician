from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.admin_audit.enums import AdminAuditAction
from app.auth.models import User  # noqa: F401
from app.database.base import Base


def _enum_values(members: type[PyEnum]) -> list[str]:
    return [member.value for member in members]


class AdminAuditEvent(Base):
    """Append-only business audit record for an administrator mutation."""

    __tablename__ = "admin_audit_events"
    __table_args__ = (
        Index("ix_admin_audit_events_created_at", "created_at"),
        Index("ix_admin_audit_events_actor_created_at", "actor_user_id", "created_at"),
        Index("ix_admin_audit_events_target_created_at", "target_user_id", "created_at"),
        Index("ix_admin_audit_events_resource", "resource_type", "resource_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    target_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[AdminAuditAction] = mapped_column(
        Enum(
            AdminAuditAction,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=_enum_values,
            length=128,
        ),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_key: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    before_state: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
