"""Retain sanitized source evidence retrieved from the exact Sentry event."""

import sqlalchemy as sa

from alembic import op

revision = "20261112_179"
down_revision = "20261112_178"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column(
        "diagnostic_external_events", sa.Column("source_evidence", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("diagnostic_external_events", "source_evidence")
