"""Durable, issue-scoped debugging conversations and execution audit."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DebugThread(Base):
    __tablename__ = "debug_threads"
    __table_args__ = (
        UniqueConstraint("issue_id", "environment", name="uq_debug_thread_issue_env"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("diagnostic_issues.id", ondelete="RESTRICT"), index=True
    )
    environment: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DebugMessage(Base):
    __tablename__ = "debug_messages"
    __table_args__ = (
        UniqueConstraint("thread_id", "submission_key", name="uq_debug_message_submission"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("debug_threads.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    submission_key: Mapped[str | None] = mapped_column(String(128))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DebugRun(Base):
    __tablename__ = "debug_runs"
    __table_args__ = (
        Index(
            "uq_debug_run_active_thread",
            "thread_id",
            unique=True,
            postgresql_where=text(
                "state IN ('queued','investigating','editing','testing',"
                "'awaiting_authorization','deploying','verifying')"
            ),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("debug_threads.id", ondelete="RESTRICT"), index=True
    )
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("debug_messages.id", ondelete="RESTRICT"), unique=True
    )
    state: Mapped[str] = mapped_column(String(32), default="queued")
    action: Mapped[str] = mapped_column(String(32), default="analyze")
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    lease_token: Mapped[UUID | None] = mapped_column()
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DebugRunEvent(Base):
    __tablename__ = "debug_run_events"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_debug_run_sequence"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("debug_runs.id", ondelete="RESTRICT"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DebugOperation(Base):
    __tablename__ = "debug_operations"
    __table_args__ = (
        UniqueConstraint("run_id", "submission_key", name="uq_debug_operation_submission"),
        CheckConstraint(
            "kind IN ('validate','publish_pr','deploy')", name="ck_debug_operation_kind"
        ),
        CheckConstraint(
            "kind <> 'deploy' OR (target_environment IS NOT NULL AND "
            "target_environment IN ('production-iran','production-germany'))",
            name="ck_debug_operation_deployment_target",
        ),
        CheckConstraint(
            "state IN ('queued','preparing','dispatching','uncertain','running',"
            "'awaiting_authorization','deploying','verifying','succeeded','failed','cancelled','blocked')",
            name="ck_debug_operation_state",
        ),
        Index("ix_debug_operation_claim", "environment", "state", "lease_until"),
        Index(
            "uq_debug_operation_deployment_target",
            "environment",
            "target_environment",
            unique=True,
            postgresql_where=text(
                "kind = 'deploy' AND state IN ('queued','preparing','dispatching','uncertain',"
                "'running','awaiting_authorization','deploying','verifying')"
            ),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("debug_runs.id", ondelete="RESTRICT"), index=True
    )
    occurrence_id: Mapped[UUID | None] = mapped_column()
    worker_id: Mapped[UUID] = mapped_column(ForeignKey("debug_connectors.id", ondelete="RESTRICT"))
    environment: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(32), default="queued")
    submission_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    request: Mapped[dict[str, Any]] = mapped_column(JSON)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    target_environment: Mapped[str | None] = mapped_column(String(64))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    lease_token: Mapped[UUID | None] = mapped_column()
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DebugConnector(Base):
    __tablename__ = "debug_connectors"
    __table_args__ = (
        CheckConstraint("kind IN ('runtime','automation')", name="ck_debug_connector_kind"),
        Index(
            "uq_debug_automation_worker_env",
            "environment",
            unique=True,
            postgresql_where=text("kind = 'automation' AND revoked = false"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(16), default="runtime", server_default="runtime")
    environment: Mapped[str] = mapped_column(String(64), index=True)
    repository: Mapped[str] = mapped_column(String(200))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DebugConnectorCall(Base):
    __tablename__ = "debug_connector_calls"
    __table_args__ = (UniqueConstraint("run_id", "call_key", name="uq_debug_connector_run_call"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    connector_id: Mapped[UUID] = mapped_column(
        ForeignKey("debug_connectors.id", ondelete="RESTRICT"), index=True
    )
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("debug_runs.id", ondelete="RESTRICT"), index=True
    )
    progress_sequence: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    call_key: Mapped[str] = mapped_column(String(128))
    tool: Mapped[str] = mapped_column(String(80))
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(32), default="queued")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    lease_token: Mapped[UUID | None] = mapped_column()
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DebugConnectorProbe(Base):
    __tablename__ = "debug_connector_probes"
    __table_args__ = (
        Index(
            "uq_debug_probe_active_connector",
            "connector_id",
            unique=True,
            postgresql_where=text("state IN ('queued','running')"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    connector_id: Mapped[UUID] = mapped_column(
        ForeignKey("debug_connectors.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    model: Mapped[str] = mapped_column(String(300))
    release_commit: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(32), default="queued")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    lease_token: Mapped[UUID | None] = mapped_column()
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
