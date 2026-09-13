from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import BillingOfferCode, BillingOrderStatus, BillingTransactionStatus
from app.billing.fulfillment import fulfill_paid_order
from app.billing.models import BillingOrder, BillingTransaction
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.service import grant_package


def make_order(
    db: Session,
    package: AccessPackageCode,
    duration: int,
) -> tuple[BillingOrder, BillingTransaction]:
    user = User(email=f"overlap-{package.value}@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    order = BillingOrder(
        user_id=user.id,
        offer_code=BillingOfferCode(f"{package.value}_{duration}w"),
        package_code_snapshot=package,
        duration_weeks_snapshot=duration,
        amount_irr_snapshot=1_000_000,
        currency_snapshot="IRR",
        provider="fake",
        status=BillingOrderStatus.PENDING,
        idempotency_key=f"overlap-{user.id}",
    )
    db.add(order)
    db.flush()
    transaction = BillingTransaction(
        order_id=order.id,
        provider="fake",
        amount_irr=order.amount_irr_snapshot,
        currency="IRR",
        status=BillingTransactionStatus.VERIFIED,
    )
    db.add(transaction)
    db.flush()
    order.status = BillingOrderStatus.PENDING
    return order, transaction


def test_paid_package_starts_after_active_launch_trial(db: Session) -> None:
    reference = datetime(2026, 9, 15, tzinfo=UTC)
    trial_end = reference + timedelta(days=10)
    order, transaction = make_order(db, AccessPackageCode.NUTRITION, 4)
    grant_package(
        db,
        order.user_id,
        AccessPackageCode.LAUNCH_TRIAL,
        source=GrantSource.LAUNCH_TRIAL,
        starts_at=reference - timedelta(days=5),
        ends_at=trial_end,
        idempotency_key="launch-trial-overlap",
    )

    result = fulfill_paid_order(
        db,
        order.id,
        transaction.id,
        now=reference,
    )

    assert result.access_grant.starts_at == trial_end
    assert result.access_grant.ends_at == trial_end + timedelta(weeks=4)
