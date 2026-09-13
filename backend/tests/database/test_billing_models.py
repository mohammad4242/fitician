from sqlalchemy import inspect

from app.billing.models import (
    BillingOrder,
    BillingOfferConfig,
    BillingProviderProduct,
    BillingTransaction,
)


def test_billing_tables_have_snapshot_and_provider_safe_columns() -> None:
    assert set(BillingOfferConfig.__table__.columns.keys()) == {
        "offer_code",
        "price_irr",
        "currency",
        "is_active",
        "available_from",
        "available_until",
        "created_at",
        "updated_at",
    }
    assert set(BillingProviderProduct.__table__.columns.keys()) == {
        "id",
        "offer_code",
        "provider",
        "external_product_id",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert "email" not in BillingOrder.__table__.columns
    assert "phone" not in BillingOrder.__table__.columns
    assert "card_number" not in BillingOrder.__table__.columns
    assert set(BillingTransaction.__table__.columns.keys()) == {
        "id",
        "order_id",
        "provider",
        "provider_reference",
        "amount_irr",
        "currency",
        "status",
        "created_at",
        "updated_at",
        "verified_at",
        "failed_at",
        "refunded_at",
    }


def test_billing_models_are_registered_and_have_required_delete_actions() -> None:
    metadata = BillingOrder.metadata
    assert metadata is BillingTransaction.metadata
    assert {"billing_offer_configs", "billing_provider_products", "billing_orders", "billing_transactions"} <= set(metadata.tables)

    user_fk = next(iter(BillingOrder.__table__.c.user_id.foreign_keys))
    grant_fk = next(iter(BillingOrder.__table__.c.access_grant_id.foreign_keys))
    assert user_fk.target_fullname == "users.id"
    assert user_fk.ondelete == "SET NULL"
    assert grant_fk.target_fullname == "user_access_grants.id"
    assert grant_fk.ondelete == "SET NULL"
    assert inspect(BillingTransaction).local_table is BillingTransaction.__table__
