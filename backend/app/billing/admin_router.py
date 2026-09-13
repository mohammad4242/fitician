from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.dependencies import AdminUser, require_admin
from app.auth.cookies import require_trusted_origin
from app.billing.enums import BillingOfferCode, BillingOrderStatus, PaymentProviderCode
from app.billing.schemas import (
    AdminBillingOfferResponse,
    AdminBillingOrderResponse,
    UpdateBillingOfferConfigRequest,
)
from app.billing.service import (
    get_admin_order,
    get_admin_orders,
    list_admin_offer_responses,
    update_offer_config,
)
from app.database.session import get_db

router = APIRouter(
    prefix="/api/v1/admin/billing",
    tags=["admin-billing"],
    dependencies=[Depends(require_admin)],
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/offers", response_model=list[AdminBillingOfferResponse])
def admin_billing_offers(db: DatabaseSession) -> list[AdminBillingOfferResponse]:
    return list_admin_offer_responses(db)


@router.patch(
    "/offers/{offer_code}",
    response_model=AdminBillingOfferResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_admin_billing_offer(
    offer_code: BillingOfferCode,
    db: DatabaseSession,
    payload: UpdateBillingOfferConfigRequest,
    admin: AdminUser,
) -> AdminBillingOfferResponse:
    response = update_offer_config(
        db,
        offer_code,
        payload,
        actor_user_id=admin.id,
    )
    db.commit()
    return response


@router.get("/orders", response_model=list[AdminBillingOrderResponse])
def admin_billing_orders(
    db: DatabaseSession,
    status: Annotated[BillingOrderStatus | None, Query()] = None,
    provider: Annotated[PaymentProviderCode | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminBillingOrderResponse]:
    return get_admin_orders(
        db,
        status=status,
        provider=provider,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.get("/orders/{order_id}", response_model=AdminBillingOrderResponse)
def admin_billing_order(
    order_id: UUID,
    db: DatabaseSession,
) -> AdminBillingOrderResponse:
    return get_admin_order(db, order_id)
