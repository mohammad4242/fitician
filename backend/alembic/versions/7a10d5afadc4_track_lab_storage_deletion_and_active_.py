"""track lab storage deletion and active deduplication

Revision ID: 7a10d5afadc4
Revises: 20260920_160
Create Date: 2026-09-27 10:04:37.854539

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a10d5afadc4"
down_revision: str | Sequence[str] | None = "20260920_160"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "nutrition_lab_documents",
        sa.Column("storage_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_constraint("uq_nutrition_lab_user_sha256", "nutrition_lab_documents", type_="unique")
    op.create_index(
        "uq_nutrition_lab_user_sha256",
        "nutrition_lab_documents",
        ["user_id", "sha256"],
        unique=True,
        postgresql_where=sa.text("purged_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_nutrition_lab_user_sha256", table_name="nutrition_lab_documents")
    op.create_unique_constraint(
        "uq_nutrition_lab_user_sha256", "nutrition_lab_documents", ["user_id", "sha256"]
    )
    op.drop_column("nutrition_lab_documents", "storage_deleted_at")
