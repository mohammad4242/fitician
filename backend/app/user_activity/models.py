from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserActivityEvent(Base):
    __tablename__ = "user_activity_events"
    __table_args__ = (
        UniqueConstraint("deduplication_key", name="uq_user_activity_events_deduplication_key"),
        Index("ix_user_activity_events_user_id_occurred_at", "user_id", "occurred_at"),
        Index("ix_user_activity_events_event_type_occurred_at", "event_type", "occurred_at"),
        Index(
            "ix_user_activity_events_user_resource",
            "user_id",
            "event_type",
            "resource_type",
            "resource_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(128))
    safe_metadata: Mapped[dict[str, str | int | float | bool]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deduplication_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
