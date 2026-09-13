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
    op.create_index(
        "uq_nutrition_weekly_plans_one_active_per_user",
        "nutrition_weekly_plans",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("lifecycle_status = 'active'"),
    )
