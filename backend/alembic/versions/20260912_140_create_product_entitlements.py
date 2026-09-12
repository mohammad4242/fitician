"""create persisted product entitlement grants and quota events"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260912_140"
down_revision: str | Sequence[str] | None = "20260912_139"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_access_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("package_code", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_user_access_grants_user_idempotency_key",
        ),
    )
    op.create_index("ix_user_access_grants_user_id", "user_access_grants", ["user_id"])
    op.create_index(
        "ix_user_access_grants_user_id_starts_at_ends_at",
        "user_access_grants",
        ["user_id", "starts_at", "ends_at"],
    )

    op.create_table(
        "entitlement_usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entitlement_key", sa.String(length=128), nullable=False),
        sa.Column("resource_key", sa.String(length=255), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "entitlement_key",
            "resource_key",
            name="uq_entitlement_usage_events_user_entitlement_resource",
        ),
    )
    op.create_index(
        "ix_entitlement_usage_events_user_id",
        "entitlement_usage_events",
        ["user_id"],
    )
    op.create_index(
        "ix_entitlement_usage_events_user_entitlement_occurred",
        "entitlement_usage_events",
        ["user_id", "entitlement_key", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_entitlement_usage_events_user_entitlement_occurred",
        table_name="entitlement_usage_events",
    )
    op.drop_index("ix_entitlement_usage_events_user_id", table_name="entitlement_usage_events")
    op.drop_table("entitlement_usage_events")
    op.drop_index(
        "ix_user_access_grants_user_id_starts_at_ends_at",
        table_name="user_access_grants",
    )
    op.drop_index("ix_user_access_grants_user_id", table_name="user_access_grants")
    op.drop_table("user_access_grants")
