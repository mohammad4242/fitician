"""add generic distributed rate-limit fallback counters"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260918_158"
down_revision: str | Sequence[str] | None = "20260918_157"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "distributed_rate_limit_counters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("namespace", sa.String(length=48), nullable=False),
        sa.Column("actor_hash", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "namespace",
            "actor_hash",
            "operation",
            "window_started_at",
            name="uq_distributed_rate_limit_window",
        ),
    )
    op.create_index(
        "ix_distributed_rate_limit_counters_actor_hash",
        "distributed_rate_limit_counters",
        ["actor_hash"],
    )
    op.create_index(
        "ix_distributed_rate_limit_lookup",
        "distributed_rate_limit_counters",
        ["namespace", "actor_hash", "operation"],
    )


def downgrade() -> None:
    op.drop_index("ix_distributed_rate_limit_lookup", table_name="distributed_rate_limit_counters")
    op.drop_index(
        "ix_distributed_rate_limit_counters_actor_hash",
        table_name="distributed_rate_limit_counters",
    )
    op.drop_table("distributed_rate_limit_counters")

