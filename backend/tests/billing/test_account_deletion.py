from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth.models import User
from app.billing.enums import BillingOfferCode, BillingOrderStatus, BillingTransactionStatus
from app.billing.models import BillingOrder, BillingTransaction


def test_account_deletion_anonymizes_order_owner_and_retains_transactions(db: Session) -> None:
    user = User(email="billing-deletion@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    order = BillingOrder(
        user_id=user.id,
        offer_code=BillingOfferCode.TRAINING_4W,
        package_code_snapshot="training",
        duration_weeks_snapshot=4,
        amount_irr_snapshot=1_000_000,
        currency_snapshot="IRR",
        provider="fake",
        status=BillingOrderStatus.PAID,
        idempotency_key="deletion-order",
    )
    db.add(order)
    db.flush()
    transaction = BillingTransaction(
        order_id=order.id,
        provider="fake",
        provider_reference="fake-deletion-reference",
        amount_irr=1_000_000,
        currency="IRR",
        status=BillingTransactionStatus.VERIFIED,
    )
    db.add(transaction)
    db.flush()

    db.execute(delete(User).where(User.id == user.id))
    db.flush()
    db.expire_all()

    retained_order = db.get(BillingOrder, order.id)
    retained_transaction = db.get(BillingTransaction, transaction.id)
    assert retained_order is not None
    assert retained_order.user_id is None
    assert retained_transaction is not None
    assert retained_transaction.order_id == order.id
