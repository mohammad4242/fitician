"""harden access campaign semantic constraints"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260913_146"
down_revision: str | Sequence[str] | None = "20260913_145"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_access_campaigns_training_term",
        "access_campaigns",
        "package_code NOT IN ('training', 'training_coach', 'complete', 'complete_care') "
        "OR term_weeks IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_access_campaigns_training_term",
        "access_campaigns",
        type_="check",
    )
