"""Quota reservations share the caller's plan lifecycle transaction."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.enums import EntitlementCode
from app.entitlements.models import EntitlementQuotaReservation, EntitlementUsageEvent
from app.entitlements.service import require_quota_available


def reserve_quota(
    db: Session,
    user_id: UUID,
    code: EntitlementCode,
    resource_key: str,
    *,
    now: datetime | None = None,
) -> None:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise ValueError("User not found")
    if user.is_admin:
        return
    for model in (EntitlementQuotaReservation, EntitlementUsageEvent):
        if db.scalar(
            select(model.id).where(
                model.user_id == user_id,
                model.entitlement_key == code.value,
                model.resource_key == resource_key,
            )
        ):
            return
    require_quota_available(db, user_id, code, now=now)
    db.add(
        EntitlementQuotaReservation(
            user_id=user_id, entitlement_key=code.value, resource_key=resource_key
        )
    )
    db.flush()


def release_reservation(
    db: Session, user_id: UUID, code: EntitlementCode, resource_key: str
) -> None:
    db.scalar(select(User.id).where(User.id == user_id).with_for_update())
    reservation = db.scalar(
        select(EntitlementQuotaReservation).where(
            EntitlementQuotaReservation.user_id == user_id,
            EntitlementQuotaReservation.entitlement_key == code.value,
            EntitlementQuotaReservation.resource_key == resource_key,
        )
    )
    if reservation is not None:
        db.delete(reservation)
        db.flush()


def finalize_reservation(
    db: Session, user_id: UUID, code: EntitlementCode, resource_key: str
) -> bool:
    """Legacy plans have no reservation and must never be charged a second time."""
    from app.entitlements.service import consume_quota

    db.scalar(select(User.id).where(User.id == user_id).with_for_update())
    if (
        db.scalar(
            select(EntitlementQuotaReservation.id).where(
                EntitlementQuotaReservation.user_id == user_id,
                EntitlementQuotaReservation.entitlement_key == code.value,
                EntitlementQuotaReservation.resource_key == resource_key,
            )
        )
        is None
    ):
        return False
    return consume_quota(db, user_id, code, resource_key)
