"""default new member profiles to the Tehran timezone"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260914_153"
down_revision: str | Sequence[str] | None = "20260914_152"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "user_profiles",
        "timezone",
        existing_type=sa.String(length=64),
        server_default="Asia/Tehran",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "user_profiles",
        "timezone",
        existing_type=sa.String(length=64),
        server_default="UTC",
        existing_nullable=False,
    )
