"""Immutable occurrence evidence; external grouping never replaces local fingerprints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DiagnosticEvidenceSnapshot(Base):
    __tablename__ = "diagnostic_evidence_snapshots"
    __table_args__ = (UniqueConstraint("event_id", name="uq_diagnostic_evidence_event"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("diagnostic_events.id", ondelete="RESTRICT"))
    issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("diagnostic_issues.id", ondelete="RESTRICT"), index=True
    )
    evidence_version: Mapped[str] = mapped_column(String(64))
    redaction_version: Mapped[str] = mapped_column(String(32), default="allowlist-v1")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    sentry_event_id: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiagnosticExternalEvent(Base):
    __tablename__ = "diagnostic_external_events"
    __table_args__ = (
        UniqueConstraint("project_id", "external_event_id", name="uq_diagnostic_external_event"),
        Index("ix_diagnostic_external_event_local", "local_event_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(String(100))
    external_event_id: Mapped[str] = mapped_column(String(32))
    external_issue_id: Mapped[str | None] = mapped_column(String(100))
    local_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("diagnostic_events.id", ondelete="SET NULL")
    )
    environment: Mapped[str] = mapped_column(String(64))
    source_evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column()
    sync_state: Mapped[str] = mapped_column(String(32), default="pending")
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DiagnosticExternalIssueLink(Base):
    __tablename__ = "diagnostic_external_issue_links"
    __table_args__ = (
        UniqueConstraint(
            "issue_id",
            "project_id",
            "external_issue_id",
            "environment",
            name="uq_diagnostic_external_issue_link",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("diagnostic_issues.id", ondelete="RESTRICT"), index=True
    )
    project_id: Mapped[str] = mapped_column(String(100))
    external_issue_id: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(64))
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
