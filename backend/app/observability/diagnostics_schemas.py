from __future__ import annotations

import re
from datetime import datetime
from enum import IntEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class DiagnosticHours(IntEnum):
    HOUR = 1
    DAY = 24
    WEEK = 168
    MONTH = 720


Category = Literal[
    "application_bug",
    "api_failure",
    "database_failure",
    "infrastructure_failure",
    "provider_failure",
    "engine_validation",
    "invalid_input",
    "business_rejection",
    "quota_limit",
    "safety_restriction",
    "auth_failure",
    "client_runtime",
    "job_failure",
    "interrupted",
    "unknown",
]
Platform = Literal[
    "web", "ios_pwa", "android", "ios", "backend", "worker", "database", "infrastructure", "unknown"
]
Severity = Literal["info", "warning", "error", "critical"]
Confidence = Literal["unknown", "likely", "confirmed"]
IssueStatus = Literal["new", "investigating", "resolved", "ignored"]
ClientErrorCode = Literal[
    "CLIENT_RUNTIME_ERROR",
    "API_REQUEST_FAILED",
    "CLIENT_UNHANDLED_REJECTION",
    "CLIENT_RENDER_ERROR",
]
Token = Annotated[
    str, StringConstraints(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")
]
ClientToken = Annotated[
    str, StringConstraints(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventInput(StrictModel):
    event_id: UUID | None = None
    request_id: str | None = Field(default=None, max_length=128)
    operation_id: str | None = Field(default=None, max_length=128)
    component: ClientToken
    operation: ClientToken
    stage: ClientToken
    platform: Platform
    version: Token | None = None
    build: Token | None = None
    category: Category
    severity: Severity
    error_code: Token
    exception_type: (
        Annotated[str, StringConstraints(max_length=100, pattern=r"^[A-Za-z][A-Za-z0-9_.]+$")]
        | None
    ) = None
    source_location: Annotated[str, StringConstraints(max_length=160)] | None = None
    input_fingerprint: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")] | None = None
    resource_id: UUID | None = None
    outcome: Literal[
        "started",
        "stage",
        "success",
        "failure",
        "timeout",
        "cancelled",
        "reused",
        "pending_review",
        "blocked",
    ]
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    retry_count: int = Field(default=0, ge=0, le=100)
    http_status: int | None = Field(default=None, ge=100, le=599)
    os_version: (
        Annotated[str, StringConstraints(max_length=40, pattern=r"^[A-Za-z0-9_.:-]+$")] | None
    ) = None

    @field_validator("request_id", "operation_id")
    @classmethod
    def safe_correlation_id(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
            raise ValueError("invalid correlation token")
        return value

    @field_validator("source_location")
    @classmethod
    def sanitize_source_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        match = re.search(r"(?:^|[/\\])([^/\\]+\.py|[^/\\]+\.(?:tsx?|jsx?)):(\d{1,7})$", value)
        if match is None:
            raise ValueError("source location must be basename:line")
        return f"{match.group(1)}:{match.group(2)}"


class ClientEventInput(StrictModel):
    event_id: UUID
    platform: Literal["android", "ios_pwa", "web"]
    component: Literal[
        "WebTransport", "Window", "ReactRoot", "NativeTransport", "ReactNativeRuntime"
    ]
    operation: Literal[
        "request",
        "download",
        "upload",
        "error_event",
        "promise_rejection",
        "render",
        "global_error",
        "registration",
        "login",
        "authentication",
        "onboarding",
        "workout_generation",
        "nutrition",
        "body_analysis",
        "notifications",
        "subscriptions",
        "entitlements",
        "media",
    ]
    stage: Literal[
        "failed", "response_failed", "transport_failed", "unhandled", "fatal", "caught", "uncaught"
    ]
    error_code: ClientErrorCode
    request_id: (
        Annotated[str, StringConstraints(max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")] | None
    ) = None
    version: (
        Annotated[
            str,
            StringConstraints(
                max_length=64,
                pattern=r"^[0-9]{1,4}(?:\.[0-9]{1,4}){1,3}(?:[-+][A-Za-z0-9.-]{1,32})?$",
            ),
        ]
        | None
    ) = None
    build: (
        Annotated[
            str, StringConstraints(max_length=64, pattern=r"^(?:[0-9]{1,10}|[a-fA-F0-9]{7,64})$")
        ]
        | None
    ) = None
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    http_status: int | None = Field(default=None, ge=100, le=599)
    os_version: (
        Annotated[str, StringConstraints(max_length=40, pattern=r"^[A-Za-z0-9_.:-]+$")] | None
    ) = None


class ClientBatch(StrictModel):
    events: list[ClientEventInput] = Field(min_length=1, max_length=10)


class IssueStatusUpdate(StrictModel):
    status: IssueStatus
    note: str | None = Field(default=None, max_length=1000)


class IssueResponse(StrictModel):
    id: UUID
    fingerprint: str
    component: str
    operation: str
    stage: str
    platform: str
    severity: str
    category: str
    error_code: str
    exception_type: str | None
    source_location: str | None
    confidence: str
    title: str
    first_seen: datetime
    last_seen: datetime
    count: int
    status: str
    regression_count: int
    last_alert_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class EventResponse(StrictModel):
    id: UUID = Field(validation_alias="id", serialization_alias="event_id")
    issue_id: UUID | None
    timestamp: datetime
    request_id: str | None
    operation_id: str | None
    user_id: UUID | None
    component: str
    operation: str
    stage: str
    platform: str
    version: str | None
    build: str | None
    category: str
    severity: str
    error_code: str
    exception_type: str | None
    source_location: str | None
    input_fingerprint: str | None
    resource_id: UUID | None
    outcome: str
    duration_ms: int | None
    retry_count: int
    http_status: int | None
    os_version: str | None

    model_config = ConfigDict(from_attributes=True)


class StatusHistoryResponse(StrictModel):
    id: UUID
    issue_id: UUID
    actor_user_id: UUID | None
    previous_status: str
    new_status: str
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(StrictModel):
    id: UUID
    issue_id: UUID
    created_at: datetime
    reason: str

    model_config = ConfigDict(from_attributes=True)


class TrendPoint(StrictModel):
    timestamp: datetime
    count: int


class PlatformCount(StrictModel):
    platform: str
    count: int


class OverviewResponse(StrictModel):
    hours: int
    event_count: int
    issue_count: int
    failure_count: int
    critical_count: int
    new_issue_count: int
    affected_users: int
    error_rate: float | None
    http_response_count: dict[str, int]
    infrastructure: dict[str, str | None]
    trend: list[TrendPoint]
    platforms: list[PlatformCount]


class IssueDetailResponse(StrictModel):
    issue: IssueResponse
    events: list[EventResponse]
    status_history: list[StatusHistoryResponse]
    affected_user_count: int
    affected_versions: list[str]


class GenerationSummary(StrictModel):
    operation: str
    terminal_count: int
    success_count: int
    success_rate: float | None
    average_duration_ms: float | None
    outcomes: dict[str, int]


class GenerationMetricsResponse(StrictModel):
    hours: int
    operations: list[GenerationSummary]
    failure_reasons: list[dict[str, str | int]]
    incomplete_attempts: int
    quota_integrity: dict[str, int]
    engine_versions: list[dict[str, str | int]]


class InfrastructureSignal(StrictModel):
    component: str
    status: str
    observed_at: datetime | None
    evidence: str
    business_operation_verified: bool = False


class InfrastructureResponse(StrictModel):
    signals: list[InfrastructureSignal]
    queues: dict[str, dict[str, int]]
