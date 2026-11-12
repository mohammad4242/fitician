"""Add immutable diagnostic evidence and many-to-many external issue references."""

import sqlalchemy as sa

from alembic import op

revision = "20261112_176"
down_revision = "20261018_175"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "diagnostic_evidence_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("diagnostic_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "issue_id",
            sa.Uuid(),
            sa.ForeignKey("diagnostic_issues.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("evidence_version", sa.String(64), nullable=False),
        sa.Column("redaction_version", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("sentry_event_id", sa.String(32)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("event_id", name="uq_diagnostic_evidence_event"),
    )
    op.create_index(
        "ix_diagnostic_evidence_snapshots_issue_id", "diagnostic_evidence_snapshots", ["issue_id"]
    )
    op.create_table(
        "diagnostic_external_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.String(100), nullable=False),
        sa.Column("external_event_id", sa.String(32), nullable=False),
        sa.Column("external_issue_id", sa.String(100)),
        sa.Column(
            "local_event_id", sa.Uuid(), sa.ForeignKey("diagnostic_events.id", ondelete="SET NULL")
        ),
        sa.Column("environment", sa.String(64), nullable=False),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("sync_state", sa.String(32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("project_id", "external_event_id", name="uq_diagnostic_external_event"),
    )
    op.create_index(
        "ix_diagnostic_external_event_local", "diagnostic_external_events", ["local_event_id"]
    )
    op.create_table(
        "diagnostic_external_issue_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "issue_id",
            sa.Uuid(),
            sa.ForeignKey("diagnostic_issues.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("project_id", sa.String(100), nullable=False),
        sa.Column("external_issue_id", sa.String(100), nullable=False),
        sa.Column("environment", sa.String(64), nullable=False),
        sa.Column(
            "observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "issue_id",
            "project_id",
            "external_issue_id",
            "environment",
            name="uq_diagnostic_external_issue_link",
        ),
    )
    op.create_index(
        "ix_diagnostic_external_issue_links_issue_id",
        "diagnostic_external_issue_links",
        ["issue_id"],
    )


def downgrade() -> None:
    op.drop_table("diagnostic_external_issue_links")
    op.drop_table("diagnostic_external_events")
    op.drop_table("diagnostic_evidence_snapshots")
