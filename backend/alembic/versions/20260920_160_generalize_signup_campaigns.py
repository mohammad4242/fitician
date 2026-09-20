"""generalize signup campaigns and add public marketing fields"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_160"
down_revision: str | Sequence[str] | None = "20260918_159"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "access_campaigns",
        sa.Column("public_badge_fa", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "access_campaigns",
        sa.Column("public_badge_en", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "access_campaigns",
        sa.Column("public_title_fa", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "access_campaigns",
        sa.Column("public_title_en", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "access_campaigns",
        sa.Column("public_message_fa", sa.Text(), nullable=True),
    )
    op.add_column(
        "access_campaigns",
        sa.Column("public_message_en", sa.Text(), nullable=True),
    )
    op.add_column(
        "access_campaigns",
        sa.Column("public_cta_fa", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "access_campaigns",
        sa.Column("public_cta_en", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "access_campaigns",
        sa.Column("show_on_landing", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "access_campaigns",
        sa.Column("show_on_register", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.drop_constraint(
        "ck_access_campaigns_kind_values",
        "access_campaigns",
        type_="check",
    )
    op.drop_constraint(
        "ck_access_campaigns_signup_trial_package",
        "access_campaigns",
        type_="check",
    )
    op.drop_constraint(
        "ck_access_campaigns_manual_promotion_package",
        "access_campaigns",
        type_="check",
    )

    op.execute(
        sa.text(
            "UPDATE access_campaigns "
            "SET kind = 'signup_bonus' "
            "WHERE kind = 'signup_trial'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE access_campaigns "
            "SET is_active = false "
            "WHERE code = 'launch_trial_v1'"
        )
    )

    op.create_check_constraint(
        "ck_access_campaigns_kind_values",
        "access_campaigns",
        "kind IN ('signup_bonus', 'manual_promotion')",
    )
    op.create_check_constraint(
        "ck_access_campaigns_manual_promotion_package",
        "access_campaigns",
        "kind <> 'manual_promotion' "
        "OR package_code NOT IN ('free', 'launch_trial')",
    )
    op.create_check_constraint(
        "ck_access_campaigns_training_duration",
        "access_campaigns",
        "package_code NOT IN ('training', 'training_coach', 'complete', 'complete_care') "
        "OR (term_weeks IS NOT NULL AND duration_days >= term_weeks * 7)",
    )
    op.create_check_constraint(
        "ck_access_campaigns_manual_promotion_private",
        "access_campaigns",
        "kind <> 'manual_promotion' "
        "OR (show_on_landing = false AND show_on_register = false)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_access_campaigns_manual_promotion_private",
        "access_campaigns",
        type_="check",
    )
    op.drop_constraint(
        "ck_access_campaigns_training_duration",
        "access_campaigns",
        type_="check",
    )
    op.drop_constraint(
        "ck_access_campaigns_manual_promotion_package",
        "access_campaigns",
        type_="check",
    )
    op.drop_constraint(
        "ck_access_campaigns_kind_values",
        "access_campaigns",
        type_="check",
    )

    op.execute(
        sa.text(
            "UPDATE access_campaigns "
            "SET kind = 'manual_promotion', is_active = false "
            "WHERE kind = 'signup_bonus' AND package_code <> 'launch_trial'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE access_campaigns "
            "SET kind = 'signup_trial', is_active = false "
            "WHERE kind = 'signup_bonus' AND package_code = 'launch_trial'"
        )
    )

    op.create_check_constraint(
        "ck_access_campaigns_kind_values",
        "access_campaigns",
        "kind IN ('signup_trial', 'manual_promotion')",
    )
    op.create_check_constraint(
        "ck_access_campaigns_signup_trial_package",
        "access_campaigns",
        "kind <> 'signup_trial' OR "
        "(package_code = 'launch_trial' AND term_weeks = 4)",
    )
    op.create_check_constraint(
        "ck_access_campaigns_manual_promotion_package",
        "access_campaigns",
        "kind <> 'manual_promotion' "
        "OR package_code NOT IN ('free', 'launch_trial')",
    )

    op.drop_column("access_campaigns", "show_on_register")
    op.drop_column("access_campaigns", "show_on_landing")
    op.drop_column("access_campaigns", "public_cta_en")
    op.drop_column("access_campaigns", "public_cta_fa")
    op.drop_column("access_campaigns", "public_message_en")
    op.drop_column("access_campaigns", "public_message_fa")
    op.drop_column("access_campaigns", "public_title_en")
    op.drop_column("access_campaigns", "public_title_fa")
    op.drop_column("access_campaigns", "public_badge_en")
    op.drop_column("access_campaigns", "public_badge_fa")
