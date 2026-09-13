"""harden access campaign package semantics"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260913_148"
down_revision: str | Sequence[str] | None = "20260913_147"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_constraint(
        "ck_access_campaigns_manual_promotion_package",
        "access_campaigns",
        type_="check",
    )
    op.drop_constraint(
        "ck_access_campaigns_signup_trial_package",
        "access_campaigns",
        type_="check",
    )
