"""Aggregate private SMS alerts and retain retry-safe dispatch audit."""

from alembic import op

revision = "20261112_181"
down_revision = "20261112_180"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("""
CREATE TABLE diagnostic_alert_deliveries (
 id UUID PRIMARY KEY,
 issue_id UUID NOT NULL REFERENCES diagnostic_issues(id) ON DELETE RESTRICT,
 environment VARCHAR(64) NOT NULL,
 state VARCHAR(32) NOT NULL,
 occurrence_total INTEGER NOT NULL,
 covered_count INTEGER NOT NULL,
 generation INTEGER NOT NULL,
 regression_count INTEGER NOT NULL,
 attempts INTEGER NOT NULL,
 provider_message_id VARCHAR(30),
 error_code VARCHAR(64),
 available_at TIMESTAMPTZ NOT NULL,
 last_dispatch_at TIMESTAMPTZ,
 lease_until TIMESTAMPTZ,
 current_attempt_id UUID,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT uq_diagnostic_alert_delivery_scope UNIQUE(issue_id, environment)
)
    """)
    op.create_index(
        "ix_diagnostic_alert_deliveries_issue_id", "diagnostic_alert_deliveries", ["issue_id"]
    )
    op.create_index(
        "ix_diagnostic_alert_delivery_due", "diagnostic_alert_deliveries", ["state", "available_at"]
    )
    op.execute("""
CREATE TABLE diagnostic_alert_attempts (
 id UUID PRIMARY KEY,
 delivery_id UUID NOT NULL REFERENCES diagnostic_alert_deliveries(id) ON DELETE RESTRICT,
 generation INTEGER NOT NULL,
 dispatch_index INTEGER NOT NULL,
 occurrence_total INTEGER NOT NULL,
 message TEXT NOT NULL,
 state VARCHAR(32) NOT NULL,
 provider_message_id VARCHAR(30),
 error_code VARCHAR(64),
 started_at TIMESTAMPTZ NOT NULL,
 finished_at TIMESTAMPTZ,
 receipt_attempts INTEGER NOT NULL,
 next_receipt_at TIMESTAMPTZ,
 CONSTRAINT uq_alert_attempt UNIQUE(delivery_id, generation, dispatch_index)
)
    """)
    op.create_index(
        "ix_diagnostic_alert_attempts_delivery_id", "diagnostic_alert_attempts", ["delivery_id"]
    )
    op.create_index(
        "ix_diagnostic_alert_attempts_started_at", "diagnostic_alert_attempts", ["started_at"]
    )


def downgrade() -> None:
    op.drop_table("diagnostic_alert_attempts")
    op.drop_table("diagnostic_alert_deliveries")
