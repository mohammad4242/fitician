"""Allow durable read-only host observations without granting deployment authority."""

from alembic import op

revision = "20261114_185"
down_revision = "20261113_184"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.drop_constraint("ck_debug_operation_kind", "debug_operations", type_="check")
    op.create_check_constraint(
        "ck_debug_operation_kind",
        "debug_operations",
        "kind IN ('validate','publish_pr','deploy','observe')",
    )


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM debug_operations WHERE kind='observe') "
        "THEN RAISE EXCEPTION 'Retain host observation audit; use application rollback'; "
        "END IF; END $$"
    )
    op.drop_constraint("ck_debug_operation_kind", "debug_operations", type_="check")
    op.create_check_constraint(
        "ck_debug_operation_kind", "debug_operations", "kind IN ('validate','publish_pr','deploy')"
    )
