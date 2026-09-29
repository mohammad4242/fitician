"""Evidence and idempotent consent for nutrition progress reviews."""

import sqlalchemy as sa

from alembic import op

revision = "20260929_164"
down_revision = "20260929_163"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nutrition_target_update_consents", sa.Column("progress_signature", sa.String(64))
    )
    op.add_column("nutrition_target_update_consents", sa.Column("progress_snapshot", sa.JSON()))
    op.create_unique_constraint(
        "uq_nutrition_progress_consent",
        "nutrition_target_update_consents",
        ["user_id", "progress_signature"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_nutrition_progress_consent", "nutrition_target_update_consents", type_="unique"
    )
    op.drop_column("nutrition_target_update_consents", "progress_snapshot")
    op.drop_column("nutrition_target_update_consents", "progress_signature")
