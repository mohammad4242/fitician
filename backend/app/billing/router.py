from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.billing.dependencies import AppSettings, BillingWriteAuthentication, resolve_provider
from app.billing.enums import PaymentProviderCode
from app.billing.exceptions import BillingOrderNotFoundError
from app.billing.models import BillingOrder, BillingTransaction
from app.billing.providers.base import PaymentProviderError, ProviderVerificationRequest
from app.billing.providers.tetrapay import TetraPayProvider, verify_webhook
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
    payment_event,
    reconcile_payment,
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
    request: Request,
) -> BillingOrderResponse:
    resolve_provider(request, payload.provider)
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


class CheckoutMethods(BaseModel):
    providers: list[PaymentProviderCode]
    default_provider: PaymentProviderCode | None


@router.get("/checkout-methods", response_model=CheckoutMethods)
def checkout_methods(request: Request, settings: AppSettings) -> CheckoutMethods:
    providers = list(getattr(request.app.state, "billing_providers", {}))
    default = settings.billing_default_provider
    return CheckoutMethods(
        providers=providers,
        default_provider=PaymentProviderCode(default)
        if default is not None and default in providers
        else None,
    )


class TetraPayReturn(BaseModel):
    token: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


@router.post("/tetrapay/return", response_model=BillingPaymentResultResponse)
def tetrapay_return(
    payload: TetraPayReturn,
    db: DatabaseSession,
    authentication: BillingWriteAuthentication,
    request: Request,
) -> BillingPaymentResultResponse:
    transaction = db.scalar(
        select(BillingTransaction)
        .join(BillingOrder)
        .where(
            BillingTransaction.provider == PaymentProviderCode.TETRAPAY,
            BillingTransaction.provider_reference == payload.token,
            BillingOrder.user_id == authentication.user.id,
        )
    )
    if transaction is None:
        raise BillingOrderNotFoundError
    return verify_payment(
        db,
        authentication.user.id,
        PaymentProviderCode.TETRAPAY,
        VerifyPaymentRequest(transaction_id=transaction.id),
        resolve_provider(request, PaymentProviderCode.TETRAPAY),
    )


@router.post("/webhooks/tetrapay")
async def tetrapay_webhook(request: Request, db: DatabaseSession) -> dict[str, bool]:
    import json

    from starlette.concurrency import run_in_threadpool

    selected = resolve_provider(request, PaymentProviderCode.TETRAPAY)
    if not isinstance(selected, TetraPayProvider):
        raise HTTPException(503, "Webhook unavailable")
    settings = selected.settings
    secret = settings.tetrapay_webhook_secret
    if not settings.tetrapay_webhook_enabled or secret is None:
        raise HTTPException(503, "Webhook disabled")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 65536:
            raise HTTPException(413, "Webhook too large")
    try:
        verify_webhook(
            bytes(raw), request.headers.get("X-TetraPay-Signature", ""), secret.get_secret_value()
        )
    except PaymentProviderError:
        payment_event("PAYMENT_WEBHOOK_INVALID_SIGNATURE", error=True)
        raise HTTPException(400, "Invalid webhook") from None
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError
        event = data.get("event")
        event_id = data.get("event_id")
        if (
            event not in {"payment.paid", "payment.underpaid"}
            or event != request.headers.get("X-TetraPay-Event")
            or not isinstance(event_id, str)
            or not 1 <= len(event_id) <= 128
            or event_id != request.headers.get("X-TetraPay-Event-Id")
            or (event == "payment.paid" and data.get("status") != "paid")
            or (event == "payment.underpaid" and data.get("status") != "pending")
        ):
            raise ValueError
        sandbox = data.get("sandbox", False)
        if not isinstance(sandbox, bool) or sandbox != (settings.tetrapay_mode == "sandbox"):
            raise ValueError
        if request.headers.get("X-TetraPay-Sandbox", "false") != str(sandbox).lower():
            raise ValueError
        token = TetraPayReturn(token=data.get("token")).token
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid webhook") from None

    def process() -> None:
        transaction = db.scalar(
            select(BillingTransaction).where(
                BillingTransaction.provider == PaymentProviderCode.TETRAPAY,
                BillingTransaction.provider_reference == token,
            )
        )
        if transaction is None:
            # A provider event can race the checkout response; ask TetraPay to retry.
            raise HTTPException(503, "Payment mapping pending")
        order = db.scalar(
            select(BillingOrder)
            .where(BillingOrder.id == transaction.order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        db.refresh(transaction)
        if order is None or order.user_id is None:
            raise HTTPException(400, "Invalid payment")
        try:
            result = selected.validate_payment(
                data,
                ProviderVerificationRequest(
                    order.id,
                    transaction.id,
                    token,
                    transaction.amount_irr,
                    transaction.currency,
                ),
            )
        except PaymentProviderError:
            payment_event("PAYMENT_WEBHOOK_REJECTED", error=True)
            raise HTTPException(400, "Invalid payment") from None
        reconcile_payment(db, transaction, order, selected, trusted_result=result)
        db.commit()
        payment_event("PAYMENT_WEBHOOK_RECEIVED")

    await run_in_threadpool(process)
    return {"received": True}
