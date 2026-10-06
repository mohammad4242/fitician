"""Explicit public exercise approval, preserving only already published seed pages."""

import sqlalchemy as sa

from alembic import op

revision = "20261006_170"
down_revision = "20261002_169"
branch_labels = None
depends_on = None

PUBLISHED_SLUGS = (
    "dumbbell-bench-press",
    "barbell-bent-over-row",
    "dumbbell-lateral-raise",
    "smith-machine-shoulder-press",
    "rear-delt-fly",
    "dumbbell-curl",
    "hammer-curl",
    "cable-curl",
    "barbell-curl",
    "overhead-dumbbell-extension",
    "glute-bridge",
    "goblet-squat",
    "leg-press",
    "leg-extension",
    "dumbbell-lunge",
    "romanian-deadlift",
    "standing-calf-raise",
    "plank",
)


def upgrade() -> None:
    op.add_column(
        "exercises", sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    exercises = sa.table("exercises", sa.column("slug"), sa.column("is_public"))
    op.execute(
        exercises.update().where(exercises.c.slug.in_(PUBLISHED_SLUGS)).values(is_public=True)
    )


def downgrade() -> None:
    op.drop_column("exercises", "is_public")
