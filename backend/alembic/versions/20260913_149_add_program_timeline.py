"""add explicit program timeline state"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_149"
down_revision: str | Sequence[str] | None = "20260913_148"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD_NUTRITION_LIFECYCLE_VALUES = (
    "'draft', 'generated', 'pending_physician_review', 'physician_review_in_progress', "
    "'awaiting_lab_information', 'changes_requested', 'physician_approved', 'active', "
    "'archived', 'rejected'"
)
_NEW_NUTRITION_LIFECYCLE_VALUES = (
    "'draft', 'generated', 'pending_physician_review', 'physician_review_in_progress', "
    "'awaiting_lab_information', 'changes_requested', 'physician_approved', "
    "'ready_to_start', 'active', 'archived', 'rejected'"
)


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
    )
    op.add_column(
        "nutrition_weekly_plans",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_constraint(
        "ck_nutrition_weekly_plan_lifecycle_values",
        "nutrition_weekly_plans",
        type_="check",
    )
    op.create_check_constraint(
        "ck_nutrition_weekly_plan_lifecycle_values",
        "nutrition_weekly_plans",
        f"lifecycle_status IN ({_NEW_NUTRITION_LIFECYCLE_VALUES})",
    )

    op.create_table(
        "workout_cycle_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("workout_day_id", sa.Uuid(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("session_number", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="scheduled"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "week_number >= 1",
            name="ck_workout_cycle_sessions_week_number_positive",
        ),
        sa.CheckConstraint(
            "session_number >= 1",
            name="ck_workout_cycle_sessions_session_number_positive",
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'completed', 'skipped')",
            name="ck_workout_cycle_sessions_status_values",
        ),
        sa.CheckConstraint(
            "(status = 'scheduled' AND completed_at IS NULL AND skipped_at IS NULL) OR "
            "(status = 'completed' AND completed_at IS NOT NULL AND skipped_at IS NULL) OR "
            "(status = 'skipped' AND skipped_at IS NOT NULL AND completed_at IS NULL)",
            name="ck_workout_cycle_sessions_timestamp_integrity",
        ),
        sa.ForeignKeyConstraint(["cycle_id"], ["workout_cycles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workout_day_id"], ["workout_days.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cycle_id",
            "session_number",
            name="uq_workout_cycle_sessions_cycle_session_number",
        ),
        sa.UniqueConstraint(
            "cycle_id",
            "week_number",
            "workout_day_id",
            name="uq_workout_cycle_sessions_cycle_week_day",
        ),
    )
    op.create_index(
        "ix_workout_cycle_sessions_cycle_id", "workout_cycle_sessions", ["cycle_id"]
    )
    op.create_index(
        "ix_workout_cycle_sessions_scheduled_date",
        "workout_cycle_sessions",
        ["scheduled_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workout_cycle_sessions_scheduled_date", table_name="workout_cycle_sessions"
    )
    op.drop_index("ix_workout_cycle_sessions_cycle_id", table_name="workout_cycle_sessions")
    op.drop_table("workout_cycle_sessions")
    op.drop_constraint(
        "ck_nutrition_weekly_plan_lifecycle_values",
        "nutrition_weekly_plans",
        type_="check",
    )
    op.create_check_constraint(
        "ck_nutrition_weekly_plan_lifecycle_values",
        "nutrition_weekly_plans",
        f"lifecycle_status IN ({_OLD_NUTRITION_LIFECYCLE_VALUES})",
    )
    op.drop_column("nutrition_weekly_plans", "started_at")
    op.drop_column("user_profiles", "timezone")
