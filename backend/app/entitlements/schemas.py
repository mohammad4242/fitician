from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.entitlements.enums import (
    AccessPackageCode,
    AccessPackageKind,
    EntitlementCode,
    GrantSource,
)


class ProductQuotaPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entitlement: EntitlementCode
    limit: int
    window_days: int


class ProductCatalogItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: AccessPackageCode
    kind: AccessPackageKind
    is_purchasable: bool
    entitlements: list[EntitlementCode]
    quota_policies: list[ProductQuotaPolicyResponse]


class AccessGrantSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    package_code: AccessPackageCode
    source: GrantSource
    starts_at: datetime
    ends_at: datetime | None
    revoked_at: datetime | None


class TrialStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool
    ends_at: datetime | None


class QuotaStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entitlement: EntitlementCode
    limit: int
    used: int
    remaining: int
    window_days: int
    reset_at: datetime


class EntitlementStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    granted: list[EntitlementCode]
    quotas: list[QuotaStatusResponse]


class EntitlementSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_package: AccessPackageCode
    active_packages: list[AccessPackageCode]
    trial: TrialStateResponse
    entitlements: EntitlementStateResponse
    grants: list[AccessGrantSummaryResponse]
