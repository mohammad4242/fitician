"""make workout review claims persistent"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260914_154"
down_revision: str | Sequence[str] | None = "20260914_153"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_workout_plan_reviews_lease_fields_consistent",
        "workout_plan_reviews",
        type_="check",
    )
    op.execute(
        """
        UPDATE workout_plan_reviews
        SET status = 'pending',
            claimed_by_user_id = NULL,
            lease_acquired_at = NULL,
            lease_expires_at = NULL
        WHERE status = 'claimed'
          AND lease_expires_at IS NOT NULL
          AND lease_expires_at <= CURRENT_TIMESTAMP
        """
    )
    op.execute(
        """
        UPDATE workout_plan_reviews
        SET lease_expires_at = NULL
        WHERE status = 'claimed'
        """
    )
    op.create_check_constraint(
        "ck_workout_plan_reviews_lease_fields_consistent",
        "workout_plan_reviews",
        "(claimed_by_user_id IS NULL AND lease_acquired_at IS NULL "
        "AND lease_expires_at IS NULL) OR "
        "(claimed_by_user_id IS NOT NULL AND lease_acquired_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_workout_plan_reviews_lease_fields_consistent",
        "workout_plan_reviews",
        type_="check",
    )
    op.execute(
        """
        UPDATE workout_plan_reviews
        SET lease_expires_at = COALESCE(lease_acquired_at, CURRENT_TIMESTAMP)
            + INTERVAL '30 minutes'
        WHERE claimed_by_user_id IS NOT NULL
        """
    )
    op.create_check_constraint(
        "ck_workout_plan_reviews_lease_fields_consistent",
        "workout_plan_reviews",
        "(claimed_by_user_id IS NULL AND lease_acquired_at IS NULL "
        "AND lease_expires_at IS NULL) OR "
        "(claimed_by_user_id IS NOT NULL AND lease_acquired_at IS NOT NULL "
        "AND lease_expires_at IS NOT NULL)",
    )
