"""Create bounded meaningful user activity events."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_172"
down_revision = "20261007_171"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_activity_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deduplication_key", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deduplication_key", name="uq_user_activity_events_deduplication_key"),
    )
    op.create_index(
        "ix_user_activity_events_user_id_occurred_at",
        "user_activity_events",
        ["user_id", "occurred_at"],
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_users_created_at",
            "users",
            ["created_at"],
            postgresql_concurrently=True,
        )
    op.create_index(
        "ix_user_activity_events_event_type_occurred_at",
        "user_activity_events",
        ["event_type", "occurred_at"],
    )
    op.create_index(
        "ix_user_activity_events_user_resource",
        "user_activity_events",
        ["user_id", "event_type", "resource_type", "resource_id"],
    )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index("ix_users_created_at", table_name="users", postgresql_concurrently=True)
    op.drop_index(
        "ix_user_activity_events_event_type_occurred_at", table_name="user_activity_events"
    )
    op.drop_index(
        "ix_user_activity_events_user_resource", table_name="user_activity_events"
    )
    op.drop_index("ix_user_activity_events_user_id_occurred_at", table_name="user_activity_events")
    op.drop_table("user_activity_events")
