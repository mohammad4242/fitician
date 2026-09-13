"""persist immutable workout cycle logical start"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_151"
down_revision: str | Sequence[str] | None = "20260913_150"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workout_cycles",
        sa.Column("start_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "workout_cycles",
        sa.Column("start_timezone", sa.String(length=64), nullable=True),
    )
    # The original member timezone is unknowable for legacy rows. UTC-date is the
    # conservative fallback because started_at is the only durable historical anchor.
    op.execute(
        "UPDATE workout_cycles "
        "SET start_date = CAST(started_at AT TIME ZONE 'UTC' AS date) "
        "WHERE start_date IS NULL"
    )
    op.alter_column("workout_cycles", "start_date", nullable=False)
    op.alter_column(
        "workout_cycles",
        "start_date",
        server_default=sa.text("CURRENT_DATE"),
    )


def downgrade() -> None:
    op.drop_column("workout_cycles", "start_timezone")
    op.drop_column("workout_cycles", "start_date")
