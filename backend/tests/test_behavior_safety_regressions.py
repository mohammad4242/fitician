from types import SimpleNamespace

import pytest

from app.athlete_state.generation_adapter import AthleteStateToGenerationOverridesAdapter
from app.athlete_state.service import AthleteStateBuilder
from app.exercises.enums import ExerciseType, MovementPattern, MuscleGroup
from app.nutrition.enums import SafetyOutcome
from app.workout_cycles.enums import (
    WorkoutCycleWeeklyCheckInDifficulty,
    WorkoutCycleWeeklyCheckInRecovery,
)
from app.workout_cycles.models import (
    WorkoutCycleWeeklyCheckIn,
    WorkoutCycleWeeklyCheckInPainLimitation,
)
from app.workouts.prescription_metrics import ExerciseMetricMetadata, refreshed_prescription_metrics
from app.workouts.program_engine.adaptation_policy import decide_cycle_adaptation
from tests.nutrition.test_clinical_review_api import _member_plan
from tests.workout_cycles.test_replacement_api import _plan_with_cycle, _user


def test_weekly_pain_blocks_the_prescribed_exercise_in_adaptation(db):
    user = _user(db)
    plan, prescribed, cycle, original, _, _ = _plan_with_cycle(db, user.id)
    check_in = WorkoutCycleWeeklyCheckIn(
        user_id=user.id,
        cycle_id=cycle.id,
        week_number=1,
        sessions_completed=1,
        perceived_difficulty=WorkoutCycleWeeklyCheckInDifficulty.APPROPRIATE,
        recovery_rating=WorkoutCycleWeeklyCheckInRecovery.GOOD,
        has_pain_or_limitation=True,
    )
    check_in.pain_limitation = WorkoutCycleWeeklyCheckInPainLimitation(
        user_id=user.id,
        cycle_id=cycle.id,
        workout_plan_exercise_id=prescribed.id,
        note_optional="Shoulder pain during this exercise",
    )
    db.add(check_in)
    db.commit()
    state = AthleteStateBuilder(db).build(user.id, cycle_id=cycle.id)
    assert original.id in state.pain_sensitive_exercises
    assert original.id in decide_cycle_adaptation(state).safety_constraints.blocked_exercises
    assert (
        original.id
        in AthleteStateToGenerationOverridesAdapter.to_overrides(state).blocked_exercises
    )
    check_in.has_pain_or_limitation = False
    check_in.pain_limitation = None
    db.commit()
    assert (
        original.id
        not in AthleteStateBuilder(db).build(user.id, cycle_id=cycle.id).pain_sensitive_exercises
    )


@pytest.mark.parametrize("suffix", ["", "/pdf"])
def test_blocked_member_cannot_read_plan_directly_or_as_pdf(client, db, monkeypatch, suffix):
    plan = _member_plan(client, db)
    monkeypatch.setattr(
        "app.nutrition.plan_service.current_medical_safety_decision",
        lambda *_: SimpleNamespace(outcome=SafetyOutcome.UNSUPPORTED_OR_HARD_BLOCKED),
    )
    response = client.get(f"/api/v1/nutrition/plans/{plan['id']}{suffix}")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NUTRITION_PLAN_SAFETY_BLOCKED"


def test_removed_muscle_has_zero_volume_after_coach_edit(db):
    user = _user(db)
    plan, prescribed, _, original, _, _ = _plan_with_cycle(db, user.id)
    original.primary_muscle = MuscleGroup.CHEST
    metadata = ExerciseMetricMetadata(
        "Chest fly", MuscleGroup.CHEST, (), MovementPattern.HORIZONTAL_PUSH, ExerciseType.ISOLATION
    )
    result = refreshed_prescription_metrics(
        plan.days,
        {prescribed.exercise_id: metadata},
        {
            "weekly_direct_sets_by_muscle": {"triceps": 4},
            "weekly_effective_sets_by_muscle": {"triceps": 4},
            "weekly_fractional_sets_by_muscle": {"triceps": 2},
        },
        training_age_months=12,
    )
    for metric in (
        "weekly_direct_sets_by_muscle",
        "weekly_effective_sets_by_muscle",
        "weekly_fractional_sets_by_muscle",
    ):
        assert result[metric]["triceps"] == 0
