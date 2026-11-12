"""Explicit public contracts for the separately authenticated laptop connection."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HeartbeatResponse(StrictResponse):
    connected: bool
    environment: str
    repository: str


class ConnectorJob(StrictResponse):
    id: UUID
    run_id: UUID
    thread_id: UUID
    lease_token: UUID
    tool: str = Field(pattern=r"^fitician_[a-z_]+$")
    arguments: dict[str, Any]
    action: Literal["analyze", "prepare_fix"]
    repository: str
    environment: str
    release_commit: str | None
    config: dict[str, Any]
    evidence: dict[str, Any]


class PollResponse(StrictResponse):
    job: ConnectorJob | None


class CallStatusResponse(StrictResponse):
    cancel_requested: bool
    state: str


class CompletionResponse(StrictResponse):
    stored: bool


class ProgressResponse(StrictResponse):
    cancel_requested: bool
    sequence: int
    evidence_id: UUID | None = None


class ProbeJob(StrictResponse):
    id: UUID
    model: str
    release_commit: str = Field(pattern=r"^[a-f0-9]{40}$")
    lease_token: UUID


class ProbePollResponse(StrictResponse):
    job: ProbeJob | None


class ProbeStatusResponse(StrictResponse):
    authorized: bool
