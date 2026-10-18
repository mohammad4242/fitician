"""Add bounded trace span metadata to existing diagnostic events."""

import sqlalchemy as sa

from alembic import op

revision = "20261018_175"
down_revision = "20261017_174"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("diagnostic_events", sa.Column("app_version", sa.String(64), nullable=True))
    op.add_column("diagnostic_events", sa.Column("origin_platform", sa.String(32), nullable=True))
    for name, kind in (
        ("trace_id", sa.String(32)),
        ("span_id", sa.String(16)),
        ("parent_span_id", sa.String(16)),
        ("clock_domain", sa.String(64)),
        ("started_at", sa.DateTime(timezone=True)),
        ("ended_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("diagnostic_events", sa.Column(name, kind, nullable=True))
    op.add_column(
        "diagnostic_events",
        sa.Column("record_type", sa.String(8), nullable=False, server_default="event"),
    )
    for name in ("offset_ms", "dropped_count", "expected_span_count"):
        op.add_column(
            "diagnostic_events", sa.Column(name, sa.Integer(), nullable=False, server_default="0")
        )
    op.create_index(
        "ix_diagnostic_events_trace_span", "diagnostic_events", ["trace_id", "span_id", "timestamp"]
    )
    op.create_index(
        "ix_diagnostic_events_record_time", "diagnostic_events", ["record_type", "timestamp"]
    )

    for table in (
        "body_analyses",
        "nutrition_food_photo_analysis_jobs",
        "notification_outbox_events",
    ):
        for name, size in (
            ("trace_id", 32),
            ("trace_parent_span_id", 16),
            ("trace_operation_id", 128),
        ):
            op.add_column(table, sa.Column(name, sa.String(size), nullable=True))


def downgrade() -> None:
    for table in (
        "body_analyses",
        "nutrition_food_photo_analysis_jobs",
        "notification_outbox_events",
    ):
        for name in ("trace_operation_id", "trace_parent_span_id", "trace_id"):
            op.drop_column(table, name)
    op.drop_column("diagnostic_events", "app_version")
    op.drop_column("diagnostic_events", "origin_platform")
    op.drop_index("ix_diagnostic_events_record_time", table_name="diagnostic_events")
    op.drop_index("ix_diagnostic_events_trace_span", table_name="diagnostic_events")
    for name in (
        "expected_span_count",
        "dropped_count",
        "offset_ms",
        "record_type",
        "ended_at",
        "started_at",
        "clock_domain",
        "parent_span_id",
        "span_id",
        "trace_id",
    ):
        op.drop_column("diagnostic_events", name)
