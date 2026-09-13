"""allow overlapping started nutrition plans for date-effective handoffs"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260914_152"
down_revision: str | Sequence[str] | None = "20260913_151"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(
        "uq_nutrition_weekly_plans_one_active_per_user",
        table_name="nutrition_weekly_plans",
    )
    op.create_index(
        "ix_nutrition_weekly_plans_user_active_start",
        "nutrition_weekly_plans",
        ["user_id", "start_date", "revision"],
        unique=False,
        postgresql_where=sa.text("lifecycle_status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nutrition_weekly_plans_user_active_start",
        table_name="nutrition_weekly_plans",
    )
    # The pre-handoff schema allowed one active row per user. Preserve every
    # plan row and keep the plan that was effective on the downgrade date; if
    # there is no started plan, keep the earliest scheduled successor.
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY user_id
                        ORDER BY
                            CASE WHEN start_date <= CURRENT_DATE THEN 0 ELSE 1 END,
                            CASE WHEN start_date <= CURRENT_DATE THEN start_date END DESC NULLS LAST,
                            CASE WHEN start_date > CURRENT_DATE THEN start_date END ASC NULLS LAST,
                            revision DESC,
                            created_at DESC,
                            id DESC
                    ) AS plan_rank
                FROM nutrition_weekly_plans
                WHERE lifecycle_status = 'active'
            )
            UPDATE nutrition_weekly_plans AS plan
            SET lifecycle_status = 'archived', is_user_visible = FALSE
            FROM ranked
            WHERE plan.id = ranked.id AND ranked.plan_rank > 1
            """
        )
    )
    op.create_index(
        "uq_nutrition_weekly_plans_one_active_per_user",
        "nutrition_weekly_plans",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("lifecycle_status = 'active'"),
    )
