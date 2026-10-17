"""Persist hashed generation request keys on existing successful outcomes."""

import sqlalchemy as sa

from alembic import op

revision = "20261017_174"
down_revision = "b092f7450d1b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    for table, index in (
        ("workout_plan_generations", "uq_workout_generation_request"),
        ("nutrition_plan_bundles", "uq_nutrition_bundle_request"),
    ):
        op.add_column(table, sa.Column("request_key_hash", sa.String(64), nullable=True))
        op.create_index(
            index,
            table,
            ["user_id", "request_key_hash"],
            unique=True,
            postgresql_where=sa.text("request_key_hash IS NOT NULL"),
        )


def downgrade() -> None:
    for table, index in (
        ("nutrition_plan_bundles", "uq_nutrition_bundle_request"),
        ("workout_plan_generations", "uq_workout_generation_request"),
    ):
        op.drop_index(index, table_name=table)
        op.drop_column(table, "request_key_hash")
