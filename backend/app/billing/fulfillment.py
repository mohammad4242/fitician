from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.enums import BillingOrderStatus, BillingTransactionStatus
from app.billing.exceptions import BillingOrderNotFoundError, BillingPaymentVerificationError
from app.billing.models import BillingOrder, BillingTransaction
from app.billing.repository import get_order
from app.entitlements.catalog import package_definition
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.models import UserAccessGrant
from app.entitlements.service import grant_package


@dataclass(frozen=True, slots=True)
class FulfillmentResult:
    order: BillingOrder
    access_grant: UserAccessGrant


def _utc_now(now: datetime | None = None) -> datetime:
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        return reference.replace(tzinfo=UTC)
    return reference.astimezone(UTC)


def _access_start(
    db: Session,
    order: BillingOrder,
    reference: datetime,
) -> datetime:
    package_code = AccessPackageCode(order.package_code_snapshot)
    valid_grants = db.scalars(
        select(UserAccessGrant).where(
            UserAccessGrant.user_id == order.user_id,
            UserAccessGrant.starts_at <= reference,
            UserAccessGrant.revoked_at.is_(None),
            UserAccessGrant.ends_at.is_not(None),
            UserAccessGrant.ends_at > reference,
        )
    ).all()
    anchors: list[datetime] = []
    for grant in valid_grants:
        if AccessPackageCode(grant.package_code) is package_code and grant.ends_at is not None:
            anchors.append(grant.ends_at)
    purchased_entitlements = package_definition(package_code).entitlements
    for grant in valid_grants:
        grant_package_code = AccessPackageCode(grant.package_code)
        if (
            grant_package_code is AccessPackageCode.LAUNCH_TRIAL
            or grant.source is GrantSource.PROMOTION
        ):
            covering_entitlements = package_definition(grant_package_code).entitlements
            if (
                purchased_entitlements.issubset(covering_entitlements)
                and grant.ends_at is not None
            ):
                anchors.append(grant.ends_at)
    return max([reference, *anchors])


def fulfill_paid_order(
    db: Session,
    order_id: UUID,
    transaction_id: UUID,
    *,
    now: datetime | None = None,
) -> FulfillmentResult:
    order = get_order(db, order_id, lock=True)
    if order is None:
        raise BillingOrderNotFoundError
    if order.access_grant_id is not None:
        access_grant = db.get(UserAccessGrant, order.access_grant_id)
        if access_grant is not None:
            return FulfillmentResult(order=order, access_grant=access_grant)

    transaction = db.get(BillingTransaction, transaction_id)
    if transaction is None or transaction.order_id != order.id:
        raise BillingPaymentVerificationError("Verified transaction does not belong to this order")
    if transaction.status is not BillingTransactionStatus.VERIFIED:
        raise BillingPaymentVerificationError("Payment must be verified before fulfillment")
    if order.user_id is None:
        raise BillingPaymentVerificationError("Cannot fulfill an order without an account")

    reference = _utc_now(now)
    starts_at = _access_start(db, order, reference)
    ends_at = starts_at + timedelta(weeks=order.duration_weeks_snapshot)
    access_grant = grant_package(
        db,
        order.user_id,
        order.package_code_snapshot,
        source=GrantSource.SUBSCRIPTION,
        starts_at=starts_at,
        ends_at=ends_at,
        idempotency_key=f"billing-order:{order.id}",
        term_weeks=order.duration_weeks_snapshot,
    )
    order.access_grant_id = access_grant.id
    order.status = BillingOrderStatus.PAID
    order.paid_at = order.paid_at or reference
    db.flush()
    db.commit()
    db.refresh(order)
    return FulfillmentResult(order=order, access_grant=access_grant)
