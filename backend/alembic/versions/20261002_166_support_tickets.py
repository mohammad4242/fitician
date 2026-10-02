"""Private support tickets and conversations."""

import sqlalchemy as sa

from alembic import op

revision = "20261002_166"
down_revision = "20260929_165"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("creation_digest", sa.String(64), nullable=False),
        sa.Column("category", sa.String(15), nullable=False),
        sa.Column("subject", sa.String(160), nullable=False),
        sa.Column("status", sa.String(13), nullable=False),
        sa.Column("troubleshooting_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "request_id", name="uq_support_ticket_request"),
        sa.CheckConstraint(
            "char_length(btrim(subject)) BETWEEN 1 AND 160", name="ck_support_ticket_subject"
        ),
        sa.CheckConstraint(
            "category IN ('technical', 'account', 'billing', 'workout', 'nutrition', "
            "'body_analysis', 'feature_request', 'other')",
            name="ck_support_ticket_category",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'awaiting_user', 'resolved', 'closed')",
            name="ck_support_ticket_status",
        ),
        sa.CheckConstraint(
            "(status IN ('resolved', 'closed')) = (resolved_at IS NOT NULL)",
            name="ck_support_ticket_resolution",
        ),
    )
    op.create_index(
        "ix_support_ticket_owner_activity", "support_tickets", ["user_id", "last_activity_at", "id"]
    )
    op.create_index(
        "ix_support_ticket_status_activity", "support_tickets", ["status", "last_activity_at", "id"]
    )
    op.create_table(
        "support_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("support_tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("sender_role", sa.String(16), nullable=False),
        sa.Column("body", sa.String(4000), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("sender_id", "request_id", name="uq_support_message_request"),
        sa.CheckConstraint(
            "char_length(btrim(body)) BETWEEN 1 AND 4000", name="ck_support_message_body"
        ),
        sa.CheckConstraint(
            "sender_role IN ('member', 'admin')", name="ck_support_message_sender_role"
        ),
    )
    op.create_index(
        "ix_support_message_ticket_created", "support_messages", ["ticket_id", "created_at", "id"]
    )
    op.create_table(
        "support_message_reads",
        sa.Column(
            "message_id",
            sa.Uuid(),
            sa.ForeignKey("support_messages.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    op.create_table(
        "support_status_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("support_tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("actor_id", "request_id", name="uq_support_status_request"),
    )
    op.create_index(
        "ix_support_status_ticket_created", "support_status_events", ["ticket_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("support_message_reads")
    op.drop_table("support_status_events")
    op.drop_table("support_messages")
    op.drop_table("support_tickets")
