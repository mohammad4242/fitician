from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from uuid import UUID

from app.exercises.enums import ExerciseType, MovementPattern, MuscleGroup, PrescriptionMode
from app.exercises.models import Exercise
from app.workouts.models import WorkoutDay, WorkoutPlan, WorkoutPlanExercise
from app.workouts.program_engine.effective_volume import (
    calculate_effective_volume,
    complete_tracked_metrics,
)
from app.workouts.program_engine.rulesets.resistance_training_v1 import (
    RULESET,
    ProgramRuleset,
)
from app.workouts.program_engine.schemas import ProgrammedExercise
from app.workouts.program_engine.volume_policy import weekly_volume_constraint_value


@dataclass(frozen=True)
class ExerciseMetricMetadata:
    name: str
    primary_muscle: MuscleGroup | None
    secondary_muscles: tuple[MuscleGroup, ...]
    movement_pattern: MovementPattern
    exercise_type: ExerciseType


def metadata_from_exercise(exercise: Exercise) -> ExerciseMetricMetadata:
    return ExerciseMetricMetadata(
        name=exercise.name_en,
        primary_muscle=exercise.primary_muscle,
        secondary_muscles=tuple(item.muscle for item in exercise.secondary_muscles),
        movement_pattern=exercise.movement_pattern,
        exercise_type=exercise.exercise_type,
    )


def metrics_for_reviewed_plan(plan: WorkoutPlan) -> dict[str, object] | None:
    if plan.generation_method != "coach_review" or not plan.days:
        return None

    metadata_by_id: dict[UUID, ExerciseMetricMetadata] = {}
    for day in plan.days:
        for item in day.exercises:
            metadata = _metadata_from_snapshot(item.exercise_snapshot)
            if metadata is None and item.exercise is not None:
                metadata = metadata_from_exercise(item.exercise)
            if metadata is None:
                return None
            metadata_by_id[item.exercise_id] = metadata

    return refreshed_prescription_metrics(
        plan.days,
        metadata_by_id,
        plan.aggregate_metrics,
        training_age_months=_training_age_months(plan.profile_snapshot),
    )


def refreshed_prescription_metrics(
    days: Sequence[WorkoutDay],
    metadata_by_id: Mapping[UUID, ExerciseMetricMetadata],
    prior_metrics: Mapping[str, object],
    *,
    training_age_months: int,
    ruleset: ProgramRuleset = RULESET,
) -> dict[str, object]:
    programmed: list[ProgrammedExercise] = []
    direct_session_frequency: Counter[str] = Counter()
    session_indexes: defaultdict[str, list[int]] = defaultdict(list)
    patterns: Counter[str] = Counter()

    for day in days:
        day_primary_muscles: set[str] = set()
        for item in day.exercises:
            metadata = metadata_by_id.get(item.exercise_id)
            if metadata is None:
                raise ValueError("Workout metric metadata is missing for a planned exercise")
            programmed.append(_programmed_exercise(item, metadata))
            patterns[metadata.movement_pattern.value] += 1
            if metadata.primary_muscle is not None:
                day_primary_muscles.add(metadata.primary_muscle.value)
        for muscle in day_primary_muscles:
            direct_session_frequency[muscle] += 1
            session_indexes[muscle].append(day.day_number)

    volume = calculate_effective_volume(programmed, ruleset)
    metrics: dict[str, object] = {
        "weekly_direct_sets_by_muscle": _complete_metrics(volume.direct_sets_by_muscle),
        "weekly_fractional_sets_by_muscle": complete_tracked_metrics(
            _metric_values(volume.secondary_sets_by_muscle)
        ),
        "weekly_effective_sets_by_muscle": complete_tracked_metrics(
            _metric_values(volume.effective_sets_by_muscle)
        ),
        "direct_session_frequency_by_muscle": complete_tracked_metrics(
            _metric_values(direct_session_frequency)
        ),
        "movement_pattern_frequency": dict(patterns),
        "estimated_weekly_duration": sum(day.estimated_duration_minutes for day in days),
        "weekly_cardio_minutes": sum(_cardio_duration(day) for day in days),
        "hard_training_days": len(days),
        "recovery_days": max(0, ruleset.days_per_week - len(days)),
    }

    prior_ranges = prior_metrics.get("volume_ranges_by_muscle")
    if isinstance(prior_ranges, dict):
        metrics["volume_ranges_by_muscle"] = _refresh_volume_ranges(
            prior_ranges,
            volume.direct_sets_by_muscle,
            volume.effective_sets_by_muscle,
            training_age_months,
        )

    prior_priorities = prior_metrics.get("priority_metrics")
    if isinstance(prior_priorities, dict):
        metrics["priority_metrics"] = _refresh_priority_metrics(
            prior_priorities,
            volume.direct_sets_by_muscle,
            volume.effective_sets_by_muscle,
            session_indexes,
        )
    return metrics


def _programmed_exercise(
    item: WorkoutPlanExercise,
    metadata: ExerciseMetricMetadata,
) -> ProgrammedExercise:
    mode = item.prescription_mode
    rep_min: int | None
    rep_max: int | None
    target_rir: int | None
    duration_min: int | None
    duration_max: int | None
    if mode is PrescriptionMode.DURATION:
        duration_min = item.duration_min_seconds or 1
        duration_max = max(duration_min, item.duration_max_seconds or duration_min)
        rep_min = rep_max = target_rir = None
    else:
        rep_min = item.reps_min or 1
        rep_max = max(rep_min, item.reps_max or rep_min)
        target_rir = item.rir if item.rir is not None else 0
        duration_min = duration_max = None
    return ProgrammedExercise(
        exercise_id=item.exercise_id,
        exercise_name=metadata.name,
        order=item.order_index,
        sets=item.sets,
        rep_min=rep_min,
        rep_max=rep_max,
        target_rir=target_rir,
        rest_seconds=item.rest_seconds,
        estimated_minutes=item.estimated_minutes,
        reason_codes=tuple(item.reason_codes or ()),
        movement_pattern=metadata.movement_pattern,
        primary_muscle=metadata.primary_muscle,
        secondary_muscles=metadata.secondary_muscles,
        prescription_mode=mode,
        exercise_type=metadata.exercise_type,
        duration_min_seconds=duration_min,
        duration_max_seconds=duration_max,
    )


def _refresh_volume_ranges(
    values: dict[str, object],
    direct_sets: Mapping[str, int],
    effective_sets: Mapping[str, float],
    training_age_months: int,
) -> dict[str, object]:
    refreshed: dict[str, object] = {}
    for muscle_key, raw_metric in values.items():
        if not isinstance(raw_metric, dict):
            continue
        metric = deepcopy(raw_metric)
        try:
            muscle = MuscleGroup(str(muscle_key))
        except ValueError:
            refreshed[str(muscle_key)] = metric
            continue
        direct = direct_sets.get(muscle.value, 0)
        effective = effective_sets.get(muscle.value, 0.0)
        actual = weekly_volume_constraint_value(
            muscle,
            training_age_months,
            direct_sets=direct,
            effective_sets=effective,
        )
        minimum = _number(metric.get("acceptable_minimum"))
        maximum = _number(metric.get("acceptable_maximum"))
        preferred = _number(metric.get("preferred_weekly_target"))
        reasons = _string_values(metric.get("constraint_reason_codes"))
        inside_range = minimum is not None and maximum is not None and minimum <= actual <= maximum
        if preferred is not None and actual == preferred:
            status = "exact_target"
        elif inside_range:
            status = "within_flexible_range"
        elif reasons:
            status = "constrained"
        else:
            status = "outside_acceptable_range"
        metric.update(
            {
                "actual_direct_volume": direct,
                "actual_effective_volume": effective,
                "actual_constraint_volume": actual,
                "status": status,
            }
        )
        refreshed[muscle.value] = metric
    return refreshed


def _refresh_priority_metrics(
    values: dict[str, object],
    direct_sets: Mapping[str, int],
    effective_sets: Mapping[str, float],
    session_indexes: Mapping[str, list[int]],
) -> dict[str, object]:
    refreshed: dict[str, object] = {}
    for muscle_key, raw_metric in values.items():
        if not isinstance(raw_metric, dict):
            continue
        metric = deepcopy(raw_metric)
        direct = direct_sets.get(str(muscle_key), 0)
        effective = effective_sets.get(str(muscle_key), 0.0)
        indexes = tuple(session_indexes.get(str(muscle_key), ()))
        target = _number(metric.get("target_sets"))
        effective_target = _number(metric.get("effective_target_sets"))
        preferred_frequency = _number(metric.get("preferred_frequency"))
        target_available = (target is not None and target > 0) or (
            effective_target is not None and effective_target > 0
        )
        direct_satisfied = target_available and target is not None and direct >= target
        effective_satisfied = (
            target_available and effective_target is not None and effective >= effective_target
        )
        frequency_satisfied = (
            preferred_frequency is not None and len(indexes) >= preferred_frequency
        )
        reasons: list[str] = []
        reasons.append(
            "PRIORITY_VOLUME_INCREASED"
            if direct_satisfied and effective_satisfied
            else "PRIORITY_TARGET_PARTIALLY_SATISFIED"
        )
        reasons.append(
            "PRIORITY_FREQUENCY_INCREASED"
            if frequency_satisfied and preferred_frequency is not None and preferred_frequency > 1
            else "PRIORITY_TARGET_CONSTRAINED"
        )
        metric.update(
            {
                "direct_sets": direct,
                "effective_sets": effective,
                "session_frequency": len(indexes),
                "session_indexes": indexes,
                "distributed": frequency_satisfied,
                "status": (
                    "satisfied"
                    if direct_satisfied and effective_satisfied and frequency_satisfied
                    else "partial"
                ),
                "reason_codes": tuple(dict.fromkeys(reasons)),
            }
        )
        refreshed[str(muscle_key)] = metric
    return refreshed


def _metadata_from_snapshot(value: object) -> ExerciseMetricMetadata | None:
    if not isinstance(value, dict) or not {
        "primary_muscle",
        "secondary_muscles",
        "movement_pattern",
        "exercise_type",
    }.issubset(value):
        return None
    raw_name = value.get("name_en")
    raw_primary = value.get("primary_muscle")
    raw_secondaries = value.get("secondary_muscles")
    primary = _muscle_group(raw_primary)
    if raw_primary is not None and primary is None:
        return None
    if not isinstance(raw_secondaries, list):
        return None
    parsed_secondaries = tuple(_muscle_group(raw) for raw in raw_secondaries)
    if any(muscle is None for muscle in parsed_secondaries):
        return None
    secondary = tuple(muscle for muscle in parsed_secondaries if muscle is not None)
    pattern = _movement_pattern(value.get("movement_pattern"))
    exercise_type = _exercise_type(value.get("exercise_type"))
    if pattern is None or exercise_type is None:
        return None
    return ExerciseMetricMetadata(
        name=raw_name if isinstance(raw_name, str) else "Reviewed exercise",
        primary_muscle=primary,
        secondary_muscles=secondary,
        movement_pattern=pattern,
        exercise_type=exercise_type,
    )


def _muscle_group(value: object) -> MuscleGroup | None:
    if value is None:
        return None
    try:
        return value if isinstance(value, MuscleGroup) else MuscleGroup(str(value))
    except ValueError:
        return None


def _movement_pattern(value: object) -> MovementPattern | None:
    try:
        return value if isinstance(value, MovementPattern) else MovementPattern(str(value))
    except ValueError:
        return None


def _exercise_type(value: object) -> ExerciseType | None:
    try:
        return value if isinstance(value, ExerciseType) else ExerciseType(str(value))
    except ValueError:
        return None


def _training_age_months(value: object) -> int:
    if not isinstance(value, dict):
        return 0
    raw = value.get("training_age_months")
    return raw if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0 else 0


def _cardio_duration(day: WorkoutDay) -> int:
    cardio = day.cardio
    if not isinstance(cardio, dict):
        return 0
    duration = cardio.get("duration_minutes")
    return duration if isinstance(duration, int) and not isinstance(duration, bool) else 0


def _metric_values(values: Mapping[str, int | float]) -> dict[str, int | float]:
    return {key: value for key, value in values.items()}


def _complete_metrics(values: Mapping[str, int | float]) -> dict[str, int | float]:
    return complete_tracked_metrics(_metric_values(values))


def _number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _string_values(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str))
