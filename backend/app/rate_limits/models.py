from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DistributedRateLimitCounter(Base):
    """Hashed actor counter used when Redis is unavailable."""

    __tablename__ = "distributed_rate_limit_counters"
    __table_args__ = (
        UniqueConstraint(
            "namespace",
            "actor_hash",
            "operation",
            "window_started_at",
            name="uq_distributed_rate_limit_window",
        ),
        Index("ix_distributed_rate_limit_lookup", "namespace", "actor_hash", "operation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    namespace: Mapped[str] = mapped_column(String(48), nullable=False)
    actor_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

