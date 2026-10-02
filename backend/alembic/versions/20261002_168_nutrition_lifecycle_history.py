"""Date-correct nutrition lifecycle history, with conservative legacy baseline."""

import sqlalchemy as sa

from alembic import op

revision = "20261002_168"
down_revision = "20261002_167"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nutrition_plan_lifecycle_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "plan_id",
            sa.Uuid(),
            sa.ForeignKey("nutrition_weekly_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lifecycle_status", sa.String(40), nullable=False),
        sa.Column("is_user_visible", sa.Boolean(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
        sa.CheckConstraint(
            "source IN ('transition','legacy_baseline')", name="ck_nutrition_lifecycle_source"
        ),
    )
    op.create_index(
        "ix_nutrition_lifecycle_user_date",
        "nutrition_plan_lifecycle_events",
        ["user_id", "effective_on", "occurred_at"],
    )
    # A current snapshot is evidence from migration time onward, never old activation history.
    op.execute("""INSERT INTO nutrition_plan_lifecycle_events
        (id,user_id,plan_id,lifecycle_status,is_user_visible,start_date,effective_on,occurred_at,source)
        SELECT gen_random_uuid(),p.user_id,p.id,p.lifecycle_status,p.is_user_visible,p.start_date,
        (CURRENT_TIMESTAMP AT TIME ZONE COALESCE(u.timezone,'Asia/Tehran'))::date,
        CURRENT_TIMESTAMP,'legacy_baseline' FROM nutrition_weekly_plans p
        LEFT JOIN user_profiles u ON u.user_id=p.user_id
        WHERE p.started_at IS NOT NULL OR p.lifecycle_status='active'""")


def downgrade() -> None:
    op.drop_table("nutrition_plan_lifecycle_events")
