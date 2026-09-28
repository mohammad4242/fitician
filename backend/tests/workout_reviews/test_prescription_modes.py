from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai.schemas import WorkoutPlanExerciseOutput
from app.exercises.enums import (
    Difficulty,
    ExerciseType,
    MovementPattern,
    MuscleGroup,
    PrescriptionMode,
)
from app.workout_reviews.schemas import (
    WorkoutReviewDayDraft,
    WorkoutReviewDraftUpdate,
    WorkoutReviewExerciseDraft,
)
from app.workout_reviews.validation import WorkoutReviewDraftValidator
from app.workouts.models import WorkoutDay, WorkoutPlan, WorkoutPlanExercise
from app.workouts.schemas import CandidateSet, WorkoutExerciseCandidate
from app.workouts.time_budget import WorkoutGenerationPolicy
from app.workouts.validator import WorkoutPlanValidationError, WorkoutPlanValidator


def test_coach_review_preserves_duration_contract() -> None:
    draft = WorkoutReviewExerciseDraft(
        order_index=1,
        exercise_id=uuid4(),
        sets=2,
        prescription_mode=PrescriptionMode.DURATION,
        reps_min=None,
        reps_max=None,
        duration_min_seconds=20,
        duration_max_seconds=40,
        rir=None,
        rest_seconds=60,
    )

    output = WorkoutPlanExerciseOutput(
        exercise_id=draft.exercise_id,
        sets=draft.sets,
        prescription_mode=draft.prescription_mode,
        reps_min=draft.reps_min,
        reps_max=draft.reps_max,
        duration_min_seconds=draft.duration_min_seconds,
        duration_max_seconds=draft.duration_max_seconds,
        rest_seconds=draft.rest_seconds,
        rir=draft.rir,
        estimated_minutes=4,
        notes_en=None,
        notes_fa=None,
    )

    assert output.prescription_mode is PrescriptionMode.DURATION
    assert output.rir is None


def test_coach_review_rejects_duration_rir() -> None:
    with pytest.raises(ValidationError, match="null RIR"):
        WorkoutReviewExerciseDraft(
            order_index=1,
            exercise_id=uuid4(),
            sets=2,
            prescription_mode=PrescriptionMode.DURATION,
            reps_min=None,
            reps_max=None,
            duration_min_seconds=20,
            duration_max_seconds=40,
            rir=2,
            rest_seconds=60,
        )


def test_coach_review_does_not_restore_source_rir_for_duration() -> None:
    exercise_id = uuid4()
    source_day = WorkoutDay(
        day_number=1,
        title_en="Day 1",
        title_fa="روز ۱",
        estimated_duration_minutes=20,
    )
    source_item = WorkoutPlanExercise(
        exercise_id=exercise_id,
        order_index=1,
        sets=2,
        reps_min=8,
        reps_max=12,
        rest_seconds=60,
        rir=2,
        estimated_minutes=4,
    )
    payload = WorkoutReviewDraftUpdate(
        expected_revision=1,
        days=[
            WorkoutReviewDayDraft(
                day_number=1,
                exercises=[
                    WorkoutReviewExerciseDraft(
                        order_index=1,
                        exercise_id=exercise_id,
                        sets=2,
                        prescription_mode=PrescriptionMode.DURATION,
                        duration_min_seconds=20,
                        duration_max_seconds=40,
                        rir=None,
                        rest_seconds=60,
                    )
                ],
            )
        ],
    )

    model = WorkoutReviewDraftValidator._to_model(
        WorkoutPlan(days=[source_day]),
        payload,
        {(1, 1): (source_day, source_item)},
    )

    assert model.days[0].exercises[0].rir is None


def test_coach_review_estimates_timed_sets_from_prescribed_duration() -> None:
    exercise_id = uuid4()
    day = WorkoutDay(
        day_number=1,
        title_en="Day 1",
        title_fa="روز ۱",
        estimated_duration_minutes=20,
    )
    payload = WorkoutReviewDraftUpdate(
        expected_revision=1,
        days=[
            WorkoutReviewDayDraft(
                day_number=1,
                exercises=[
                    WorkoutReviewExerciseDraft(
                        order_index=1,
                        exercise_id=exercise_id,
                        sets=3,
                        prescription_mode=PrescriptionMode.DURATION,
                        duration_min_seconds=240,
                        duration_max_seconds=300,
                        rir=None,
                        rest_seconds=60,
                    )
                ],
            )
        ],
    )

    model = WorkoutReviewDraftValidator._to_model(
        WorkoutPlan(days=[day]),
        payload,
        {},
    )

    assert model.days[0].exercises[0].estimated_minutes == 19
    assert model.days[0].estimated_duration_minutes == 24


def test_workout_validator_rejects_timed_session_over_duration_limit() -> None:
    exercise_id = uuid4()
    day = WorkoutDay(
        day_number=1,
        title_en="Day 1",
        title_fa="روز ۱",
        estimated_duration_minutes=20,
    )
    payload = WorkoutReviewDraftUpdate(
        expected_revision=1,
        days=[
            WorkoutReviewDayDraft(
                day_number=1,
                exercises=[
                    WorkoutReviewExerciseDraft(
                        order_index=1,
                        exercise_id=exercise_id,
                        sets=3,
                        prescription_mode=PrescriptionMode.DURATION,
                        duration_min_seconds=3600,
                        duration_max_seconds=3600,
                        rir=None,
                        rest_seconds=60,
                    )
                ],
            )
        ],
    )
    model = WorkoutReviewDraftValidator._to_model(WorkoutPlan(days=[day]), payload, {})
    candidate = WorkoutExerciseCandidate(
        id=exercise_id,
        primary_muscle=MuscleGroup.CHEST,
        secondary_muscles=(),
        movement_pattern=MovementPattern.HORIZONTAL_PUSH,
        exercise_type=ExerciseType.COMPOUND,
        equipment=(),
        difficulty=Difficulty.BEGINNER,
        caution_tags=(),
        prescription_mode=PrescriptionMode.DURATION,
        duration_min_seconds=3600,
        duration_max_seconds=3600,
    )
    validator = WorkoutPlanValidator(
        candidates=CandidateSet(
            exercises=(candidate,),
            candidate_set_hash="timed-duration-test",
            soft_cautions=(),
            minimum_candidate_count=1,
        ),
        policy=WorkoutGenerationPolicy.for_session_duration(45),
        required_day_count=1,
    )

    with pytest.raises(WorkoutPlanValidationError) as error:
        validator.validate(model)

    assert any(problem.code == "duration_exceeded" for problem in error.value.problems)
