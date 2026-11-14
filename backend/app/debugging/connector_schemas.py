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
    ci_available: bool = False


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


class ServerEvidenceResponse(StrictResponse):
    evidence_id: UUID
    output: str = Field(max_length=28000)


class StoredServerEvidenceResponse(StrictResponse):
    state: Literal["recorded", "not_collected"]
    evidence_id: UUID | None = None
    output: str | None = Field(default=None, max_length=28000)


class OperationResponse(StrictResponse):
    id: UUID
    run_id: UUID
    occurrence_id: UUID | None
    environment: str
    target_environment: Literal["production-iran", "production-germany"] | None = None
    kind: Literal["validate", "publish_pr", "deploy", "observe"]
    state: str
    error_code: str | None
    cancel_requested: bool
    profile: str | None
    purpose: Literal[
        "connection_check",
        "repair_validation",
        "repair_publication",
        "server_observation",
        "repair_deployment",
    ]
    snapshot_digest: str | None
    result: dict[str, Any]
    created_at: str
    updated_at: str


class OperationPage(StrictResponse):
    operations: list[OperationResponse]


class AutomationAvailability(StrictResponse):
    worker_id: UUID | None
    worker_name: str | None
    connected: bool
    configured: bool
    live_validation_verified: bool
    policy_commit: str | None
    error_code: str | None


class AutomationHeartbeatResponse(StrictResponse):
    connected: bool
    environment: str


class AutomationJob(OperationResponse):
    lease_token: UUID
    request: dict[str, Any]
    repository: str


class AutomationPollResponse(StrictResponse):
    job: AutomationJob | None


class AutomationAuthorizationResponse(StrictResponse):
    authorized: bool
    cancel_requested: bool
    state: str


class AutomationProgressResponse(StrictResponse):
    operation: OperationResponse
    disposition: Literal[
        "recorded", "reconcile_only", "dispatch_once", "cancel_once", "publish_once"
    ]
