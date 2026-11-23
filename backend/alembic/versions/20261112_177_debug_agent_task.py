"""Add debug_agent to the persisted AI task catalog without selecting a model."""

from alembic import op

revision = "20261112_177"
down_revision = "20261112_176"
branch_labels = None
depends_on = None

_TASKS = (
    "workout_plan_generation",
    "body_photo_analysis",
    "progress_comparison",
    "food_photo_estimation",
    "food_price_search",
)


def _constraint(tasks: tuple[str, ...]) -> None:
    op.drop_constraint("ck_ai_task_configs_task_type_values", "ai_task_configs", type_="check")
    values = ", ".join(repr(task) for task in tasks)
    op.create_check_constraint(
        "ck_ai_task_configs_task_type_values", "ai_task_configs", f"task_type IN ({values})"
    )


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    _constraint((*_TASKS, "debug_agent"))


def downgrade() -> None:
    # Deliberately fail rather than silently deleting operator configuration/provenance.
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM ai_task_configs "
        "WHERE task_type = 'debug_agent') THEN RAISE EXCEPTION "
        "'Retain debug_agent configuration; use application rollback'; END IF; END $$"
    )
    _constraint(_TASKS)
