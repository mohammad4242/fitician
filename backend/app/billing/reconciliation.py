"""Restart-safe bounded recovery in the existing Iran scheduler."""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.enums import BillingTransactionStatus, PaymentProviderCode
from app.billing.exceptions import BillingPaymentVerificationError, BillingProviderRequestError
from app.billing.models import BillingOrder, BillingTransaction
from app.billing.providers import build_payment_providers
from app.billing.providers.base import PaymentProvider
from app.billing.providers.tetrapay import TetraPayProvider
from app.billing.service import payment_event, reconcile_payment, resume_checkout, utc_now
from app.config import Settings
from app.database.session import get_engine


def reconcile_batch(db: Session, providers: dict[PaymentProviderCode, PaymentProvider]) -> int:
    ids = db.execute(
        select(BillingTransaction.id, BillingTransaction.order_id)
        .join(BillingOrder, BillingOrder.id == BillingTransaction.order_id)
        .where(
            BillingOrder.user_id.is_not(None),
            BillingTransaction.provider == PaymentProviderCode.TETRAPAY,
            BillingTransaction.next_reconcile_at <= utc_now(),
            BillingTransaction.status.not_in(
                [BillingTransactionStatus.VERIFIED, BillingTransactionStatus.REFUNDED]
            ),
        )
        .order_by(BillingTransaction.next_reconcile_at)
        .limit(5)
    ).all()
    completed = 0
    for transaction_id, order_id in ids:
        order = db.scalar(
            select(BillingOrder)
            .where(BillingOrder.id == order_id)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if order is None:
            continue
        transaction = db.get(BillingTransaction, transaction_id, populate_existing=True)
        provider = providers.get(PaymentProviderCode.TETRAPAY)
        if (
            transaction is None
            or provider is None
            or order.user_id is None
            or transaction.next_reconcile_at is None
            or transaction.next_reconcile_at > utc_now()
        ):
            db.rollback()
            continue
        if (
            isinstance(provider, TetraPayProvider)
            and transaction.provider_mode != provider.settings.tetrapay_mode
        ):
            transaction.next_reconcile_at = None
            transaction.provider_evidence = {"reason": "PAYMENT_ENVIRONMENT_MISMATCH"}
            db.commit()
            continue
        try:
            if transaction.provider_reference is None:
                resume_checkout(db, order, transaction, provider)
                # resume commits the write; reacquire before applying verification.
                order = db.scalar(
                    select(BillingOrder)
                    .where(BillingOrder.id == order_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                assert order is not None
                db.refresh(transaction)
            reconcile_payment(db, transaction, order, provider)
            completed += 1
        except (BillingPaymentVerificationError, BillingProviderRequestError):
            db.commit()
        finally:
            # Fast paths may leave a lock held. Never hold it across scheduler ticks.
            db.commit()
    payment_event("PAYMENT_RECONCILIATION_COMPLETED")
    return completed


async def reconciliation_loop(settings: Settings, stop_event: asyncio.Event) -> None:
    providers = build_payment_providers(settings)

    def tick() -> None:
        try:
            with Session(get_engine(settings)) as db:
                reconcile_batch(db, providers)
        except Exception:
            payment_event("PAYMENT_RECONCILIATION_FAILED", error=True)

    while not stop_event.is_set():
        await asyncio.to_thread(tick)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
        except TimeoutError:
            pass
