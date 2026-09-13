from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.enums import BillingOfferCode
from app.billing.models import BillingOfferConfig, BillingOrder, BillingTransaction


def list_offer_configs(db: Session) -> list[BillingOfferConfig]:
    statement = select(BillingOfferConfig).order_by(BillingOfferConfig.offer_code)
    return list(db.scalars(statement).all())


def get_offer_config(
    db: Session,
    offer_code: BillingOfferCode,
) -> BillingOfferConfig | None:
    return db.get(BillingOfferConfig, offer_code)


def get_order_for_user(
    db: Session,
    order_id: UUID,
    user_id: UUID,
    *,
    lock: bool = False,
) -> BillingOrder | None:
    statement = select(BillingOrder).where(
        BillingOrder.id == order_id,
        BillingOrder.user_id == user_id,
    )
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def get_order(db: Session, order_id: UUID, *, lock: bool = False) -> BillingOrder | None:
    statement = select(BillingOrder).where(BillingOrder.id == order_id)
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def list_orders_for_user(db: Session, user_id: UUID) -> list[BillingOrder]:
    statement = (
        select(BillingOrder)
        .where(BillingOrder.user_id == user_id)
        .order_by(BillingOrder.created_at.desc(), BillingOrder.id.desc())
    )
    return list(db.scalars(statement).all())


def list_all_orders(db: Session) -> list[BillingOrder]:
    statement = select(BillingOrder).order_by(
        BillingOrder.created_at.desc(), BillingOrder.id.desc()
    )
    return list(db.scalars(statement).all())


def find_order_by_idempotency(
    db: Session,
    user_id: UUID,
    idempotency_key: str,
    *,
    lock: bool = False,
) -> BillingOrder | None:
    statement = select(BillingOrder).where(
        BillingOrder.user_id == user_id,
        BillingOrder.idempotency_key == idempotency_key,
    )
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def get_transaction_for_user(
    db: Session,
    transaction_id: UUID,
    user_id: UUID,
    *,
    lock: bool = False,
) -> BillingTransaction | None:
    statement = (
        select(BillingTransaction)
        .join(BillingOrder, BillingOrder.id == BillingTransaction.order_id)
        .where(
            BillingTransaction.id == transaction_id,
            BillingOrder.user_id == user_id,
        )
    )
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)
