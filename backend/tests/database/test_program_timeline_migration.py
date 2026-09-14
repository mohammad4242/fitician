from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.nutrition.enums import NutritionPlanLifecycleStatus
from app.workout_cycles.models import WorkoutCycle
from app.workouts.enums import WorkoutPlanStatus
from app.workouts.models import WorkoutPlan
from tests.nutrition.test_bundle_selection import _seed_test_bundle


def test_program_timeline_schema_has_required_columns_and_constraints(db: Session) -> None:
    inspector = inspect(db.get_bind())

    profile_columns = {column["name"]: column for column in inspector.get_columns("user_profiles")}
    assert profile_columns["timezone"]["nullable"] is False
    assert profile_columns["timezone"]["default"] in {
        "'Asia/Tehran'::character varying",
        "'Asia/Tehran'",
    }

    nutrition_columns = {
        column["name"]: column for column in inspector.get_columns("nutrition_weekly_plans")
    }
    assert nutrition_columns["started_at"]["nullable"] is True

    cycle_columns = {column["name"]: column for column in inspector.get_columns("workout_cycles")}
    assert cycle_columns["start_date"]["nullable"] is False
    assert cycle_columns["start_timezone"]["nullable"] is True
    assert "ix_nutrition_weekly_plans_user_active_start" in {
        index["name"] for index in inspector.get_indexes("nutrition_weekly_plans")
    }

    session_columns = {column["name"] for column in inspector.get_columns("workout_cycle_sessions")}
    assert session_columns == {
        "id",
        "cycle_id",
        "workout_day_id",
        "week_number",
        "session_number",
        "scheduled_date",
        "status",
        "completed_at",
        "skipped_at",
        "created_at",
        "updated_at",
    }
    check_names = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("workout_cycle_sessions")
    }
    assert {
        "ck_workout_cycle_sessions_week_number_positive",
        "ck_workout_cycle_sessions_session_number_positive",
        "ck_workout_cycle_sessions_status_values",
        "ck_workout_cycle_sessions_timestamp_integrity",
    }.issubset(check_names)
    assert {index["name"] for index in inspector.get_indexes("workout_cycle_sessions")} >= {
        "ix_workout_cycle_sessions_cycle_id",
        "ix_workout_cycle_sessions_scheduled_date",
    }


def test_migration_does_not_fabricate_sessions_for_legacy_cycles(db: Session) -> None:
    user = User(email="legacy-cycle-migration@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    plan = WorkoutPlan(
        user_id=user.id,
        status=WorkoutPlanStatus.ACTIVE,
        generation_signature="a" * 64,
        profile_snapshot={},
        provider="test",
        model_id="test",
        prompt_version="test",
        generation_policy_version="test",
        candidate_set_hash="b" * 64,
        generation_method="test",
    )
    db.add(plan)
    db.flush()
    cycle = WorkoutCycle(user_id=user.id, workout_plan_id=plan.id, duration_weeks=4)
    db.add(cycle)
    db.flush()

    session_count = db.scalar(
        text("SELECT count(*) FROM workout_cycle_sessions WHERE cycle_id = :cycle_id"),
        {"cycle_id": cycle.id},
    )

    assert session_count == 0


def test_previous_nutrition_handoff_downgrade_preserves_effective_plan(
    client: TestClient, db: Session
) -> None:
    _, bundle, current_plan, future_plan = _seed_test_bundle(client, db)
    current_plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    current_plan.start_date = date(2026, 9, 1)
    future_plan.lifecycle_status = NutritionPlanLifecycleStatus.ACTIVE
    future_plan.start_date = date(2026, 9, 20)
    bundle.selected_plan_id = future_plan.id
    db.flush()

    path = (
        Path(__file__).parents[2]
        / "alembic/versions/20260914_152_allow_scheduled_nutrition_handoffs.py"
    )
    spec = spec_from_file_location("nutrition_handoff_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    migration.op = Operations(MigrationContext.configure(db.connection()))

    migration.downgrade()

    active_plans = db.scalars(
        text(
            "SELECT id FROM nutrition_weekly_plans "
            "WHERE user_id = :user_id AND lifecycle_status = 'active'"
        ),
        {"user_id": current_plan.user_id},
    ).all()
    assert active_plans == [current_plan.id]
    assert (
        db.scalar(
            text("SELECT lifecycle_status FROM nutrition_weekly_plans WHERE id = :id"),
            {"id": future_plan.id},
        )
        == "archived"
    )

    migration.op = Operations(MigrationContext.configure(db.connection()))
    migration.upgrade()
