from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin_audit.enums import AdminAuditAction
from app.admin_audit.service import record_admin_audit_event
from app.billing.catalog import PAID_OFFER_CATALOG, offer_definition
from app.billing.enums import (
    BillingOfferCode,
    BillingOrderStatus,
    BillingTransactionStatus,
    PaymentProviderCode,
)
from app.billing.exceptions import (
    BillingIdempotencyConflictError,
    BillingOfferConfigInvalidError,
    BillingOfferPriceRequiredError,
    BillingOfferUnavailableError,
    BillingOrderInvalidStateError,
    BillingOrderNotFoundError,
    BillingPaymentVerificationError,
    BillingProviderRequestError,
)
from app.billing.fulfillment import fulfill_paid_order
from app.billing.models import (
    BillingOfferConfig,
    BillingOrder,
    BillingProviderProduct,
    BillingTransaction,
)
from app.billing.providers.base import (
    PaymentProvider,
    PaymentProviderError,
    ProviderCheckoutRequest,
    ProviderVerificationRequest,
)
from app.billing.repository import (
    find_order_by_idempotency,
    get_offer_config,
    get_order,
    get_order_for_user,
    get_transaction_for_user,
    list_all_orders,
    list_offer_configs,
    list_orders_for_user,
)
from app.billing.schemas import (
    AdminBillingOfferResponse,
    AdminBillingOrderResponse,
    BillingCheckoutResponse,
    BillingOfferResponse,
    BillingOrderResponse,
    BillingPaymentResultResponse,
    BillingQuotaPolicyResponse,
    BillingTransactionResponse,
    CreateCheckoutRequest,
    CreateOrderRequest,
    UpdateBillingOfferConfigRequest,
    VerifyPaymentRequest,
)
from app.config import Settings
from app.entitlements.catalog import QUOTA_POLICIES, package_definition


def utc_now(now: datetime | None = None) -> datetime:
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        return reference.replace(tzinfo=UTC)
    return reference.astimezone(UTC)


def _is_in_window(config: BillingOfferConfig, now: datetime) -> bool:
    available_from = config.available_from
    available_until = config.available_until
    if available_from is not None and utc_now(available_from) > now:
        return False
    if available_until is not None and utc_now(available_until) < now:
        return False
    return True


def is_offer_available(
    config: BillingOfferConfig | None,
    *,
    now: datetime | None = None,
) -> bool:
    if config is None:
        return False
    reference = utc_now(now)
    return (
        config.is_active
        and config.price_irr >= 0
        and bool(config.currency.strip())
        and _is_in_window(config, reference)
    )


def _offer_response(
    code: BillingOfferCode,
    config: BillingOfferConfig | None,
    *,
    now: datetime,
) -> BillingOfferResponse:
    definition = offer_definition(code)
    package = package_definition(definition.package_code)
    return BillingOfferResponse(
        offer_code=definition.code,
        package_code=definition.package_code,
        duration_weeks=definition.duration_weeks,
        price_irr=config.price_irr if config is not None else None,
        currency=config.currency if config is not None else None,
        is_available=is_offer_available(config, now=now),
        entitlements=sorted(package.entitlements, key=lambda entitlement: entitlement.value),
        quota_policies=[
            BillingQuotaPolicyResponse(
                entitlement=entitlement,
                limit=policy.limit,
                window_days=policy.window_days,
            )
            for entitlement, policy in sorted(
                QUOTA_POLICIES.items(), key=lambda item: item[0].value
            )
            if entitlement in package.entitlements
        ],
    )


def list_offer_responses(
    db: Session,
    *,
    now: datetime | None = None,
) -> list[BillingOfferResponse]:
    reference = utc_now(now)
    configs = {config.offer_code: config for config in list_offer_configs(db)}
    return [
        _offer_response(code, configs.get(code), now=reference)
        for code in PAID_OFFER_CATALOG
    ]


def _admin_offer_response(
    code: BillingOfferCode,
    config: BillingOfferConfig | None,
    *,
    now: datetime,
) -> AdminBillingOfferResponse:
    offer = _offer_response(code, config, now=now)
    return AdminBillingOfferResponse(
        **offer.model_dump(),
        is_active=config.is_active if config is not None else False,
        available_from=config.available_from if config is not None else None,
        available_until=config.available_until if config is not None else None,
    )


def list_admin_offer_responses(
    db: Session,
    *,
    now: datetime | None = None,
) -> list[AdminBillingOfferResponse]:
    reference = utc_now(now)
    configs = {config.offer_code: config for config in list_offer_configs(db)}
    return [
        _admin_offer_response(code, configs.get(code), now=reference)
        for code in PAID_OFFER_CATALOG
    ]


def _admin_offer_config_state(config: BillingOfferConfig) -> dict[str, object]:
    return {
        "price_irr": config.price_irr,
        "currency": config.currency,
        "is_active": config.is_active,
        "available_from": (
            config.available_from.isoformat() if config.available_from is not None else None
        ),
        "available_until": (
            config.available_until.isoformat() if config.available_until is not None else None
        ),
    }


def update_offer_config(
    db: Session,
    offer_code: BillingOfferCode,
    payload: UpdateBillingOfferConfigRequest,
    *,
    now: datetime | None = None,
    actor_user_id: UUID | None = None,
) -> AdminBillingOfferResponse:
    reference = utc_now(now)
    offer_definition(offer_code)
    config = get_offer_config(db, offer_code)
    before_state = _admin_offer_config_state(config) if config is not None else None
    if config is None:
        if payload.price_irr is None:
            raise BillingOfferPriceRequiredError(offer_code.value)
        config = BillingOfferConfig(
            offer_code=offer_code,
            price_irr=payload.price_irr,
            currency=payload.currency or "IRR",
            is_active=payload.is_active if payload.is_active is not None else True,
            available_from=payload.available_from,
            available_until=payload.available_until,
        )
        db.add(config)
    else:
        if payload.price_irr is not None:
            config.price_irr = payload.price_irr
        if payload.currency is not None:
            config.currency = payload.currency
        if payload.is_active is not None:
            config.is_active = payload.is_active
        if "available_from" in payload.model_fields_set:
            config.available_from = payload.available_from
        if "available_until" in payload.model_fields_set:
            config.available_until = payload.available_until
    if (
        config.available_from is not None
        and config.available_until is not None
        and utc_now(config.available_until) < utc_now(config.available_from)
    ):
        raise BillingOfferConfigInvalidError("available_until must be after available_from")
    if not config.currency.strip():
        raise BillingOfferConfigInvalidError("currency must not be empty")
    if config.price_irr < 0:
        raise BillingOfferConfigInvalidError("price_irr must not be negative")
    db.flush()
    if actor_user_id is not None:
        record_admin_audit_event(
            db,
            action=AdminAuditAction.BILLING_OFFER_UPDATED,
            actor_user_id=actor_user_id,
            resource_type="billing_offer",
            resource_key=offer_code.value,
            before_state=before_state,
            after_state=_admin_offer_config_state(config),
        )
    else:
        db.commit()
        db.refresh(config)
    return _admin_offer_response(offer_code, config, now=reference)


def to_admin_order_response(order: BillingOrder) -> AdminBillingOrderResponse:
    base = to_order_response(order)
    return AdminBillingOrderResponse(
        **base.model_dump(),
        user_id=order.user_id,
        access_grant_id=order.access_grant_id,
        transactions=[
            BillingTransactionResponse(
                id=transaction.id,
                order_id=transaction.order_id,
                provider=transaction.provider,
                provider_reference=transaction.provider_reference,
                amount_irr=transaction.amount_irr,
                currency=transaction.currency,
                status=transaction.status,
                created_at=transaction.created_at,
                verified_at=transaction.verified_at,
                failed_at=transaction.failed_at,
                refunded_at=transaction.refunded_at,
            )
            for transaction in order.transactions
        ],
    )


def get_admin_orders(
    db: Session,
    *,
    status: BillingOrderStatus | None = None,
    provider: PaymentProviderCode | None = None,
    user_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AdminBillingOrderResponse]:
    return [
        to_admin_order_response(order)
        for order in list_all_orders(
            db,
            status=status,
            provider=provider,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
    ]


def get_admin_order(db: Session, order_id: UUID) -> AdminBillingOrderResponse:
    order = get_order(db, order_id)
    if order is None:
        raise BillingOrderNotFoundError
    return to_admin_order_response(order)


def to_order_response(order: BillingOrder) -> BillingOrderResponse:
    return BillingOrderResponse(
        id=order.id,
        offer_code=order.offer_code,
        package_code_snapshot=order.package_code_snapshot,
        duration_weeks_snapshot=order.duration_weeks_snapshot,
        amount_irr_snapshot=order.amount_irr_snapshot,
        currency_snapshot=order.currency_snapshot,
        provider=order.provider,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
        expires_at=order.expires_at,
        paid_at=order.paid_at,
        refunded_at=order.refunded_at,
    )


def create_order(
    db: Session,
    user_id: UUID,
    payload: CreateOrderRequest,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> BillingOrder:
    reference = utc_now(now)
    existing = find_order_by_idempotency(db, user_id, payload.client_idempotency_key)
    if existing is not None:
        if existing.offer_code != payload.offer_code or existing.provider != payload.provider:
            raise BillingIdempotencyConflictError
        return existing

    definition = offer_definition(payload.offer_code)
    config = get_offer_config(db, payload.offer_code)
    if not is_offer_available(config, now=reference):
        raise BillingOfferUnavailableError(payload.offer_code.value)
    assert config is not None
    order = BillingOrder(
        user_id=user_id,
        offer_code=definition.code,
        package_code_snapshot=definition.package_code,
        duration_weeks_snapshot=definition.duration_weeks,
        amount_irr_snapshot=config.price_irr,
        currency_snapshot=config.currency,
        provider=payload.provider,
        status=BillingOrderStatus.CREATED,
        idempotency_key=payload.client_idempotency_key,
        expires_at=reference + timedelta(minutes=settings.billing_order_ttl_minutes),
    )
    db.add(order)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = find_order_by_idempotency(db, user_id, payload.client_idempotency_key)
        if existing is not None:
            if existing.offer_code != payload.offer_code or existing.provider != payload.provider:
                raise BillingIdempotencyConflictError from None
            return existing
        raise
    db.refresh(order)
    db.commit()
    return order


def get_user_orders(db: Session, user_id: UUID) -> list[BillingOrderResponse]:
    return [to_order_response(order) for order in list_orders_for_user(db, user_id)]


_FINAL_ORDER_STATUSES = frozenset(
    {
        BillingOrderStatus.PAID,
        BillingOrderStatus.CANCELLED,
        BillingOrderStatus.EXPIRED,
        BillingOrderStatus.REFUNDED,
    }
)


def _payment_result_response(
    transaction: BillingTransaction,
    order: BillingOrder,
) -> BillingPaymentResultResponse:
    return BillingPaymentResultResponse(
        order_id=order.id,
        transaction_id=transaction.id,
        transaction_status=transaction.status,
        order_status=order.status,
        verified=transaction.status is BillingTransactionStatus.VERIFIED,
        access_grant_id=order.access_grant_id,
    )


def create_checkout(
    db: Session,
    user_id: UUID,
    order_id: UUID,
    payload: CreateCheckoutRequest,
    provider: PaymentProvider,
    *,
    callback_base_url: str | None = None,
    now: datetime | None = None,
) -> BillingCheckoutResponse:
    reference = utc_now(now)
    order = get_order_for_user(db, order_id, user_id, lock=True)
    if order is None:
        raise BillingOrderNotFoundError
    if order.status in _FINAL_ORDER_STATUSES:
        raise BillingOrderInvalidStateError(order.status.value)
    if order.expires_at is not None and utc_now(order.expires_at) <= reference:
        order.status = BillingOrderStatus.EXPIRED
        db.commit()
        raise BillingOrderInvalidStateError(BillingOrderStatus.EXPIRED.value)
    if order.provider is not payload.provider or provider.code is not payload.provider:
        raise BillingProviderRequestError("Payment provider does not match the order")

    mapping = db.scalar(
        select(BillingProviderProduct).where(
            BillingProviderProduct.offer_code == order.offer_code,
            BillingProviderProduct.provider == payload.provider,
            BillingProviderProduct.is_active.is_(True),
        )
    )
    transaction = BillingTransaction(
        order_id=order.id,
        provider=order.provider,
        amount_irr=order.amount_irr_snapshot,
        currency=order.currency_snapshot,
        status=BillingTransactionStatus.CREATED,
    )
    db.add(transaction)
    db.flush()
    try:
        result = provider.create_checkout(
            ProviderCheckoutRequest(
                order_id=order.id,
                transaction_id=transaction.id,
                offer_code=order.offer_code,
                amount_irr=order.amount_irr_snapshot,
                currency=order.currency_snapshot,
                external_product_id=mapping.external_product_id if mapping else None,
                callback_base_url=callback_base_url,
            )
        )
    except PaymentProviderError as error:
        db.rollback()
        raise BillingProviderRequestError(str(error)) from error
    transaction.provider_reference = result.provider_reference
    transaction.status = BillingTransactionStatus.PENDING
    order.status = BillingOrderStatus.PENDING
    db.flush()
    db.commit()
    db.refresh(transaction)
    return BillingCheckoutResponse(
        order_id=order.id,
        transaction_id=transaction.id,
        provider=order.provider,
        checkout_kind=result.checkout_kind,
        checkout_url=result.checkout_url,
        provider_product_id=result.provider_product_id,
        provider_reference=result.provider_reference,
    )


def _transaction_and_order_for_user(
    db: Session,
    user_id: UUID,
    transaction_id: UUID,
) -> tuple[BillingTransaction, BillingOrder]:
    transaction = get_transaction_for_user(db, transaction_id, user_id)
    if transaction is None:
        raise BillingOrderNotFoundError
    order = get_order_for_user(db, transaction.order_id, user_id)
    if order is None:
        raise BillingOrderNotFoundError
    return transaction, order


def _provider_request(
    transaction: BillingTransaction,
    order: BillingOrder,
    provider_reference: str | None,
) -> ProviderVerificationRequest:
    reference = provider_reference or transaction.provider_reference
    if reference is None or reference != transaction.provider_reference:
        raise BillingPaymentVerificationError("Payment reference does not match the transaction")
    return ProviderVerificationRequest(
        order_id=order.id,
        transaction_id=transaction.id,
        provider_reference=reference,
        amount_irr=transaction.amount_irr,
        currency=transaction.currency,
    )


def verify_payment(
    db: Session,
    user_id: UUID,
    provider_code: PaymentProviderCode,
    payload: VerifyPaymentRequest,
    provider: PaymentProvider,
    *,
    now: datetime | None = None,
) -> BillingPaymentResultResponse:
    transaction, order = _transaction_and_order_for_user(db, user_id, payload.transaction_id)
    if transaction.provider is not provider_code or provider.code is not provider_code:
        raise BillingProviderRequestError("Payment provider does not match the transaction")
    if transaction.status in {
        BillingTransactionStatus.VERIFIED,
        BillingTransactionStatus.FAILED,
        BillingTransactionStatus.REFUNDED,
    }:
        return _payment_result_response(transaction, order)
    request = _provider_request(transaction, order, payload.provider_reference)
    try:
        result = provider.verify_payment(request)
    except PaymentProviderError as error:
        raise BillingPaymentVerificationError(str(error)) from error

    locked_transaction = db.get(BillingTransaction, transaction.id)
    locked_order = get_order_for_user(db, order.id, user_id, lock=True)
    if locked_transaction is None or locked_order is None:
        raise BillingOrderNotFoundError
    if result.status == "verified":
        locked_transaction.status = BillingTransactionStatus.VERIFIED
        locked_transaction.verified_at = utc_now(now)
        db.flush()
        fulfillment = fulfill_paid_order(
            db,
            locked_order.id,
            locked_transaction.id,
            now=now,
        )
        return _payment_result_response(locked_transaction, fulfillment.order)
    if result.status == "refunded":
        return revoke_transaction(
            db,
            user_id,
            provider_code,
            payload,
            provider,
            now=now,
        )

    locked_transaction.status = BillingTransactionStatus.FAILED
    locked_transaction.failed_at = utc_now(now)
    open_attempts = db.scalar(
        select(func.count())
        .select_from(BillingTransaction)
        .where(
            BillingTransaction.order_id == locked_order.id,
            BillingTransaction.id != locked_transaction.id,
            BillingTransaction.status.in_(
                [BillingTransactionStatus.CREATED, BillingTransactionStatus.PENDING]
            ),
        )
    )
    if not open_attempts and locked_order.access_grant_id is None:
        locked_order.status = BillingOrderStatus.FAILED
    db.flush()
    db.commit()
    return _payment_result_response(locked_transaction, locked_order)


def revoke_transaction(
    db: Session,
    user_id: UUID,
    provider_code: PaymentProviderCode,
    payload: VerifyPaymentRequest,
    provider: PaymentProvider,
    *,
    now: datetime | None = None,
) -> BillingPaymentResultResponse:
    transaction, order = _transaction_and_order_for_user(db, user_id, payload.transaction_id)
    if transaction.provider is not provider_code or provider.code is not provider_code:
        raise BillingProviderRequestError("Payment provider does not match the transaction")
    if transaction.status is BillingTransactionStatus.REFUNDED:
        return _payment_result_response(transaction, order)
    request = _provider_request(transaction, order, payload.provider_reference)
    try:
        result = provider.verify_refund(request)
    except PaymentProviderError as error:
        raise BillingPaymentVerificationError(str(error)) from error
    if result.status != "refunded":
        raise BillingPaymentVerificationError("Provider did not verify a refund")

    locked_transaction = db.get(BillingTransaction, transaction.id)
    locked_order = get_order_for_user(db, order.id, user_id, lock=True)
    if locked_transaction is None or locked_order is None:
        raise BillingOrderNotFoundError
    locked_transaction.status = BillingTransactionStatus.REFUNDED
    locked_transaction.refunded_at = utc_now(now)
    locked_order.status = BillingOrderStatus.REFUNDED
    locked_order.refunded_at = utc_now(now)
    if locked_order.access_grant_id is not None:
        from app.entitlements.models import UserAccessGrant

        grant = db.get(UserAccessGrant, locked_order.access_grant_id)
        if grant is not None and grant.revoked_at is None:
            grant.revoked_at = utc_now(now)
    db.flush()
    db.commit()
    return _payment_result_response(locked_transaction, locked_order)
