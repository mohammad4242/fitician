"""Persist explicit API debug execution targets without changing generation routing."""

import sqlalchemy as sa

from alembic import op

revision = "20261113_183"
down_revision = "20261113_182"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("ai_task_configs", sa.Column("debug_connector_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_ai_task_configs_debug_connector",
        "ai_task_configs",
        "debug_connectors",
        ["debug_connector_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_ai_task_configs_debug_connector_task",
        "ai_task_configs",
        "debug_connector_id IS NULL OR task_type = 'debug_agent'",
    )


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM ai_task_configs WHERE debug_connector_id IS NOT NULL)"
        )
    ):
        raise RuntimeError("Clear the selected debug target explicitly before schema downgrade")
    op.drop_constraint("ck_ai_task_configs_debug_connector_task", "ai_task_configs", type_="check")
    op.drop_constraint("fk_ai_task_configs_debug_connector", "ai_task_configs", type_="foreignkey")
    op.drop_column("ai_task_configs", "debug_connector_id")
