"""Persist payment environment, checkout recovery and bounded reconciliation."""

import sqlalchemy as sa

from alembic import op

revision = "20261123_176"
down_revision = "20261018_175"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in [
        sa.Column("provider_evidence", sa.JSON(), nullable=True),
        sa.Column("provider_mode", sa.String(16), nullable=True),
        sa.Column("checkout_url", sa.String(2000), nullable=True),
        sa.Column("reconcile_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_reconcile_at", sa.DateTime(timezone=True), nullable=True),
    ]:
        op.add_column("billing_transactions", column)
    op.create_index(
        "ix_billing_transactions_reconcile", "billing_transactions", ["next_reconcile_at"]
    )
    op.create_index(
        "ix_billing_transactions_provider_cooldown",
        "billing_transactions",
        ["provider", "provider_mode", sa.text("(provider_evidence ->> 'provider_cooldown_until')")],
        postgresql_where=sa.text("provider_evidence ->> 'provider_cooldown_until' IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_billing_transactions_provider_cooldown", table_name="billing_transactions")
    op.drop_index("ix_billing_transactions_reconcile", table_name="billing_transactions")
    for column in [
        "next_reconcile_at",
        "reconcile_attempts",
        "checkout_url",
        "provider_mode",
        "provider_evidence",
    ]:
        op.drop_column("billing_transactions", column)
