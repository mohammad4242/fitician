"""Resume bounded native SDK discovery without changing local issue authority."""

import sqlalchemy as sa

from alembic import op

revision = "20261121_186"
down_revision = "20261114_185"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "diagnostic_discovery_cursors",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("organization", sa.String(100), nullable=False),
        sa.Column("project_id", sa.String(100), nullable=False),
        sa.Column("environment", sa.String(64), nullable=False),
        sa.Column("watermark", sa.DateTime(timezone=True)),
        sa.Column("scan_start", sa.DateTime(timezone=True)),
        sa.Column("scan_end", sa.DateTime(timezone=True)),
        sa.Column("cursor", sa.String(256)),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "organization", "project_id", "environment", name="uq_diagnostic_discovery_scope"
        ),
    )


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM diagnostic_discovery_cursors) "
        "THEN RAISE EXCEPTION 'Retain native discovery progress; use application rollback'; "
        "END IF; END $$"
    )
    op.drop_table("diagnostic_discovery_cursors")
