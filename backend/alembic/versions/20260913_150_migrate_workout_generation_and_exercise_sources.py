"""migrate workout generation method and exercise sources to fitician

Revision ID: 20260913_150
Revises: 20260913_149
Create Date: 2026-09-13
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260913_150"
down_revision: str | Sequence[str] | None = "20260913_149"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update user_profiles.workout_generation_method
    op.drop_constraint(
        "ck_user_profiles_workout_generation_method_values",
        "user_profiles",
        type_="check",
    )
    op.execute(
        "UPDATE user_profiles "
        "SET workout_generation_method = 'fitician_coach' "
        "WHERE workout_generation_method = 'fitsho_coach'"
    )
    op.create_check_constraint(
        "ck_user_profiles_workout_generation_method_values",
        "user_profiles",
        "workout_generation_method IN ('fitician_coach', 'ai')",
    )

    # 2. Update nutrition_structured_exercises.source
    op.drop_constraint(
        "ck_nutrition_structured_exercises_source_values",
        "nutrition_structured_exercises",
        type_="check",
    )
    op.execute(
        "UPDATE nutrition_structured_exercises "
        "SET source = 'active_fitician_plan' "
        "WHERE source = 'active_fitsho_plan'"
    )
    op.create_check_constraint(
        "ck_nutrition_structured_exercises_source_values",
        "nutrition_structured_exercises",
        "source IN ('user_reported', 'training_profile', 'active_fitician_plan')",
    )

    # 3. Update training_program_templates source names
    op.execute(
        "UPDATE training_program_templates "
        "SET source_name = 'Fitician canonical training template catalog' "
        "WHERE source_name = 'Fitsho canonical training template catalog'"
    )
    op.execute(
        "UPDATE training_program_templates "
        "SET source_name = 'Fitician fixed bodyweight templates' "
        "WHERE source_name = 'Fitsho fixed bodyweight templates'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE training_program_templates "
        "SET source_name = 'Fitsho fixed bodyweight templates' "
        "WHERE source_name = 'Fitician fixed bodyweight templates'"
    )
    op.execute(
        "UPDATE training_program_templates "
        "SET source_name = 'Fitsho canonical training template catalog' "
        "WHERE source_name = 'Fitician canonical training template catalog'"
    )

    op.drop_constraint(
        "ck_nutrition_structured_exercises_source_values",
        "nutrition_structured_exercises",
        type_="check",
    )
    op.execute(
        "UPDATE nutrition_structured_exercises "
        "SET source = 'active_fitsho_plan' "
        "WHERE source = 'active_fitician_plan'"
    )
    op.create_check_constraint(
        "ck_nutrition_structured_exercises_source_values",
        "nutrition_structured_exercises",
        "source IN ('user_reported', 'training_profile', 'active_fitsho_plan')",
    )

    op.drop_constraint(
        "ck_user_profiles_workout_generation_method_values",
        "user_profiles",
        type_="check",
    )
    op.execute(
        "UPDATE user_profiles "
        "SET workout_generation_method = 'fitsho_coach' "
        "WHERE workout_generation_method = 'fitician_coach'"
    )
    op.create_check_constraint(
        "ck_user_profiles_workout_generation_method_values",
        "user_profiles",
        "workout_generation_method IN ('fitsho_coach', 'ai')",
    )
