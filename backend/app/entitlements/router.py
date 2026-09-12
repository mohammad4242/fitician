from fastapi import APIRouter

from app.entitlements.catalog import PACKAGE_CATALOG, QUOTA_POLICIES
from app.entitlements.dependencies import CurrentAccessSnapshot, CurrentUser, DatabaseSession
from app.entitlements.schemas import (
    AccessGrantSummaryResponse,
    EntitlementSnapshotResponse,
    EntitlementStateResponse,
    ProductCatalogItemResponse,
    ProductQuotaPolicyResponse,
    QuotaStatusResponse,
    TrialStateResponse,
)
from app.entitlements.service import quota_status

router = APIRouter(tags=["entitlements"])


@router.get("/api/v1/products", response_model=list[ProductCatalogItemResponse])
def products() -> list[ProductCatalogItemResponse]:
    return [
        ProductCatalogItemResponse(
            code=definition.code,
            kind=definition.kind,
            is_purchasable=definition.is_purchasable,
            entitlements=sorted(definition.entitlements, key=lambda code: code.value),
            quota_policies=[
                ProductQuotaPolicyResponse(
                    entitlement=entitlement,
                    limit=policy.limit,
                    window_days=policy.window_days,
                )
                for entitlement, policy in sorted(
                    QUOTA_POLICIES.items(), key=lambda item: item[0].value
                )
                if entitlement in definition.entitlements
            ],
        )
        for definition in PACKAGE_CATALOG.values()
    ]


@router.get("/api/v1/entitlements/me", response_model=EntitlementSnapshotResponse)
def my_entitlements(
    db: DatabaseSession,
    user: CurrentUser,
    snapshot: CurrentAccessSnapshot,
) -> EntitlementSnapshotResponse:
    quota_responses: list[QuotaStatusResponse] = []
    for entitlement in sorted(snapshot.granted_entitlements, key=lambda code: code.value):
        status = quota_status(db, user.id, entitlement)
        if status is not None:
            quota_responses.append(
                QuotaStatusResponse(
                    entitlement=status.entitlement,
                    limit=status.limit,
                    used=status.used,
                    remaining=status.remaining,
                    window_days=status.window_days,
                    reset_at=status.reset_at,
                )
            )
    return EntitlementSnapshotResponse(
        primary_package=snapshot.primary_package,
        active_packages=list(snapshot.active_packages),
        trial=TrialStateResponse(active=snapshot.trial.active, ends_at=snapshot.trial.ends_at),
        entitlements=EntitlementStateResponse(
            granted=sorted(snapshot.granted_entitlements, key=lambda code: code.value),
            quotas=quota_responses,
        ),
        grants=[
            AccessGrantSummaryResponse(
                id=grant.id,
                package_code=grant.package_code,
                source=grant.source,
                starts_at=grant.starts_at,
                ends_at=grant.ends_at,
                revoked_at=grant.revoked_at,
            )
            for grant in snapshot.grants
        ],
    )
