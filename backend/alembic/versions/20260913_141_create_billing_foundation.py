"""create billing offers, orders, transactions, and grant term metadata"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_141"
down_revision: str | Sequence[str] | None = "20260912_140"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_access_grants",
        sa.Column("term_weeks", sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_user_access_grants_term_weeks_values",
        "user_access_grants",
        "term_weeks IS NULL OR term_weeks IN (4, 6, 8)",
    )

    op.create_table(
        "billing_offer_configs",
        sa.Column("offer_code", sa.String(length=64), nullable=False),
        sa.Column("price_irr", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="IRR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("available_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("price_irr >= 0", name="ck_billing_offer_configs_price_nonnegative"),
        sa.CheckConstraint(
            "available_until IS NULL OR available_from IS NULL "
            "OR available_until >= available_from",
            name="ck_billing_offer_configs_availability_order",
        ),
        sa.PrimaryKeyConstraint("offer_code"),
    )
    op.create_index(
        "ix_billing_offer_configs_active_window",
        "billing_offer_configs",
        ["is_active", "available_from", "available_until"],
    )

    op.create_table(
        "billing_provider_products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_code", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_product_id", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["offer_code"], ["billing_offer_configs.offer_code"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "external_product_id", name="uq_billing_provider_products_provider_external"
        ),
        sa.UniqueConstraint(
            "provider", "offer_code", name="uq_billing_provider_products_provider_offer"
        ),
    )
    op.create_index(
        "ix_billing_provider_products_offer_active",
        "billing_provider_products",
        ["offer_code", "is_active"],
    )

    op.create_table(
        "billing_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("offer_code", sa.String(length=64), nullable=False),
        sa.Column("package_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("duration_weeks_snapshot", sa.SmallInteger(), nullable=False),
        sa.Column("amount_irr_snapshot", sa.BigInteger(), nullable=False),
        sa.Column("currency_snapshot", sa.String(length=8), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_grant_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "duration_weeks_snapshot IN (4, 6, 8)",
            name="ck_billing_orders_duration_values",
        ),
        sa.CheckConstraint("amount_irr_snapshot >= 0", name="ck_billing_orders_amount_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["access_grant_id"], ["user_access_grants.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_billing_orders_user_idempotency"
        ),
    )
    op.create_index("ix_billing_orders_user_status", "billing_orders", ["user_id", "status"])
    op.create_index("ix_billing_orders_user_created", "billing_orders", ["user_id", "created_at"])
    op.create_index("ix_billing_orders_status_expires", "billing_orders", ["status", "expires_at"])

    op.create_table(
        "billing_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("amount_irr", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount_irr >= 0", name="ck_billing_transactions_amount_nonnegative"),
        sa.ForeignKeyConstraint(["order_id"], ["billing_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "provider_reference", name="uq_billing_transactions_provider_reference"
        ),
    )
    op.create_index(
        "ix_billing_transactions_order_status",
        "billing_transactions",
        ["order_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_billing_transactions_order_status", table_name="billing_transactions")
    op.drop_table("billing_transactions")
    op.drop_index("ix_billing_orders_status_expires", table_name="billing_orders")
    op.drop_index("ix_billing_orders_user_created", table_name="billing_orders")
    op.drop_index("ix_billing_orders_user_status", table_name="billing_orders")
    op.drop_table("billing_orders")
    op.drop_index(
        "ix_billing_provider_products_offer_active",
        table_name="billing_provider_products",
    )
    op.drop_table("billing_provider_products")
    op.drop_index("ix_billing_offer_configs_active_window", table_name="billing_offer_configs")
    op.drop_table("billing_offer_configs")
    op.drop_constraint(
        "ck_user_access_grants_term_weeks_values",
        "user_access_grants",
        type_="check",
    )
    op.drop_column("user_access_grants", "term_weeks")
