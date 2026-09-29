"""Register the shared nutrition plan admission policy."""

from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "20260929_165"
down_revision = "20260929_164"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nutrition_weekly_plan_foods",
        sa.Column(
            "quantity_snapshot",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    table = sa.table(
        "nutrition_planner_policy_versions",
        sa.column("version", sa.String()),
        sa.column("planner_version", sa.String()),
        sa.column("meal_distribution_policy", sa.JSON()),
        sa.column("portion_policy", sa.JSON()),
        sa.column("scoring_policy", sa.JSON()),
        sa.column("tolerance_policy", sa.JSON()),
        sa.column("effective_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        table,
        [
            {
                "version": "weekly-planner-shared-admission-v2",
                "planner_version": "nutrition-planner-portion-solver-v2",
                "meal_distribution_policy": {
                    "snack_energy_share": "0.15",
                    "free_meal_energy_reserved": True,
                },
                "portion_policy": {
                    "minimum_g": "10",
                    "maximum_main_food_g": "450",
                    "maximum_snack_food_g": "500",
                },
                "scoring_policy": {
                    "shared_daily_weekly_validation": True,
                    "hard_repetition_cap": True,
                },
                "tolerance_policy": {
                    "calorie_ratio": "0.05",
                    "daily_calorie_ratio": "0.10",
                    "energy_delta_ratio": "0.25",
                    "micronutrient_review_ratio": "0.75",
                    "micronutrient_data_completeness": "0.80",
                    "flexible_budget_overage_cap": "0.15",
                },
                "effective_at": datetime(2026, 9, 29, tzinfo=UTC),
            }
        ],
    )


def downgrade() -> None:
    op.drop_column("nutrition_weekly_plan_foods", "quantity_snapshot")
    op.execute(
        "DELETE FROM nutrition_planner_policy_versions "
        "WHERE version = 'weekly-planner-shared-admission-v2'"
    )
