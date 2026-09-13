from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import BillingOfferCode, BillingOrderStatus, BillingTransactionStatus
from app.billing.fulfillment import fulfill_paid_order
from app.billing.models import BillingOrder, BillingTransaction
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.service import grant_package


def test_same_package_purchase_extends_from_latest_active_expiry(db: Session) -> None:
    reference = datetime(2026, 9, 15, tzinfo=UTC)
    current_end = reference + timedelta(days=12)
    user = User(email="extension@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    grant_package(
        db,
        user.id,
        AccessPackageCode.TRAINING,
        source=GrantSource.SUBSCRIPTION,
        starts_at=reference - timedelta(days=10),
        ends_at=current_end,
        term_weeks=4,
        idempotency_key="existing-training",
    )
    order = BillingOrder(
        user_id=user.id,
        offer_code=BillingOfferCode.TRAINING_4W,
        package_code_snapshot=AccessPackageCode.TRAINING,
        duration_weeks_snapshot=4,
        amount_irr_snapshot=1_000_000,
        currency_snapshot="IRR",
        provider="fake",
        status=BillingOrderStatus.PENDING,
        idempotency_key="extension-order",
    )
    db.add(order)
    db.flush()
    transaction = BillingTransaction(
        order_id=order.id,
        provider="fake",
        amount_irr=1_000_000,
        currency="IRR",
        status=BillingTransactionStatus.VERIFIED,
    )
    db.add(transaction)
    db.flush()

    result = fulfill_paid_order(db, order.id, transaction.id, now=reference)

    assert result.access_grant.starts_at == current_end
    assert result.access_grant.ends_at == current_end + timedelta(weeks=4)


def test_future_same_package_grant_does_not_delay_new_access(db: Session) -> None:
    reference = datetime(2026, 9, 15, tzinfo=UTC)
    user = User(email="future-extension@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    grant_package(
        db,
        user.id,
        AccessPackageCode.TRAINING,
        source=GrantSource.SUBSCRIPTION,
        starts_at=reference + timedelta(days=5),
        ends_at=reference + timedelta(weeks=4, days=5),
        term_weeks=4,
        idempotency_key="future-training",
    )
    order = BillingOrder(
        user_id=user.id,
        offer_code=BillingOfferCode.TRAINING_4W,
        package_code_snapshot=AccessPackageCode.TRAINING,
        duration_weeks_snapshot=4,
        amount_irr_snapshot=1_000_000,
        currency_snapshot="IRR",
        provider="fake",
        status=BillingOrderStatus.PENDING,
        idempotency_key="future-extension-order",
    )
    db.add(order)
    db.flush()
    transaction = BillingTransaction(
        order_id=order.id,
        provider="fake",
        amount_irr=1_000_000,
        currency="IRR",
        status=BillingTransactionStatus.VERIFIED,
    )
    db.add(transaction)
    db.flush()

    result = fulfill_paid_order(db, order.id, transaction.id, now=reference)

    assert result.access_grant.starts_at == reference
    assert result.access_grant.ends_at == reference + timedelta(weeks=4)
