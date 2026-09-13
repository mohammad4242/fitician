from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.access_management.enums import AccessCampaignKind
from app.entitlements.catalog import package_definition
from app.entitlements.enums import AccessPackageCode, EntitlementCode, GrantSource

AccessTermWeeks = Literal[4, 6, 8]


def _trim(value: str) -> str:
    return value.strip()


class AccessCampaignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    kind: AccessCampaignKind
    package_code: AccessPackageCode
    duration_days: int = Field(ge=1, le=3650)
    term_weeks: AccessTermWeeks | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None
    is_active: bool = False
    max_total_redemptions: int | None = Field(default=None, gt=0)

    _normalize_name = field_validator("name", mode="before")(_trim)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        return None if value is None else _trim(str(value))

    @model_validator(mode="after")
    def validate_semantics(self) -> "AccessCampaignCreateRequest":
        _validate_campaign_semantics(
            self.package_code,
            self.term_weeks,
            self.available_from,
            self.available_until,
        )
        return self


class AccessCampaignUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    kind: AccessCampaignKind | None = None
    package_code: AccessPackageCode | None = None
    duration_days: int | None = Field(default=None, ge=1, le=3650)
    term_weeks: AccessTermWeeks | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None
    is_active: bool | None = None
    max_total_redemptions: int | None = Field(default=None, gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return None if value is None else _trim(str(value))

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        return None if value is None else _trim(str(value))


class AccessCampaignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    name: str
    description: str | None
    kind: AccessCampaignKind
    package_code: AccessPackageCode
    duration_days: int
    term_weeks: AccessTermWeeks | None
    available_from: datetime | None
    available_until: datetime | None
    is_active: bool
    max_total_redemptions: int | None
    redemption_count: int
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ManualCampaignRedemptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return _trim(str(value))


class AdminGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_code: AccessPackageCode
    term_weeks: AccessTermWeeks | None = None
    starts_at: datetime | None = None
    ends_at: datetime
    reason: str = Field(min_length=1, max_length=500)
    client_idempotency_key: str = Field(min_length=1, max_length=255)

    @field_validator("reason", "client_idempotency_key", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _trim(str(value))

    @model_validator(mode="after")
    def validate_dates(self) -> "AdminGrantRequest":
        if (
            self.starts_at is not None
            and self.ends_at.tzinfo is not None
            and self.starts_at.tzinfo is not None
            and self.ends_at <= self.starts_at
        ):
            raise ValueError("ends_at must be after starts_at")
        return self


class RevokeGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return _trim(str(value))


class AdminMemberSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    display_name: str | None
    email: str | None
    phone_number: str | None
    created_at: datetime
    primary_package: AccessPackageCode
    active_packages: list[AccessPackageCode]
    trial_active: bool
    trial_ends_at: datetime | None
    paid_access_end: datetime | None


class AdminEntitlementSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_package: AccessPackageCode
    active_packages: list[AccessPackageCode]
    granted_entitlements: list[EntitlementCode]
    trial_active: bool
    trial_ends_at: datetime | None


class AdminGrantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    package_code: AccessPackageCode
    source: GrantSource
    term_weeks: AccessTermWeeks | None
    starts_at: datetime
    ends_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    status: Literal["active", "future", "expired", "revoked"]
    is_currently_active: bool
    billing_order_id: UUID | None
    campaign_id: UUID | None
    campaign_name: str | None


class AdminUserAccessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member: AdminMemberSummaryResponse
    entitlement_snapshot: AdminEntitlementSnapshotResponse
    grants: list[AdminGrantResponse]


class AdminCampaignRedemptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign: AccessCampaignResponse
    grant: AdminGrantResponse


def _validate_campaign_semantics(
    package_code: AccessPackageCode,
    term_weeks: AccessTermWeeks | None,
    available_from: datetime | None,
    available_until: datetime | None,
) -> None:
    if package_code is AccessPackageCode.FREE:
        raise ValueError("Campaign package cannot be free")
    if EntitlementCode.TRAINING_PLAN_GENERATE in package_definition(package_code).entitlements:
        if term_weeks is None:
            raise ValueError("term_weeks is required for training access")
    if package_code is AccessPackageCode.LAUNCH_TRIAL and term_weeks != 4:
        raise ValueError("Launch Trial campaigns require term_weeks=4")
    if (
        available_from is not None
        and available_until is not None
        and available_until < available_from
    ):
        raise ValueError("available_until must be after available_from")
