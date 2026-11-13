"""Retain issue-scoped CI/publication/deployment intent and uncertain outcomes."""

import sqlalchemy as sa

from alembic import op

revision = "20261113_184"
down_revision = "20261113_183"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column(
        "debug_connectors",
        sa.Column("kind", sa.String(16), nullable=False, server_default="runtime"),
    )
    op.create_check_constraint(
        "ck_debug_connector_kind", "debug_connectors", "kind IN ('runtime','automation')"
    )
    op.create_index(
        "uq_debug_automation_worker_env",
        "debug_connectors",
        ["environment"],
        unique=True,
        postgresql_where=sa.text("kind = 'automation' AND revoked = false"),
    )
    op.create_table(
        "debug_operations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "run_id", sa.Uuid(), sa.ForeignKey("debug_runs.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("occurrence_id", sa.Uuid()),
        sa.Column(
            "worker_id",
            sa.Uuid(),
            sa.ForeignKey("debug_connectors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("environment", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("submission_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("target_environment", sa.String(64)),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(64)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("run_id", "submission_key", name="uq_debug_operation_submission"),
        sa.CheckConstraint(
            "kind IN ('validate','publish_pr','deploy')", name="ck_debug_operation_kind"
        ),
        sa.CheckConstraint(
            "kind <> 'deploy' OR (target_environment IS NOT NULL AND "
            "target_environment IN ('production-iran','production-germany'))",
            name="ck_debug_operation_deployment_target",
        ),
        sa.CheckConstraint(
            "state IN ('queued','preparing','dispatching','uncertain','running',"
            "'awaiting_authorization','deploying','verifying','succeeded','failed','cancelled','blocked')",
            name="ck_debug_operation_state",
        ),
    )
    op.create_index("ix_debug_operations_run_id", "debug_operations", ["run_id"])
    op.create_index(
        "ix_debug_operation_claim", "debug_operations", ["environment", "state", "lease_until"]
    )
    op.create_index(
        "uq_debug_operation_deployment_target",
        "debug_operations",
        ["environment", "target_environment"],
        unique=True,
        postgresql_where=sa.text(
            "kind = 'deploy' AND state IN ('queued','preparing','dispatching','uncertain',"
            "'running','awaiting_authorization','deploying','verifying')"
        ),
    )


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM debug_operations)")):
        raise RuntimeError("Retain operation audit; explicitly archive it before schema downgrade")
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM debug_connectors WHERE kind = 'automation')")
    ):
        raise RuntimeError("Retain automation identity before schema downgrade")
    op.drop_table("debug_operations")
    op.drop_index("uq_debug_automation_worker_env", "debug_connectors")
    op.drop_constraint("ck_debug_connector_kind", "debug_connectors", type_="check")
    op.drop_column("debug_connectors", "kind")
