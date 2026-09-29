"""Program conversations, notification inbox and opt-in personal reminders."""

import sqlalchemy as sa

from alembic import op

revision = "20260929_163"
down_revision = "20260928_162"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, default in [
        ("messages", "true"),
        ("training_reminders", "false"),
        ("nutrition_reminders", "false"),
        ("return_reminders", "false"),
    ]:
        op.add_column(
            "notification_preferences",
            sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.text(default)),
        )
    for name, length in [("training_time", 5), ("nutrition_time", 5), ("reminder_timezone", 64)]:
        op.add_column("notification_preferences", sa.Column(name, sa.String(length)))
    op.create_table(
        "program_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workout_review_id",
            sa.Uuid(),
            sa.ForeignKey("workout_plan_reviews.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "nutrition_review_id",
            sa.Uuid(),
            sa.ForeignKey("nutrition_plan_physician_reviews.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "sender_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.String(2000), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("sender_id", "request_id", name="uq_program_message_request"),
        sa.CheckConstraint(
            "(workout_review_id IS NULL) <> (nutrition_review_id IS NULL)",
            name="ck_program_message_reference",
        ),
        sa.CheckConstraint(
            "char_length(btrim(body)) BETWEEN 1 AND 2000", name="ck_program_message_body"
        ),
    )
    for field in ["workout_review_id", "nutrition_review_id"]:
        op.create_index(f"ix_program_messages_{field}", "program_messages", [field])
    op.create_table(
        "program_message_reads",
        sa.Column(
            "message_id",
            sa.Uuid(),
            sa.ForeignKey("program_messages.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    op.create_table(
        "notification_inbox_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("deduplication_key", sa.String(200), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "deduplication_key", name="uq_notification_inbox_dedup"),
    )
    op.create_index(
        "ix_notification_inbox_user_created", "notification_inbox_items", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("notification_inbox_items")
    op.drop_table("program_message_reads")
    op.drop_table("program_messages")
    for name in [
        "messages",
        "training_reminders",
        "nutrition_reminders",
        "return_reminders",
        "training_time",
        "nutrition_time",
        "reminder_timezone",
    ]:
        op.drop_column("notification_preferences", name)
