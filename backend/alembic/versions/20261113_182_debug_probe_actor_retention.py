"""Retain runtime probe audit without preventing account deletion."""

import sqlalchemy as sa

from alembic import op

revision = "20261113_182"
down_revision = "20261112_181"
branch_labels = None
depends_on = None

TABLE = "debug_connector_probes"
CONSTRAINT = "debug_connector_probes_actor_id_fkey"


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.drop_constraint(CONSTRAINT, TABLE, type_="foreignkey")
    op.alter_column(TABLE, "actor_id", nullable=True)
    op.create_foreign_key(CONSTRAINT, TABLE, "users", ["actor_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    # Restoring the old NOT NULL schema must not erase retained audit or invent an actor.
    if op.get_bind().scalar(
        sa.text(f"SELECT EXISTS (SELECT 1 FROM {TABLE} WHERE actor_id IS NULL)")
    ):
        raise RuntimeError("Retained actorless probes require roll-forward; audit was preserved")
    op.drop_constraint(CONSTRAINT, TABLE, type_="foreignkey")
    op.alter_column(TABLE, "actor_id", nullable=False)
    op.create_foreign_key(CONSTRAINT, TABLE, "users", ["actor_id"], ["id"], ondelete="RESTRICT")
