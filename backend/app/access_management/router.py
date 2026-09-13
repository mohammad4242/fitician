from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.access_management.repository import search_users as search_access_users_query
from app.access_management.schemas import (
    AccessCampaignCreateRequest,
    AccessCampaignResponse,
    AccessCampaignUpdateRequest,
    AdminCampaignRedemptionResponse,
    AdminGrantRequest,
    AdminGrantResponse,
    AdminMemberSummaryResponse,
    AdminUserAccessResponse,
    ManualCampaignRedemptionRequest,
    RevokeGrantRequest,
)
from app.access_management.service import (
    create_admin_grant,
    create_campaign,
    get_campaign_response,
    grant_response,
    list_campaign_responses,
    manual_redemption_response,
    member_summary,
    redeem_campaign,
    revoke_grant,
    set_campaign_active,
    update_campaign,
    user_access_response,
)
from app.admin.dependencies import AdminUser, require_admin
from app.auth.cookies import require_trusted_origin
from app.auth.dependencies import DatabaseSession

router = APIRouter(
    prefix="/api/v1/admin/access",
    tags=["admin-access"],
    dependencies=[Depends(require_admin)],
)


def _commit(db: Session) -> None:
    db.commit()


@router.get("/campaigns", response_model=list[AccessCampaignResponse])
def read_campaigns(
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AccessCampaignResponse]:
    return list_campaign_responses(db, limit=limit, offset=offset)


@router.get("/campaigns/{campaign_id}", response_model=AccessCampaignResponse)
def read_campaign(campaign_id: UUID, db: DatabaseSession) -> AccessCampaignResponse:
    return get_campaign_response(db, campaign_id)


@router.post(
    "/campaigns",
    response_model=AccessCampaignResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create_access_campaign(
    payload: AccessCampaignCreateRequest,
    db: DatabaseSession,
    admin: AdminUser,
) -> AccessCampaignResponse:
    campaign = create_campaign(db, payload, actor_user_id=admin.id)
    _commit(db)
    return get_campaign_response(db, campaign.id)


@router.patch(
    "/campaigns/{campaign_id}",
    response_model=AccessCampaignResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_access_campaign(
    campaign_id: UUID,
    payload: AccessCampaignUpdateRequest,
    db: DatabaseSession,
    admin: AdminUser,
) -> AccessCampaignResponse:
    campaign = update_campaign(db, campaign_id, payload, actor_user_id=admin.id)
    _commit(db)
    return get_campaign_response(db, campaign.id)


@router.post(
    "/campaigns/{campaign_id}/activate",
    response_model=AccessCampaignResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def activate_access_campaign(
    campaign_id: UUID,
    db: DatabaseSession,
    admin: AdminUser,
) -> AccessCampaignResponse:
    campaign = set_campaign_active(db, campaign_id, True, actor_user_id=admin.id)
    _commit(db)
    return get_campaign_response(db, campaign.id)


@router.post(
    "/campaigns/{campaign_id}/deactivate",
    response_model=AccessCampaignResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def deactivate_access_campaign(
    campaign_id: UUID,
    db: DatabaseSession,
    admin: AdminUser,
) -> AccessCampaignResponse:
    campaign = set_campaign_active(db, campaign_id, False, actor_user_id=admin.id)
    _commit(db)
    return get_campaign_response(db, campaign.id)


@router.post(
    "/users/{user_id}/campaigns/{campaign_id}/redeem",
    response_model=AdminCampaignRedemptionResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def redeem_access_campaign(
    user_id: UUID,
    campaign_id: UUID,
    payload: ManualCampaignRedemptionRequest,
    db: DatabaseSession,
    admin: AdminUser,
) -> AdminCampaignRedemptionResponse:
    result = redeem_campaign(
        db,
        campaign_id,
        user_id,
        actor_user_id=admin.id,
        reason=payload.reason,
        manual=True,
    )
    _commit(db)
    return manual_redemption_response(db, result)


@router.get("/users", response_model=list[AdminMemberSummaryResponse])
def search_access_users(
    db: DatabaseSession,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminMemberSummaryResponse]:
    return [
        member_summary(db, user)
        for user in search_access_users_query(db, q, limit=limit, offset=offset)
    ]


@router.get("/users/{user_id}", response_model=AdminUserAccessResponse)
def read_user_access(user_id: UUID, db: DatabaseSession) -> AdminUserAccessResponse:
    member, snapshot, grants = user_access_response(db, user_id)
    return AdminUserAccessResponse(
        member=member,
        entitlement_snapshot=snapshot,
        grants=grants,
    )


@router.post(
    "/users/{user_id}/grants",
    response_model=AdminGrantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create_access_grant(
    user_id: UUID,
    payload: AdminGrantRequest,
    db: DatabaseSession,
    admin: AdminUser,
) -> AdminGrantResponse:
    result = create_admin_grant(
        db,
        user_id,
        package_code=payload.package_code,
        term_weeks=payload.term_weeks,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        reason=payload.reason,
        client_idempotency_key=payload.client_idempotency_key,
        actor_user_id=admin.id,
    )
    _commit(db)
    return grant_response(db, result.grant)


@router.post(
    "/grants/{grant_id}/revoke",
    response_model=AdminGrantResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def revoke_access_grant(
    grant_id: UUID,
    payload: RevokeGrantRequest,
    db: DatabaseSession,
    admin: AdminUser,
) -> AdminGrantResponse:
    result = revoke_grant(
        db,
        grant_id,
        reason=payload.reason,
        actor_user_id=admin.id,
    )
    _commit(db)
    return grant_response(db, result.grant)
