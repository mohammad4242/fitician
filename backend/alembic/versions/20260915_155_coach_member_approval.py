"""add coach proposal and member acceptance workflow"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260915_155"
down_revision: str | Sequence[str] | None = "20260914_154"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_workout_plan_reviews_status_values",
        "workout_plan_reviews",
        type_="check",
    )
    op.alter_column(
        "workout_plan_reviews",
        "status",
        existing_type=sa.String(length=10),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_workout_plan_reviews_status_values",
        "workout_plan_reviews",
        "status IN ('pending', 'claimed', 'awaiting_member_acceptance', "
        "'member_changes_requested', 'approved', 'rejected', 'superseded')",
    )
    op.add_column(
        "workout_plan_reviews",
        sa.Column("proposed_plan_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "workout_plan_reviews",
        sa.Column("member_rejection_note", sa.String(length=2000), nullable=True),
    )
    op.create_check_constraint(
        "ck_workout_plan_reviews_member_rejection_note_length",
        "workout_plan_reviews",
        "member_rejection_note IS NULL OR char_length(member_rejection_note) <= 2000",
    )
    op.create_foreign_key(
        "fk_workout_plan_reviews_proposed_plan_id",
        "workout_plan_reviews",
        "workout_plans",
        ["proposed_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_workout_plan_reviews_proposed_plan_id",
        "workout_plan_reviews",
        ["proposed_plan_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_workout_plan_reviews_proposed_plan_id",
        "workout_plan_reviews",
        type_="unique",
    )
    op.drop_constraint(
        "fk_workout_plan_reviews_proposed_plan_id",
        "workout_plan_reviews",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_workout_plan_reviews_member_rejection_note_length",
        "workout_plan_reviews",
        type_="check",
    )
    op.drop_column("workout_plan_reviews", "member_rejection_note")
    op.drop_column("workout_plan_reviews", "proposed_plan_id")
    op.drop_constraint(
        "ck_workout_plan_reviews_status_values",
        "workout_plan_reviews",
        type_="check",
    )
    op.alter_column(
        "workout_plan_reviews",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_workout_plan_reviews_status_values",
        "workout_plan_reviews",
        "status IN ('pending', 'claimed', 'approved', 'rejected', 'superseded')",
    )
