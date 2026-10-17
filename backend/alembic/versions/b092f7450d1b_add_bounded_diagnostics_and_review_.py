"""add bounded diagnostics and review quota reservations

Revision ID: b092f7450d1b
Revises: 20261007_172
Create Date: 2026-10-16 22:43:13.873499

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b092f7450d1b"
down_revision: Union[str, Sequence[str], None] = "20261007_172"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "diagnostic_issues",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("component", sa.String(length=80), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("exception_type", sa.String(length=100), nullable=True),
        sa.Column("source_location", sa.String(length=160), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("regression_count", sa.Integer(), nullable=False),
        sa.Column("last_alert_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_diagnostic_issue_fingerprint"),
    )
    op.create_index(
        "ix_diagnostic_issues_last_seen", "diagnostic_issues", ["last_seen"], unique=False
    )
    op.create_index(
        "ix_diagnostic_issues_seen_status_severity",
        "diagnostic_issues",
        ["last_seen", "status", "severity"],
        unique=False,
    )
    op.create_index(
        "ix_diagnostic_issues_status_severity",
        "diagnostic_issues",
        ["status", "severity"],
        unique=False,
    )
    op.create_table(
        "diagnostic_alerts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["diagnostic_issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_diagnostic_alerts_created_at", "diagnostic_alerts", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_diagnostic_alerts_issue_id"), "diagnostic_alerts", ["issue_id"], unique=False
    )
    op.create_table(
        "diagnostic_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("operation_id", sa.String(length=128), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("component", sa.String(length=80), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("build", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("exception_type", sa.String(length=100), nullable=True),
        sa.Column("source_location", sa.String(length=160), nullable=True),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("os_version", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["issue_id"], ["diagnostic_issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_diagnostic_events_issue_id"), "diagnostic_events", ["issue_id"], unique=False
    )
    op.create_index(
        "ix_diagnostic_events_operation_id_timestamp",
        "diagnostic_events",
        ["operation_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_diagnostic_events_operation_outcome_timestamp",
        "diagnostic_events",
        ["operation", "outcome", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_diagnostic_events_request_timestamp",
        "diagnostic_events",
        ["request_id", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_diagnostic_events_timestamp", "diagnostic_events", ["timestamp"], unique=False
    )
    op.create_index(
        op.f("ix_diagnostic_events_user_id"), "diagnostic_events", ["user_id"], unique=False
    )
    op.create_index(
        "ix_diagnostic_events_resource_attempt",
        "diagnostic_events",
        ["resource_id", "component", "retry_count"],
        unique=False,
    )
    op.create_table(
        "diagnostic_status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("previous_status", sa.String(length=20), nullable=False),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["issue_id"], ["diagnostic_issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_diagnostic_status_history_created_at",
        "diagnostic_status_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_diagnostic_status_history_issue_id"),
        "diagnostic_status_history",
        ["issue_id"],
        unique=False,
    )
    op.create_table(
        "entitlement_quota_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entitlement_key", sa.String(length=128), nullable=False),
        sa.Column("resource_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "entitlement_key", "resource_key", name="uq_quota_reservation_resource"
        ),
    )
    op.create_index(
        "ix_quota_reservation_user_entitlement",
        "entitlement_quota_reservations",
        ["user_id", "entitlement_key"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index(
        "ix_quota_reservation_user_entitlement", table_name="entitlement_quota_reservations"
    )
    op.drop_table("entitlement_quota_reservations")
    op.drop_index(
        op.f("ix_diagnostic_status_history_issue_id"), table_name="diagnostic_status_history"
    )
    op.drop_index("ix_diagnostic_status_history_created_at", table_name="diagnostic_status_history")
    op.drop_table("diagnostic_status_history")
    op.drop_index(op.f("ix_diagnostic_events_user_id"), table_name="diagnostic_events")
    op.drop_index("ix_diagnostic_events_timestamp", table_name="diagnostic_events")
    op.drop_index("ix_diagnostic_events_request_timestamp", table_name="diagnostic_events")
    op.drop_index(
        "ix_diagnostic_events_operation_outcome_timestamp", table_name="diagnostic_events"
    )
    op.drop_index("ix_diagnostic_events_operation_id_timestamp", table_name="diagnostic_events")
    op.drop_index(op.f("ix_diagnostic_events_issue_id"), table_name="diagnostic_events")
    op.drop_index("ix_diagnostic_events_resource_attempt", table_name="diagnostic_events")
    op.drop_table("diagnostic_events")
    op.drop_index(op.f("ix_diagnostic_alerts_issue_id"), table_name="diagnostic_alerts")
    op.drop_index("ix_diagnostic_alerts_created_at", table_name="diagnostic_alerts")
    op.drop_table("diagnostic_alerts")
    op.drop_index("ix_diagnostic_issues_status_severity", table_name="diagnostic_issues")
    op.drop_index("ix_diagnostic_issues_seen_status_severity", table_name="diagnostic_issues")
    op.drop_index("ix_diagnostic_issues_last_seen", table_name="diagnostic_issues")
    op.drop_table("diagnostic_issues")
    # ### end Alembic commands ###
