"""add safe request correlation ids to durable jobs"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260918_157"
down_revision: str | Sequence[str] | None = "20260918_156"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in (
        "body_analyses",
        "nutrition_food_photo_analysis_jobs",
        "notification_outbox_events",
    ):
        op.add_column(
            table_name,
            sa.Column("correlation_id", sa.String(length=128), nullable=True),
        )
        op.create_index(
            f"ix_{table_name}_correlation_id",
            table_name,
            ["correlation_id"],
        )


def downgrade() -> None:
    for table_name in (
        "notification_outbox_events",
        "nutrition_food_photo_analysis_jobs",
        "body_analyses",
    ):
        op.drop_index(f"ix_{table_name}_correlation_id", table_name=table_name)
        op.drop_column(table_name, "correlation_id")
