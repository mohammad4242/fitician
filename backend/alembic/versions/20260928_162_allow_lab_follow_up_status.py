"""allow physician lab follow-up status"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_162"
down_revision: str | Sequence[str] | None = "20260928_161"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_nutrition_lab_document_review_status",
        "nutrition_lab_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_nutrition_lab_document_review_status",
        "nutrition_lab_documents",
        "review_status IN ('unreviewed','reviewed','rejected','requires_follow_up')",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE nutrition_lab_documents "
            "SET review_status = 'rejected' "
            "WHERE review_status = 'requires_follow_up'"
        )
    )
    op.drop_constraint(
        "ck_nutrition_lab_document_review_status",
        "nutrition_lab_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_nutrition_lab_document_review_status",
        "nutrition_lab_documents",
        "review_status IN ('unreviewed','reviewed','rejected')",
    )
