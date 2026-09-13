"""curate back exercise safety notes"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.exercises.curated_safety_notes import CURATED_BACK_SAFETY_NOTES

revision: str = "20260913_143"
down_revision: str | Sequence[str] | None = "20260913_142"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    exercises = sa.table(
        "exercises",
        sa.column("slug", sa.String(length=120)),
        sa.column("is_active", sa.Boolean()),
        sa.column("primary_muscle", sa.String(length=14)),
        sa.column("exercise_type", sa.String(length=20)),
        sa.column("safety_notes_fa", sa.JSON()),
        sa.column("safety_notes_en", sa.JSON()),
    )
    connection = op.get_bind()
    for slug, notes in CURATED_BACK_SAFETY_NOTES.items():
        connection.execute(
            exercises.update()
            .where(
                exercises.c.slug == slug,
                exercises.c.is_active.is_(True),
                exercises.c.primary_muscle == "back",
                exercises.c.exercise_type != "mobility",
            )
            .values(
                safety_notes_fa=list(notes.fa),
                safety_notes_en=list(notes.en),
            )
        )


def downgrade() -> None:
    # This content backfill has no safe historical value to restore.
    pass
