"""create access campaigns, redemptions, and admin audit events"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_145"
down_revision: str | Sequence[str] | None = "20260913_144"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "access_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("package_code", sa.String(length=64), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("term_weeks", sa.SmallInteger(), nullable=True),
        sa.Column("available_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_total_redemptions", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "char_length(btrim(code)) BETWEEN 1 AND 128",
            name="ck_access_campaigns_code_length",
        ),
        sa.CheckConstraint(
            "kind IN ('signup_trial', 'manual_promotion')",
            name="ck_access_campaigns_kind_values",
        ),
        sa.CheckConstraint(
            "package_code <> 'free'",
            name="ck_access_campaigns_package_not_free",
        ),
        sa.CheckConstraint(
            "duration_days BETWEEN 1 AND 3650",
            name="ck_access_campaigns_duration_days",
        ),
        sa.CheckConstraint(
            "term_weeks IS NULL OR term_weeks IN (4, 6, 8)",
            name="ck_access_campaigns_term_weeks_values",
        ),
        sa.CheckConstraint(
            "package_code <> 'launch_trial' OR term_weeks = 4",
            name="ck_access_campaigns_launch_trial_term",
        ),
        sa.CheckConstraint(
            "available_until IS NULL OR available_from IS NULL "
            "OR available_until >= available_from",
            name="ck_access_campaigns_availability_order",
        ),
        sa.CheckConstraint(
            "max_total_redemptions IS NULL OR max_total_redemptions > 0",
            name="ck_access_campaigns_max_redemptions_positive",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_access_campaigns_code"),
    )
    op.create_index(
        "ix_access_campaigns_kind_active_window",
        "access_campaigns",
        ["kind", "is_active", "available_from", "available_until"],
    )

    op.create_table(
        "access_campaign_redemptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("access_grant_id", sa.Uuid(), nullable=True),
        sa.Column("package_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("duration_days_snapshot", sa.Integer(), nullable=False),
        sa.Column("term_weeks_snapshot", sa.SmallInteger(), nullable=True),
        sa.Column(
            "redeemed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "duration_days_snapshot BETWEEN 1 AND 3650",
            name="ck_access_campaign_redemptions_duration_days",
        ),
        sa.CheckConstraint(
            "term_weeks_snapshot IS NULL OR term_weeks_snapshot IN (4, 6, 8)",
            name="ck_access_campaign_redemptions_term_weeks_values",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["access_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["access_grant_id"], ["user_access_grants.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "user_id", name="uq_access_campaign_redemptions_campaign_user"
        ),
    )
    op.create_index(
        "ix_access_campaign_redemptions_campaign_id",
        "access_campaign_redemptions",
        ["campaign_id"],
    )
    op.create_index(
        "ix_access_campaign_redemptions_user_id",
        "access_campaign_redemptions",
        ["user_id"],
    )

    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_key", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_events_created_at", "admin_audit_events", ["created_at"])
    op.create_index(
        "ix_admin_audit_events_actor_created_at",
        "admin_audit_events",
        ["actor_user_id", "created_at"],
    )
    op.create_index(
        "ix_admin_audit_events_target_created_at",
        "admin_audit_events",
        ["target_user_id", "created_at"],
    )
    op.create_index(
        "ix_admin_audit_events_resource",
        "admin_audit_events",
        ["resource_type", "resource_key"],
    )

    op.execute(
        sa.text(
            "INSERT INTO access_campaigns "
            "(id, code, name, kind, package_code, duration_days, term_weeks, is_active) "
            "VALUES (gen_random_uuid(), :code, :name, :kind, :package_code, "
            ":duration_days, :term_weeks, :is_active)"
        ).bindparams(
            code="launch_trial_v1",
            name="Fitition Launch Trial",
            kind="signup_trial",
            package_code="launch_trial",
            duration_days=30,
            term_weeks=4,
            is_active=True,
        )
    )


def downgrade() -> None:
    op.drop_index("ix_admin_audit_events_resource", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_target_created_at", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_actor_created_at", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_created_at", table_name="admin_audit_events")
    op.drop_table("admin_audit_events")
    op.drop_index(
        "ix_access_campaign_redemptions_user_id",
        table_name="access_campaign_redemptions",
    )
    op.drop_index(
        "ix_access_campaign_redemptions_campaign_id",
        table_name="access_campaign_redemptions",
    )
    op.drop_table("access_campaign_redemptions")
    op.drop_index("ix_access_campaigns_kind_active_window", table_name="access_campaigns")
    op.drop_table("access_campaigns")
