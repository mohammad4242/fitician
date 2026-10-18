from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DiagnosticIssue(Base):
    __tablename__ = "diagnostic_issues"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_diagnostic_issue_fingerprint"),
        Index("ix_diagnostic_issues_last_seen", "last_seen"),
        Index("ix_diagnostic_issues_status_severity", "status", "severity"),
        Index("ix_diagnostic_issues_seen_status_severity", "last_seen", "status", "severity"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    component: Mapped[str] = mapped_column(String(80), nullable=False)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    exception_type: Mapped[str | None] = mapped_column(String(100))
    source_location: Mapped[str | None] = mapped_column(String(160))
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    regression_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_alert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DiagnosticEvent(Base):
    __tablename__ = "diagnostic_events"
    __table_args__ = (
        Index("ix_diagnostic_events_timestamp", "timestamp"),
        Index("ix_diagnostic_events_trace_span", "trace_id", "span_id", "timestamp"),
        Index("ix_diagnostic_events_record_time", "record_type", "timestamp"),
        Index("ix_diagnostic_events_resource_attempt", "resource_id", "component", "retry_count"),
        Index("ix_diagnostic_events_request_timestamp", "request_id", "timestamp"),
        Index("ix_diagnostic_events_operation_id_timestamp", "operation_id", "timestamp"),
        Index(
            "ix_diagnostic_events_operation_outcome_timestamp", "operation", "outcome", "timestamp"
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    issue_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("diagnostic_issues.id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    request_id: Mapped[str | None] = mapped_column(String(128))
    operation_id: Mapped[str | None] = mapped_column(String(128))
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    app_version: Mapped[str | None] = mapped_column(String(64))
    origin_platform: Mapped[str | None] = mapped_column(String(32))
    trace_id: Mapped[str | None] = mapped_column(String(32))
    span_id: Mapped[str | None] = mapped_column(String(16))
    parent_span_id: Mapped[str | None] = mapped_column(String(16))
    record_type: Mapped[str] = mapped_column(String(8), default="event", server_default="event")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offset_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    clock_domain: Mapped[str | None] = mapped_column(String(64))
    expected_span_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    dropped_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    component: Mapped[str] = mapped_column(String(80), nullable=False)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str | None] = mapped_column(String(64))
    build: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    exception_type: Mapped[str | None] = mapped_column(String(100))
    source_location: Mapped[str | None] = mapped_column(String(160))
    input_fingerprint: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    http_status: Mapped[int | None] = mapped_column(Integer)
    os_version: Mapped[str | None] = mapped_column(String(40))


class DiagnosticAlert(Base):
    __tablename__ = "diagnostic_alerts"
    __table_args__ = (Index("ix_diagnostic_alerts_created_at", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("diagnostic_issues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str] = mapped_column(String(40), nullable=False)


class DiagnosticStatusHistory(Base):
    __tablename__ = "diagnostic_status_history"
    __table_args__ = (Index("ix_diagnostic_status_history_created_at", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("diagnostic_issues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    previous_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
