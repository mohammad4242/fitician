from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.access_management.enums import AccessCampaignKind
from app.entitlements.catalog import package_definition
from app.entitlements.enums import AccessPackageCode, EntitlementCode, GrantSource

AccessTermWeeks = Literal[4, 6, 8]


def _trim(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _normalize_optional_text(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return value


PUBLIC_MARKETING_FIELDS = (
    "public_badge_fa",
    "public_badge_en",
    "public_title_fa",
    "public_title_en",
    "public_message_fa",
    "public_message_en",
    "public_cta_fa",
    "public_cta_en",
)

PUBLIC_COPY_FIELDS = PUBLIC_MARKETING_FIELDS[2:]


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
    public_badge_fa: str | None = Field(default=None, max_length=80)
    public_badge_en: str | None = Field(default=None, max_length=80)
    public_title_fa: str | None = Field(default=None, max_length=160)
    public_title_en: str | None = Field(default=None, max_length=160)
    public_message_fa: str | None = Field(default=None, max_length=1000)
    public_message_en: str | None = Field(default=None, max_length=1000)
    public_cta_fa: str | None = Field(default=None, max_length=80)
    public_cta_en: str | None = Field(default=None, max_length=80)
    show_on_landing: bool = False
    show_on_register: bool = False

    _normalize_name = field_validator("name", mode="before")(_trim)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        return _normalize_optional_text(value)

    @field_validator(*PUBLIC_MARKETING_FIELDS, mode="before")
    @classmethod
    def normalize_public_copy(cls, value: object) -> object:
        return _normalize_optional_text(value)

    @model_validator(mode="after")
    def validate_semantics(self) -> "AccessCampaignCreateRequest":
        _validate_campaign_semantics(
            self.kind,
            self.package_code,
            self.duration_days,
            self.term_weeks,
            self.available_from,
            self.available_until,
            self.max_total_redemptions,
            show_on_landing=self.show_on_landing,
            show_on_register=self.show_on_register,
            public_copy={field: getattr(self, field) for field in PUBLIC_COPY_FIELDS},
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
    max_total_redemptions: int | None = Field(default=None, gt=0)
    public_badge_fa: str | None = Field(default=None, max_length=80)
    public_badge_en: str | None = Field(default=None, max_length=80)
    public_title_fa: str | None = Field(default=None, max_length=160)
    public_title_en: str | None = Field(default=None, max_length=160)
    public_message_fa: str | None = Field(default=None, max_length=1000)
    public_message_en: str | None = Field(default=None, max_length=1000)
    public_cta_fa: str | None = Field(default=None, max_length=80)
    public_cta_en: str | None = Field(default=None, max_length=80)
    show_on_landing: bool | None = None
    show_on_register: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return None if value is None else _trim(str(value))

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        return _normalize_optional_text(value)

    @field_validator(*PUBLIC_MARKETING_FIELDS, mode="before")
    @classmethod
    def normalize_public_copy(cls, value: object) -> object:
        return _normalize_optional_text(value)


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
    public_badge_fa: str | None
    public_badge_en: str | None
    public_title_fa: str | None
    public_title_en: str | None
    public_message_fa: str | None
    public_message_en: str | None
    public_cta_fa: str | None
    public_cta_en: str | None
    show_on_landing: bool
    show_on_register: bool
    redemption_count: int
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class PublicSignupCampaignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    package_code: AccessPackageCode
    duration_days: int
    term_weeks: AccessTermWeeks | None
    available_until: datetime | None
    public_badge_fa: str | None
    public_badge_en: str | None
    public_title_fa: str | None
    public_title_en: str | None
    public_message_fa: str | None
    public_message_en: str | None
    public_cta_fa: str | None
    public_cta_en: str | None
    show_on_landing: bool
    show_on_register: bool


class ManualCampaignRedemptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return _trim(value)


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
        return _trim(value)

    @field_validator("package_code")
    @classmethod
    def validate_package_code(cls, value: AccessPackageCode) -> AccessPackageCode:
        if package_definition(value).kind.value != "subscription":
            raise ValueError("Admin grants support normal subscription packages only")
        return value

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
        return _trim(value)


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
    kind: AccessCampaignKind,
    package_code: AccessPackageCode,
    duration_days: int,
    term_weeks: AccessTermWeeks | None,
    available_from: datetime | None,
    available_until: datetime | None,
    max_total_redemptions: int | None,
    *,
    show_on_landing: bool = False,
    show_on_register: bool = False,
    public_copy: dict[str, str | None] | None = None,
    allow_legacy_launch_trial: bool = False,
) -> None:
    if package_code is AccessPackageCode.FREE:
        raise ValueError("Campaign package cannot be free")
    if package_code is AccessPackageCode.LAUNCH_TRIAL and not allow_legacy_launch_trial:
        raise ValueError("New campaigns cannot use the launch_trial package")
    if (
        kind is AccessCampaignKind.MANUAL_PROMOTION
        and package_code is AccessPackageCode.LAUNCH_TRIAL
    ):
        raise ValueError("manual_promotion campaigns cannot use the launch_trial package")
    if EntitlementCode.TRAINING_PLAN_GENERATE in package_definition(package_code).entitlements:
        if term_weeks is None:
            raise ValueError("term_weeks is required for training access")
        if duration_days < term_weeks * 7:
            raise ValueError("duration_days must cover the selected training term")
    if (
        available_from is not None
        and available_until is not None
        and available_until < available_from
    ):
        raise ValueError("available_until must be after available_from")
    if max_total_redemptions is not None and max_total_redemptions < 1:
        raise ValueError("max_total_redemptions must be positive")
    if kind not in {AccessCampaignKind.SIGNUP_BONUS, AccessCampaignKind.MANUAL_PROMOTION}:
        raise ValueError("Unsupported campaign kind")
    if kind is AccessCampaignKind.MANUAL_PROMOTION and (show_on_landing or show_on_register):
        raise ValueError("manual_promotion campaigns cannot be public")
    if kind is AccessCampaignKind.SIGNUP_BONUS and (show_on_landing or show_on_register):
        copy = public_copy or {}
        missing = [field for field in PUBLIC_COPY_FIELDS if not copy.get(field)]
        if missing:
            raise ValueError(f"Public campaign copy is required: {missing[0]}")
