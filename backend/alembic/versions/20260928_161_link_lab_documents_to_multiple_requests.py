"""link nutrition lab documents to multiple physician requests"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_161"
down_revision: str | Sequence[str] | None = "7a10d5afadc4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nutrition_lab_document_requests",
        sa.Column(
            "lab_document_id",
            sa.Uuid(),
            sa.ForeignKey("nutrition_lab_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lab_request_id",
            sa.Uuid(),
            sa.ForeignKey("nutrition_lab_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "linked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "lab_document_id", "lab_request_id", name="pk_nutrition_lab_document_requests"
        ),
    )
    op.create_index(
        "ix_nutrition_lab_document_requests_lab_request_id",
        "nutrition_lab_document_requests",
        ["lab_request_id"],
    )
    op.execute(
        sa.text(
            """
            INSERT INTO nutrition_lab_document_requests (lab_document_id, lab_request_id, linked_at)
            SELECT id, request_id, COALESCE(uploaded_at, now())
            FROM nutrition_lab_documents
            WHERE request_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nutrition_lab_document_requests_lab_request_id",
        table_name="nutrition_lab_document_requests",
    )
    op.drop_table("nutrition_lab_document_requests")
