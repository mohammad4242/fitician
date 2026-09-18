"""add durable body analysis queue lease fields"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260918_156"
down_revision: str | Sequence[str] | None = "20260915_155"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "body_analyses",
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "body_analyses",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "body_analyses",
        sa.Column("locked_by", sa.String(length=80), nullable=True),
    )
    op.create_index(
        "ix_body_analyses_available_at",
        "body_analyses",
        ["available_at"],
    )
    op.create_index(
        "ix_body_analyses_queue_claim",
        "body_analyses",
        ["status", "available_at", "locked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_body_analyses_queue_claim", table_name="body_analyses")
    op.drop_index("ix_body_analyses_available_at", table_name="body_analyses")
    op.drop_column("body_analyses", "locked_by")
    op.drop_column("body_analyses", "locked_at")
    op.drop_column("body_analyses", "available_at")
