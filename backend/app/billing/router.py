from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.billing.dependencies import AppSettings, BillingWriteAuthentication, resolve_provider
from app.billing.enums import PaymentProviderCode
from app.billing.exceptions import BillingOrderNotFoundError
from app.billing.repository import get_order_for_user
from app.billing.schemas import (
    BillingCheckoutResponse,
    BillingOfferResponse,
    BillingOrderResponse,
    BillingPaymentResultResponse,
    CreateCheckoutRequest,
    CreateOrderRequest,
    VerifyPaymentRequest,
)
from app.billing.service import (
    create_checkout,
    create_order,
    get_user_orders,
    list_offer_responses,
    revoke_transaction,
    to_order_response,
    verify_payment,
)
from app.database.session import get_db

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/offers", response_model=list[BillingOfferResponse])
def offers(db: DatabaseSession) -> list[BillingOfferResponse]:
    return list_offer_responses(db)


@router.post(
    "/orders",
    response_model=BillingOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_billing_order(
    db: DatabaseSession,
    authentication: BillingWriteAuthentication,
    settings: AppSettings,
    payload: CreateOrderRequest,
) -> BillingOrderResponse:
    order = create_order(db, authentication.user.id, payload, settings)
    return to_order_response(order)


@router.get("/orders", response_model=list[BillingOrderResponse])
def billing_orders(db: DatabaseSession, user: CurrentUser) -> list[BillingOrderResponse]:
    return get_user_orders(db, user.id)


@router.get("/orders/{order_id}", response_model=BillingOrderResponse)
def billing_order(
    order_id: UUID,
    db: DatabaseSession,
    user: CurrentUser,
) -> BillingOrderResponse:
    order = get_order_for_user(db, order_id, user.id)
    if order is None:
        raise BillingOrderNotFoundError
    return to_order_response(order)


@router.post(
    "/orders/{order_id}/checkout",
    response_model=BillingCheckoutResponse,
)
def billing_checkout(
    order_id: UUID,
    db: DatabaseSession,
    authentication: BillingWriteAuthentication,
    settings: AppSettings,
    payload: CreateCheckoutRequest,
    request: Request,
) -> BillingCheckoutResponse:
    provider = resolve_provider(request, payload.provider)
    return create_checkout(
        db,
        authentication.user.id,
        order_id,
        payload,
        provider,
        callback_base_url=settings.billing_callback_base_url,
    )


@router.post(
    "/providers/{provider}/verify",
    response_model=BillingPaymentResultResponse,
)
def verify_billing_payment(
    provider: PaymentProviderCode,
    db: DatabaseSession,
    authentication: BillingWriteAuthentication,
    payload: VerifyPaymentRequest,
    request: Request,
) -> BillingPaymentResultResponse:
    selected_provider = resolve_provider(request, provider)
    return verify_payment(
        db,
        authentication.user.id,
        provider,
        payload,
        selected_provider,
    )


@router.post(
    "/providers/{provider}/refund",
    response_model=BillingPaymentResultResponse,
)
def refund_billing_payment(
    provider: PaymentProviderCode,
    db: DatabaseSession,
    authentication: BillingWriteAuthentication,
    payload: VerifyPaymentRequest,
    request: Request,
) -> BillingPaymentResultResponse:
    selected_provider = resolve_provider(request, provider)
    return revoke_transaction(
        db,
        authentication.user.id,
        provider,
        payload,
        selected_provider,
    )
