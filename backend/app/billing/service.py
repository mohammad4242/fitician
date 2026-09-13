from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.billing.catalog import PAID_OFFER_CATALOG, offer_definition
from app.billing.enums import BillingOfferCode, BillingOrderStatus
from app.billing.exceptions import (
    BillingIdempotencyConflictError,
    BillingOfferUnavailableError,
)
from app.billing.models import BillingOfferConfig, BillingOrder
from app.billing.repository import (
    find_order_by_idempotency,
    get_offer_config,
    list_offer_configs,
    list_orders_for_user,
)
from app.billing.schemas import (
    BillingOfferResponse,
    BillingOrderResponse,
    BillingQuotaPolicyResponse,
    CreateOrderRequest,
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
