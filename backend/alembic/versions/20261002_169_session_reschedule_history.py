"""Preserve workout schedule changes and their historical coverage."""

import sqlalchemy as sa

from alembic import op

revision = "20261002_169"
down_revision = "20261002_168"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workout_cycle_sessions",
        sa.Column(
            "reschedule_history_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "workout_session_reschedule_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("workout_cycle_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("is_requested", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("from_date != to_date", name="ck_workout_reschedule_real_change"),
    )
    op.create_index(
        "ix_workout_reschedule_session_date",
        "workout_session_reschedule_events",
        ["session_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_table("workout_session_reschedule_events")
    op.drop_column("workout_cycle_sessions", "reschedule_history_started_at")
