from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from app.entitlements.enums import (
    AccessPackageCode,
    AccessPackageKind,
    EntitlementCode,
)


@dataclass(frozen=True, slots=True)
class QuotaPolicy:
    limit: int
    window_days: int


@dataclass(frozen=True, slots=True)
class PackageDefinition:
    code: AccessPackageCode
    kind: AccessPackageKind
    is_purchasable: bool
    entitlements: frozenset[EntitlementCode]


_TRAINING: Final = frozenset(
    {
        EntitlementCode.TRAINING_PLAN_GENERATE,
        EntitlementCode.TRAINING_CYCLE_MANAGE,
        EntitlementCode.BODY_ANALYSIS_RUN,
    }
)
_TRAINING_COACH: Final = _TRAINING | frozenset({EntitlementCode.TRAINING_COACH_REVIEW})
_NUTRITION: Final = frozenset(
    {
        EntitlementCode.NUTRITION_PLAN_GENERATE,
        EntitlementCode.NUTRITION_PLAN_MANAGE,
        EntitlementCode.NUTRITION_FOOD_PHOTO_ANALYZE,
        EntitlementCode.BODY_ANALYSIS_RUN,
    }
)
_NUTRITION_PHYSICIAN: Final = _NUTRITION | frozenset(
    {
        EntitlementCode.NUTRITION_PHYSICIAN_REVIEW,
        EntitlementCode.NUTRITION_LABS_MANAGE,
        EntitlementCode.NUTRITION_SUPPLEMENTS_MANAGE,
    }
)


PACKAGE_CATALOG: Final = MappingProxyType(
    {
        AccessPackageCode.FREE: PackageDefinition(
            code=AccessPackageCode.FREE,
            kind=AccessPackageKind.FREE,
            is_purchasable=False,
            entitlements=frozenset(),
        ),
        AccessPackageCode.TRAINING: PackageDefinition(
            code=AccessPackageCode.TRAINING,
            kind=AccessPackageKind.SUBSCRIPTION,
            is_purchasable=True,
            entitlements=_TRAINING,
        ),
        AccessPackageCode.TRAINING_COACH: PackageDefinition(
            code=AccessPackageCode.TRAINING_COACH,
            kind=AccessPackageKind.SUBSCRIPTION,
            is_purchasable=True,
            entitlements=_TRAINING_COACH,
        ),
        AccessPackageCode.NUTRITION: PackageDefinition(
            code=AccessPackageCode.NUTRITION,
            kind=AccessPackageKind.SUBSCRIPTION,
            is_purchasable=True,
            entitlements=_NUTRITION,
        ),
        AccessPackageCode.NUTRITION_PHYSICIAN: PackageDefinition(
            code=AccessPackageCode.NUTRITION_PHYSICIAN,
            kind=AccessPackageKind.SUBSCRIPTION,
            is_purchasable=True,
            entitlements=_NUTRITION_PHYSICIAN,
        ),
        AccessPackageCode.COMPLETE: PackageDefinition(
            code=AccessPackageCode.COMPLETE,
            kind=AccessPackageKind.SUBSCRIPTION,
            is_purchasable=True,
            entitlements=_TRAINING | _NUTRITION,
        ),
        AccessPackageCode.COMPLETE_CARE: PackageDefinition(
            code=AccessPackageCode.COMPLETE_CARE,
            kind=AccessPackageKind.SUBSCRIPTION,
            is_purchasable=True,
            entitlements=_TRAINING_COACH | _NUTRITION_PHYSICIAN,
        ),
        AccessPackageCode.LAUNCH_TRIAL: PackageDefinition(
            code=AccessPackageCode.LAUNCH_TRIAL,
            kind=AccessPackageKind.TRIAL,
            is_purchasable=False,
            entitlements=_TRAINING_COACH | _NUTRITION_PHYSICIAN,
        ),
    }
)

QUOTA_POLICIES: Final = MappingProxyType(
    {
        EntitlementCode.BODY_ANALYSIS_RUN: QuotaPolicy(limit=1, window_days=7),
        EntitlementCode.TRAINING_COACH_REVIEW: QuotaPolicy(limit=1, window_days=28),
        EntitlementCode.NUTRITION_PHYSICIAN_REVIEW: QuotaPolicy(limit=1, window_days=28),
    }
)

_PRIMARY_PACKAGE_RANK: Final = {
    AccessPackageCode.COMPLETE_CARE: 80,
    AccessPackageCode.COMPLETE: 70,
    AccessPackageCode.TRAINING_COACH: 60,
    AccessPackageCode.NUTRITION_PHYSICIAN: 60,
    AccessPackageCode.TRAINING: 50,
    AccessPackageCode.NUTRITION: 50,
    AccessPackageCode.LAUNCH_TRIAL: 40,
    AccessPackageCode.FREE: 0,
}


def package_definition(code: AccessPackageCode | str) -> PackageDefinition:
    return PACKAGE_CATALOG[AccessPackageCode(code)]


def package_rank(code: AccessPackageCode) -> int:
    return _PRIMARY_PACKAGE_RANK[code]


def eligible_upgrade_packages(entitlement: EntitlementCode | str) -> tuple[AccessPackageCode, ...]:
    entitlement_code = EntitlementCode(entitlement)
    return tuple(
        definition.code
        for definition in PACKAGE_CATALOG.values()
        if definition.is_purchasable and entitlement_code in definition.entitlements
    )
