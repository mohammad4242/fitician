from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.exercises.enums import MuscleGroup
from app.exercises.models import ExerciseAlternative
from app.profile.enums import FitnessGoal, TrainingLocation
from app.profile.models import UserProfile
from app.profile.schemas import ProfileUpdate
from app.profile.service import apply_profile_update_without_commit
from app.time_context import (
    DEFAULT_MEMBER_TIMEZONE,
    fitician_weekday,
    local_date_for_timezone,
    local_midnight_utc,
    member_timezone_or_default,
    validate_timezone_name,
)
from app.workout_cycles.body_progress_schemas import (
    WorkoutCycleBodyProgressComparisonResponse,
    WorkoutCycleFeedbackBodyProgressContext,
)
from app.workout_cycles.enums import (
    WorkoutCycleExerciseFeedbackSuggestionKind,
    WorkoutCycleExerciseFeedbackType,
    WorkoutCycleSessionStatus,
    WorkoutCycleStatus,
    WorkoutCycleWeeklyCheckInDifficulty,
    WorkoutCycleWeeklyCheckInRecovery,
    WorkoutExercisePreferenceType,
    WorkoutExerciseReplacementReason,
    WorkoutExerciseReplacementScope,
    WorkoutExerciseSafetySignalType,
)
from app.workout_cycles.models import (
    WorkoutCycle,
    WorkoutCycleExerciseFeedback,
    WorkoutCycleFeedback,
    WorkoutCycleSession,
    WorkoutCycleWeeklyCheckIn,
    WorkoutCycleWeeklyCheckInPainLimitation,
    WorkoutExercisePreference,
    WorkoutExerciseReplacement,
    WorkoutExerciseSafetySignal,
)
from app.workout_cycles.schemas import (
    CompletionFeedbackInput,
    WorkoutCycleExerciseFeedbackPersistentStateResponse,
    WorkoutCycleExerciseFeedbackReplacementSummaryResponse,
    WorkoutCycleExerciseFeedbackSuggestionResponse,
)
from app.workouts.enums import WorkoutPlanStatus
from app.workouts.models import WorkoutDay, WorkoutPlan, WorkoutPlanExercise
from app.workouts.program_engine.enums import Goal
from app.workouts.repository import get_plan_for_user

SUPPORTED_CYCLE_DURATIONS = frozenset({4, 6, 8})


class WorkoutCycleNotFoundError(Exception):
    pass


class WorkoutCycleAlreadyStartedError(Exception):
    pass


class WorkoutCycleSessionNotFoundError(Exception):
    pass


class WorkoutCycleSessionAlreadyFinishedError(Exception):
    pass


class WorkoutCycleSessionDateConflictError(Exception):
    pass


class WorkoutCycleSessionBeforeStartError(ValueError):
    pass


class WorkoutCycleSessionNotActionableError(ValueError):
    pass


class WorkoutCycleAlreadyCompletedError(Exception):
    pass


class WorkoutCycleCompletionFeedbackNotDueError(Exception):
    pass


class WorkoutCycleCompletionFeedbackNotFoundError(Exception):
    pass


class WorkoutCyclePlanInactiveError(Exception):
    pass


class WorkoutExerciseReplacementNoActiveCycleError(Exception):
    pass


class WorkoutExerciseReplacementPlanExerciseNotFoundError(Exception):
    pass


class WorkoutExerciseReplacementSelfError(Exception):
    pass


class WorkoutExerciseReplacementAlternativeNotAllowedError(Exception):
    pass


class WorkoutCycleExerciseFeedbackPlanExerciseNotFoundError(Exception):
    pass


class WorkoutCycleExerciseFeedbackDuplicateError(Exception):
    pass


class WorkoutCycleExerciseFeedbackNotStartedError(Exception):
    pass


class WorkoutCycleWeeklyCheckInCycleNotFoundError(Exception):
    pass


class WorkoutCycleWeeklyCheckInNoActiveCycleError(Exception):
    pass


class WorkoutCycleWeeklyCheckInNotFoundError(Exception):
    pass


class WorkoutCycleWeeklyCheckInWeekOutOfRangeError(ValueError):
    pass


class WorkoutCycleWeeklyCheckInSessionsOutOfRangeError(ValueError):
    pass


class WorkoutCycleWeeklyCheckInPainExerciseRequiredError(ValueError):
    pass


class WorkoutCycleWeeklyCheckInPainExerciseNotFoundError(Exception):
    pass


class WorkoutCycleWeeklyCheckInPainFollowUpNotAllowedError(ValueError):
    pass


def calculate_current_week(
    started_at: datetime,
    duration_weeks: int,
    *,
    now: datetime | None = None,
) -> int:
    if duration_weeks < 1:
        raise ValueError("Workout cycle duration must be at least one week")

    current_at = datetime.now(UTC) if now is None else now
    started_at_utc = _as_utc(started_at)
    current_at_utc = _as_utc(current_at)
    elapsed_days = max(0, (current_at_utc - started_at_utc).days)
    return min(duration_weeks, elapsed_days // 7 + 1)


def workout_cycle_start_date(
    cycle: WorkoutCycle, *, timezone_name: str = DEFAULT_MEMBER_TIMEZONE
) -> date:
    """Return the immutable logical start, with a legacy in-memory fallback."""
    stored = getattr(cycle, "start_date", None)
    if isinstance(stored, date):
        return stored
    return local_date_for_timezone(timezone_name, now=cycle.started_at)


def get_actionable_workout_session(cycle: WorkoutCycle) -> WorkoutCycleSession | None:
    return min(
        (
            session
            for session in cycle.sessions
            if session.status is WorkoutCycleSessionStatus.SCHEDULED
        ),
        key=lambda session: session.session_number,
        default=None,
    )


def workout_cycle_timezone(db: Session, *, user_id: UUID, cycle: WorkoutCycle) -> str:
    profile_timezone = db.scalar(select(UserProfile.timezone).where(UserProfile.user_id == user_id))
    return member_timezone_or_default(profile_timezone, cycle.start_timezone)


def _cycle_local_date(
    db: Session,
    *,
    user_id: UUID,
    cycle: WorkoutCycle,
    now: datetime | None = None,
) -> date:
    return local_date_for_timezone(
        workout_cycle_timezone(db, user_id=user_id, cycle=cycle),
        now=_as_utc(now or datetime.now(UTC)),
    )


def _ensure_actionable_session(
    db: Session,
    *,
    user_id: UUID,
    session: WorkoutCycleSession,
    now: datetime | None,
    require_due: bool,
) -> None:
    actionable = get_actionable_workout_session(session.cycle)
    local_date = _cycle_local_date(db, user_id=user_id, cycle=session.cycle, now=now)
    if (
        actionable is None
        or actionable.id != session.id
        or local_date < workout_cycle_start_date(session.cycle)
        or (require_due and session.scheduled_date > local_date)
    ):
        raise WorkoutCycleSessionNotActionableError("Workout cycle session is not actionable")


def cycle_has_reached_nominal_end(
    cycle: WorkoutCycle,
    *,
    now: datetime | None = None,
    timezone_name: str = DEFAULT_MEMBER_TIMEZONE,
) -> bool:
    current_at = _as_utc(datetime.now(UTC) if now is None else now)
    if cycle.sessions:
        if any(session.status is WorkoutCycleSessionStatus.SCHEDULED for session in cycle.sessions):
            return False
        current_date = local_date_for_timezone(timezone_name, now=current_at)
        return current_date >= workout_cycle_start_date(
            cycle, timezone_name=timezone_name
        ) + timedelta(days=cycle.duration_weeks * 7)
    started_at = _as_utc(cycle.started_at)
    return current_at - started_at >= timedelta(days=cycle.duration_weeks * 7)


def calculate_cycle_current_week(
    cycle: WorkoutCycle,
    *,
    timezone_name: str = DEFAULT_MEMBER_TIMEZONE,
    now: datetime | None = None,
) -> int:
    current_date = local_date_for_timezone(
        timezone_name,
        now=_as_utc(now or datetime.now(UTC)),
    )
    elapsed_days = max(
        0,
        (current_date - workout_cycle_start_date(cycle, timezone_name=timezone_name)).days,
    )
    return min(cycle.duration_weeks, elapsed_days // 7 + 1)


def workout_cycle_has_started(
    cycle: WorkoutCycle,
    *,
    timezone_name: str = DEFAULT_MEMBER_TIMEZONE,
    now: datetime | None = None,
) -> bool:
    current_date = local_date_for_timezone(
        timezone_name,
        now=_as_utc(now or datetime.now(UTC)),
    )
    return workout_cycle_start_date(cycle, timezone_name=timezone_name) <= current_date


def create_weekly_check_in(
    db: Session,
    *,
    user_id: UUID,
    cycle_id: UUID,
    week_number: int,
    sessions_completed: int,
    perceived_difficulty: WorkoutCycleWeeklyCheckInDifficulty,
    recovery_rating: WorkoutCycleWeeklyCheckInRecovery,
    has_pain_or_limitation: bool,
    note_optional: str | None = None,
    pain_workout_plan_exercise_id: UUID | None = None,
    pain_note_optional: str | None = None,
) -> WorkoutCycleWeeklyCheckIn:
    cycle = get_cycle_for_user(db, cycle_id=cycle_id, user_id=user_id)
    if cycle is None or cycle.workout_plan.user_id != user_id:
        raise WorkoutCycleWeeklyCheckInCycleNotFoundError
    if not workout_cycle_has_started(
        cycle,
        timezone_name=workout_cycle_timezone(db, user_id=user_id, cycle=cycle),
    ):
        raise WorkoutCycleWeeklyCheckInNoActiveCycleError
    _validate_weekly_check_in_payload(
        cycle,
        week_number=week_number,
        sessions_completed=sessions_completed,
        has_pain_or_limitation=has_pain_or_limitation,
        pain_workout_plan_exercise_id=pain_workout_plan_exercise_id,
        pain_note_optional=pain_note_optional,
    )

    check_in = WorkoutCycleWeeklyCheckIn(
        user_id=user_id,
        cycle_id=cycle.id,
        week_number=week_number,
        sessions_completed=sessions_completed,
        perceived_difficulty=perceived_difficulty,
        recovery_rating=recovery_rating,
        has_pain_or_limitation=has_pain_or_limitation,
        note_optional=note_optional,
    )
    _set_pain_follow_up(
        check_in,
        user_id=user_id,
        cycle_id=cycle.id,
        has_pain_or_limitation=has_pain_or_limitation,
        pain_workout_plan_exercise_id=pain_workout_plan_exercise_id,
        pain_note_optional=pain_note_optional,
        db=db,
    )
    db.add(check_in)
    try:
        db.flush()
        db.commit()
        db.refresh(check_in)
    except SQLAlchemyError:
        db.rollback()
        raise
    return check_in


def get_weekly_check_in_for_cycle_week(
    db: Session,
    *,
    cycle_id: UUID,
    week_number: int,
) -> WorkoutCycleWeeklyCheckIn | None:
    return db.scalar(
        select(WorkoutCycleWeeklyCheckIn).where(
            WorkoutCycleWeeklyCheckIn.cycle_id == cycle_id,
            WorkoutCycleWeeklyCheckIn.week_number == week_number,
        )
    )


def get_current_weekly_check_in(
    db: Session,
    *,
    user_id: UUID,
) -> WorkoutCycleWeeklyCheckIn:
    cycle = get_current_active_cycle_for_user(db, user_id=user_id)
    if cycle is None:
        raise WorkoutCycleWeeklyCheckInNoActiveCycleError
    week_number = calculate_cycle_current_week(
        cycle,
        timezone_name=workout_cycle_timezone(db, user_id=user_id, cycle=cycle),
    )
    check_in = get_weekly_check_in_for_cycle_week(
        db,
        cycle_id=cycle.id,
        week_number=week_number,
    )
    if check_in is None:
        raise WorkoutCycleWeeklyCheckInNotFoundError
    return check_in


def upsert_current_weekly_check_in(
    db: Session,
    *,
    user_id: UUID,
    sessions_completed: int,
    perceived_difficulty: WorkoutCycleWeeklyCheckInDifficulty,
    recovery_rating: WorkoutCycleWeeklyCheckInRecovery,
    has_pain_or_limitation: bool,
    note_optional: str | None = None,
    pain_workout_plan_exercise_id: UUID | None = None,
    pain_note_optional: str | None = None,
) -> WorkoutCycleWeeklyCheckIn:
    cycle = get_current_active_cycle_for_user(db, user_id=user_id)
    if cycle is None:
        raise WorkoutCycleWeeklyCheckInNoActiveCycleError
    week_number = calculate_cycle_current_week(
        cycle,
        timezone_name=workout_cycle_timezone(db, user_id=user_id, cycle=cycle),
    )
    _validate_weekly_check_in_payload(
        cycle,
        week_number=week_number,
        sessions_completed=sessions_completed,
        has_pain_or_limitation=has_pain_or_limitation,
        pain_workout_plan_exercise_id=pain_workout_plan_exercise_id,
        pain_note_optional=pain_note_optional,
    )

    check_in = db.scalar(
        select(WorkoutCycleWeeklyCheckIn)
        .where(
            WorkoutCycleWeeklyCheckIn.cycle_id == cycle.id,
            WorkoutCycleWeeklyCheckIn.week_number == week_number,
        )
        .with_for_update()
    )
    if check_in is None:
        check_in = WorkoutCycleWeeklyCheckIn(
            user_id=user_id,
            cycle_id=cycle.id,
            week_number=week_number,
            sessions_completed=sessions_completed,
            perceived_difficulty=perceived_difficulty,
            recovery_rating=recovery_rating,
            has_pain_or_limitation=has_pain_or_limitation,
            note_optional=note_optional,
        )
        db.add(check_in)
    else:
        check_in.sessions_completed = sessions_completed
        check_in.perceived_difficulty = perceived_difficulty
        check_in.recovery_rating = recovery_rating
        check_in.has_pain_or_limitation = has_pain_or_limitation
        check_in.note_optional = note_optional
        check_in.submitted_at = datetime.now(UTC)

    _set_pain_follow_up(
        check_in,
        user_id=user_id,
        cycle_id=cycle.id,
        has_pain_or_limitation=has_pain_or_limitation,
        pain_workout_plan_exercise_id=pain_workout_plan_exercise_id,
        pain_note_optional=pain_note_optional,
        db=db,
    )
    try:
        db.flush()
        db.commit()
        db.refresh(check_in)
    except SQLAlchemyError:
        db.rollback()
        raise
    return check_in


def record_exercise_replacement(
    db: Session,
    *,
    user_id: UUID,
    workout_plan_exercise_id: UUID,
    replacement_exercise_id: UUID,
    reason: WorkoutExerciseReplacementReason,
    scope: WorkoutExerciseReplacementScope,
) -> WorkoutExerciseReplacement:
    cycle = get_current_active_cycle_for_user(db, user_id=user_id)
    if cycle is None:
        raise WorkoutExerciseReplacementNoActiveCycleError

    plan = get_plan_for_user(db, plan_id=cycle.workout_plan_id, user_id=user_id)
    if plan is None or plan.status is not WorkoutPlanStatus.ACTIVE:
        raise WorkoutExerciseReplacementPlanExerciseNotFoundError

    prescribed = next(
        (
            item
            for day in plan.days
            for item in day.exercises
            if item.id == workout_plan_exercise_id
        ),
        None,
    )
    if prescribed is None:
        raise WorkoutExerciseReplacementPlanExerciseNotFoundError

    if replacement_exercise_id == prescribed.exercise_id:
        raise WorkoutExerciseReplacementSelfError
    if replacement_exercise_id not in _allowed_replacement_ids(prescribed):
        raise WorkoutExerciseReplacementAlternativeNotAllowedError

    replacement = WorkoutExerciseReplacement(
        user_id=user_id,
        cycle_id=cycle.id,
        workout_plan_exercise_id=prescribed.id,
        original_exercise_id=prescribed.exercise_id,
        replacement_exercise_id=replacement_exercise_id,
        reason=reason,
        scope=scope,
        week_number=calculate_cycle_current_week(
            cycle,
            timezone_name=workout_cycle_timezone(db, user_id=user_id, cycle=cycle),
        ),
    )
    db.add(replacement)
    try:
        db.flush()
        _persist_replacement_meaning(db, replacement)
        db.commit()
        db.refresh(replacement)
    except SQLAlchemyError:
        db.rollback()
        raise
    return replacement


def record_workout_cycle_exercise_feedback(
    db: Session,
    *,
    user_id: UUID,
    cycle_id: UUID,
    workout_plan_exercise_id: UUID,
    feedback_type: WorkoutCycleExerciseFeedbackType,
    persistent: bool,
    note_optional: str | None = None,
) -> WorkoutCycleExerciseFeedback:
    cycle = get_cycle_for_user(db, cycle_id=cycle_id, user_id=user_id)
    if cycle is None:
        raise WorkoutCycleExerciseFeedbackPlanExerciseNotFoundError
    if cycle.status is WorkoutCycleStatus.ACTIVE and not workout_cycle_has_started(
        cycle,
        timezone_name=workout_cycle_timezone(db, user_id=user_id, cycle=cycle),
    ):
        raise WorkoutCycleExerciseFeedbackNotStartedError

    prescribed = db.scalar(
        select(WorkoutPlanExercise)
        .join(WorkoutDay, WorkoutDay.id == WorkoutPlanExercise.workout_day_id)
        .where(
            WorkoutPlanExercise.id == workout_plan_exercise_id,
            WorkoutDay.workout_plan_id == cycle.workout_plan_id,
        )
    )
    if prescribed is None:
        raise WorkoutCycleExerciseFeedbackPlanExerciseNotFoundError
    if note_optional is not None and len(note_optional) > 1000:
        raise ValueError("Exercise feedback note must be at most 1000 characters")

    existing = db.scalar(
        select(WorkoutCycleExerciseFeedback).where(
            WorkoutCycleExerciseFeedback.cycle_id == cycle.id,
            WorkoutCycleExerciseFeedback.workout_plan_exercise_id == prescribed.id,
            WorkoutCycleExerciseFeedback.feedback_type == feedback_type,
        )
    )
    if existing is not None:
        raise WorkoutCycleExerciseFeedbackDuplicateError

    feedback = WorkoutCycleExerciseFeedback(
        user_id=user_id,
        cycle_id=cycle.id,
        workout_plan_exercise_id=prescribed.id,
        exercise_id=prescribed.exercise_id,
        feedback_type=feedback_type,
        persistent=persistent,
        note_optional=note_optional,
    )
    db.add(feedback)
    try:
        db.flush()
        db.commit()
        db.refresh(feedback)
    except SQLAlchemyError:
        db.rollback()
        raise
    return feedback


def get_cycle_exercise_feedback_suggestions(
    db: Session,
    *,
    user_id: UUID,
    cycle_id: UUID,
) -> list[WorkoutCycleExerciseFeedbackSuggestionResponse]:
    cycle = get_cycle_for_user(db, cycle_id=cycle_id, user_id=user_id)
    if cycle is None:
        raise WorkoutCycleNotFoundError

    replacements = list(
        db.scalars(
            select(WorkoutExerciseReplacement)
            .options(
                joinedload(WorkoutExerciseReplacement.original_exercise),
                joinedload(WorkoutExerciseReplacement.replacement_exercise),
            )
            .where(
                WorkoutExerciseReplacement.user_id == user_id,
                WorkoutExerciseReplacement.cycle_id == cycle.id,
            )
            .order_by(
                WorkoutExerciseReplacement.workout_plan_exercise_id,
                WorkoutExerciseReplacement.created_at,
                WorkoutExerciseReplacement.id,
            )
        ).all()
    )
    if not replacements:
        return []

    original_exercise_ids = {replacement.original_exercise_id for replacement in replacements}
    preferences = list(
        db.scalars(
            select(WorkoutExercisePreference).where(
                WorkoutExercisePreference.user_id == user_id,
                WorkoutExercisePreference.exercise_id.in_(original_exercise_ids),
            )
        ).all()
    )
    safety_signals = list(
        db.scalars(
            select(WorkoutExerciseSafetySignal).where(
                WorkoutExerciseSafetySignal.user_id == user_id,
                WorkoutExerciseSafetySignal.cycle_id == cycle.id,
                WorkoutExerciseSafetySignal.original_exercise_id.in_(original_exercise_ids),
            )
        ).all()
    )

    preferences_by_exercise: dict[UUID, list[WorkoutExercisePreference]] = {}
    for preference in preferences:
        preferences_by_exercise.setdefault(preference.exercise_id, []).append(preference)
    safety_by_exercise: dict[UUID, list[WorkoutExerciseSafetySignal]] = {}
    for signal in safety_signals:
        safety_by_exercise.setdefault(signal.original_exercise_id, []).append(signal)

    grouped: dict[UUID, list[WorkoutExerciseReplacement]] = {}
    for replacement in replacements:
        if _replacement_suggestion_kind(replacement) is not None:
            grouped.setdefault(replacement.workout_plan_exercise_id, []).append(replacement)

    suggestions: list[WorkoutCycleExerciseFeedbackSuggestionResponse] = []
    for prescribed_replacements in grouped.values():
        by_kind: dict[
            WorkoutCycleExerciseFeedbackSuggestionKind,
            list[WorkoutExerciseReplacement],
        ] = {}
        for replacement in prescribed_replacements:
            kind = _replacement_suggestion_kind(replacement)
            if kind is not None:
                by_kind.setdefault(kind, []).append(replacement)

        first = prescribed_replacements[0]
        persistent_state = WorkoutCycleExerciseFeedbackPersistentStateResponse(
            preference_types=sorted(
                (
                    preference.preference_type
                    for preference in preferences_by_exercise.get(first.original_exercise_id, [])
                ),
                key=lambda preference_type: preference_type.value,
            ),
            safety_signal_types=sorted(
                (
                    signal.signal_type
                    for signal in safety_by_exercise.get(first.original_exercise_id, [])
                ),
                key=lambda signal_type: signal_type.value,
            ),
        )
        for kind, kind_replacements in by_kind.items():
            suggestions.append(
                _build_replacement_suggestion(
                    kind=kind,
                    replacements=kind_replacements,
                    persistent_state=persistent_state,
                )
            )

    return suggestions


def _replacement_suggestion_kind(
    replacement: WorkoutExerciseReplacement,
) -> WorkoutCycleExerciseFeedbackSuggestionKind | None:
    if replacement.reason is WorkoutExerciseReplacementReason.PAIN_OR_DISCOMFORT:
        return WorkoutCycleExerciseFeedbackSuggestionKind.SAFETY
    if replacement.scope is not WorkoutExerciseReplacementScope.PERSISTENT:
        return None
    if replacement.reason in {
        WorkoutExerciseReplacementReason.UNCOMFORTABLE,
        WorkoutExerciseReplacementReason.DISLIKE,
    }:
        return WorkoutCycleExerciseFeedbackSuggestionKind.NEGATIVE_EXERCISE_PREFERENCE
    if replacement.reason is WorkoutExerciseReplacementReason.EQUIPMENT_UNAVAILABLE:
        return WorkoutCycleExerciseFeedbackSuggestionKind.EQUIPMENT_CONTEXT
    return None


def _build_replacement_suggestion(
    *,
    kind: WorkoutCycleExerciseFeedbackSuggestionKind,
    replacements: list[WorkoutExerciseReplacement],
    persistent_state: WorkoutCycleExerciseFeedbackPersistentStateResponse,
) -> WorkoutCycleExerciseFeedbackSuggestionResponse:
    first = replacements[0]
    by_replacement_exercise: dict[UUID, list[WorkoutExerciseReplacement]] = {}
    for replacement in replacements:
        by_replacement_exercise.setdefault(replacement.replacement_exercise_id, []).append(
            replacement
        )

    replacement_summaries = [
        WorkoutCycleExerciseFeedbackReplacementSummaryResponse(
            replacement_exercise_id=rows[0].replacement_exercise_id,
            replacement_name_en=rows[0].replacement_exercise.name_en,
            replacement_name_fa=rows[0].replacement_exercise.name_fa,
            replacement_count=len(rows),
            replacement_ids=[row.id for row in rows],
            reasons=_unique_enum_values(row.reason for row in rows),
            scopes=_unique_enum_values(row.scope for row in rows),
            week_numbers=_unique_int_values(row.week_number for row in rows),
        )
        for rows in by_replacement_exercise.values()
    ]
    return WorkoutCycleExerciseFeedbackSuggestionResponse(
        suggestion_kind=kind,
        workout_plan_exercise_id=first.workout_plan_exercise_id,
        original_exercise_id=first.original_exercise_id,
        original_name_en=first.original_exercise.name_en,
        original_name_fa=first.original_exercise.name_fa,
        replacement_count=len(replacements),
        replacement_ids=[replacement.id for replacement in replacements],
        reasons=_unique_enum_values(replacement.reason for replacement in replacements),
        replacement_exercises=replacement_summaries,
        current_persistent_state=persistent_state,
    )


def _unique_enum_values[
    EnumValue: (WorkoutExerciseReplacementReason, WorkoutExerciseReplacementScope)
](values: Iterable[EnumValue]) -> list[EnumValue]:
    unique: dict[EnumValue, None] = {}
    for value in values:
        unique[value] = None
    return list(unique)


def _unique_int_values(values: Iterable[int]) -> list[int]:
    unique: dict[int, None] = {}
    for value in values:
        unique[value] = None
    return list(unique)


def _persist_replacement_meaning(
    db: Session,
    replacement: WorkoutExerciseReplacement,
) -> None:
    if replacement.reason is WorkoutExerciseReplacementReason.PAIN_OR_DISCOMFORT:
        _ensure_safety_signal(db, replacement)
        return

    if replacement.scope is not WorkoutExerciseReplacementScope.PERSISTENT:
        return

    preference_type = {
        WorkoutExerciseReplacementReason.EQUIPMENT_UNAVAILABLE: (
            WorkoutExercisePreferenceType.EQUIPMENT_UNAVAILABLE
        ),
        WorkoutExerciseReplacementReason.UNCOMFORTABLE: WorkoutExercisePreferenceType.UNCOMFORTABLE,
        WorkoutExerciseReplacementReason.DISLIKE: WorkoutExercisePreferenceType.DISLIKE,
    }.get(replacement.reason)
    if preference_type is not None:
        _ensure_exercise_preference(db, replacement, preference_type)


def _ensure_exercise_preference(
    db: Session,
    replacement: WorkoutExerciseReplacement,
    preference_type: WorkoutExercisePreferenceType,
) -> None:
    existing = db.scalar(
        select(WorkoutExercisePreference).where(
            WorkoutExercisePreference.user_id == replacement.user_id,
            WorkoutExercisePreference.exercise_id == replacement.original_exercise_id,
            WorkoutExercisePreference.preference_type == preference_type,
        )
    )
    if existing is not None:
        return

    preference = WorkoutExercisePreference(
        user_id=replacement.user_id,
        exercise_id=replacement.original_exercise_id,
        preference_type=preference_type,
        source_replacement_id=replacement.id,
    )
    try:
        with db.begin_nested():
            db.add(preference)
            db.flush()
    except IntegrityError:
        if (
            db.scalar(
                select(WorkoutExercisePreference).where(
                    WorkoutExercisePreference.user_id == replacement.user_id,
                    WorkoutExercisePreference.exercise_id == replacement.original_exercise_id,
                    WorkoutExercisePreference.preference_type == preference_type,
                )
            )
            is None
        ):
            raise


def _ensure_safety_signal(
    db: Session,
    replacement: WorkoutExerciseReplacement,
) -> None:
    existing = db.scalar(
        select(WorkoutExerciseSafetySignal).where(
            WorkoutExerciseSafetySignal.user_id == replacement.user_id,
            WorkoutExerciseSafetySignal.cycle_id == replacement.cycle_id,
            WorkoutExerciseSafetySignal.workout_plan_exercise_id
            == replacement.workout_plan_exercise_id,
            WorkoutExerciseSafetySignal.replacement_exercise_id
            == replacement.replacement_exercise_id,
            WorkoutExerciseSafetySignal.week_number == replacement.week_number,
            WorkoutExerciseSafetySignal.signal_type
            == WorkoutExerciseSafetySignalType.PAIN_OR_DISCOMFORT,
        )
    )
    if existing is not None:
        return

    signal = WorkoutExerciseSafetySignal(
        user_id=replacement.user_id,
        cycle_id=replacement.cycle_id,
        workout_plan_exercise_id=replacement.workout_plan_exercise_id,
        original_exercise_id=replacement.original_exercise_id,
        replacement_exercise_id=replacement.replacement_exercise_id,
        signal_type=WorkoutExerciseSafetySignalType.PAIN_OR_DISCOMFORT,
        week_number=replacement.week_number,
        source_replacement_id=replacement.id,
    )
    try:
        with db.begin_nested():
            db.add(signal)
            db.flush()
    except IntegrityError:
        if (
            db.scalar(
                select(WorkoutExerciseSafetySignal).where(
                    WorkoutExerciseSafetySignal.user_id == replacement.user_id,
                    WorkoutExerciseSafetySignal.cycle_id == replacement.cycle_id,
                    WorkoutExerciseSafetySignal.workout_plan_exercise_id
                    == replacement.workout_plan_exercise_id,
                    WorkoutExerciseSafetySignal.replacement_exercise_id
                    == replacement.replacement_exercise_id,
                    WorkoutExerciseSafetySignal.week_number == replacement.week_number,
                    WorkoutExerciseSafetySignal.signal_type
                    == WorkoutExerciseSafetySignalType.PAIN_OR_DISCOMFORT,
                )
            )
            is None
        ):
            raise


def start_cycle(
    db: Session,
    *,
    user_id: UUID,
    workout_plan_id: UUID,
    start_date: date,
    timezone_name: str,
) -> WorkoutCycle:
    validated_timezone = validate_timezone_name(timezone_name)
    plan = db.scalar(
        select(WorkoutPlan)
        .where(WorkoutPlan.id == workout_plan_id, WorkoutPlan.user_id == user_id)
        .options(selectinload(WorkoutPlan.days))
    )
    if plan is None:
        raise WorkoutCycleNotFoundError
    if plan.status is not WorkoutPlanStatus.ACTIVE or plan.deleted_at is not None:
        raise WorkoutCyclePlanInactiveError

    existing = db.scalar(
        select(WorkoutCycle).where(
            WorkoutCycle.workout_plan_id == workout_plan_id,
            WorkoutCycle.user_id == user_id,
        )
    )
    if existing is not None:
        existing_start_date = workout_cycle_start_date(
            existing,
            timezone_name=validated_timezone,
        )
        if existing_start_date == start_date:
            _persist_cycle_timezone(db, user_id=user_id, timezone_name=validated_timezone)
            db.flush()
            return existing
        raise WorkoutCycleAlreadyStartedError

    duration_weeks = _plan_duration_weeks(plan)
    cycle = WorkoutCycle(
        user_id=user_id,
        workout_plan_id=plan.id,
        duration_weeks=duration_weeks,
        started_at=local_midnight_utc(start_date, validated_timezone),
        start_date=start_date,
        start_timezone=validated_timezone,
    )
    try:
        with db.begin_nested():
            db.add(cycle)
            db.flush()
    except IntegrityError as error:
        concurrent_cycle = db.scalar(
            select(WorkoutCycle).where(WorkoutCycle.workout_plan_id == workout_plan_id)
        )
        if concurrent_cycle is not None:
            concurrent_start_date = workout_cycle_start_date(
                concurrent_cycle,
                timezone_name=validated_timezone,
            )
            if concurrent_start_date == start_date:
                return concurrent_cycle
            raise WorkoutCycleAlreadyStartedError from error
        raise
    _persist_cycle_timezone(db, user_id=user_id, timezone_name=validated_timezone)
    sessions = build_cycle_sessions(
        cycle_id=cycle.id,
        plan=plan,
        start_date=start_date,
        duration_weeks=duration_weeks,
    )
    db.add_all(sessions)
    db.flush()
    return cycle


def build_cycle_sessions(
    *,
    cycle_id: UUID,
    plan: WorkoutPlan,
    start_date: date,
    duration_weeks: int,
) -> list[WorkoutCycleSession]:
    days = list(plan.days)
    if not days:
        return []

    stored_weekdays = tuple(day.weekday for day in days)
    if all(weekday is not None for weekday in stored_weekdays):
        weekdays = tuple(int(weekday) for weekday in stored_weekdays if weekday is not None)
    else:
        weekdays = _fallback_weekdays(plan, len(days))

    scheduled: list[tuple[date, int, int, WorkoutDay]] = []
    start_weekday = fitician_weekday(start_date)
    for week_number in range(1, duration_weeks + 1):
        for day_order, (day, weekday) in enumerate(zip(days, weekdays, strict=True)):
            offset = (weekday - start_weekday) % 7
            scheduled.append(
                (
                    start_date + timedelta(days=offset + (week_number - 1) * 7),
                    day_order,
                    week_number,
                    day,
                )
            )

    scheduled.sort(key=lambda item: (item[0], item[1]))
    return [
        WorkoutCycleSession(
            cycle_id=cycle_id,
            workout_day_id=day.id,
            week_number=week_number,
            session_number=session_number,
            scheduled_date=scheduled_date,
            status=WorkoutCycleSessionStatus.SCHEDULED,
        )
        for session_number, (scheduled_date, _, week_number, day) in enumerate(
            scheduled,
            start=1,
        )
    ]


def _fallback_weekdays(plan: WorkoutPlan, day_count: int) -> tuple[int, ...]:
    snapshot_weekdays = plan.profile_snapshot.get("preferred_weekdays")
    if isinstance(snapshot_weekdays, (list, tuple)):
        valid = (
            len(snapshot_weekdays) == day_count
            and len(set(snapshot_weekdays)) == day_count
            and all(
                isinstance(weekday, int) and not isinstance(weekday, bool) and 0 <= weekday <= 6
                for weekday in snapshot_weekdays
            )
        )
        if valid:
            return tuple(int(weekday) for weekday in snapshot_weekdays)

    from app.workouts.program_engine.rulesets.resistance_training_v1 import RULESET

    try:
        return RULESET.default_weekdays[day_count]
    except KeyError as error:
        raise ValueError("Workout plan has no supported weekday fallback") from error


def _persist_cycle_timezone(db: Session, *, user_id: UUID, timezone_name: str) -> None:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id).with_for_update())
    if profile is not None:
        profile.timezone = timezone_name


def _current_plan_cycles(
    db: Session,
    *,
    user_id: UUID,
    lock: bool,
) -> list[WorkoutCycle]:
    query = (
        select(WorkoutCycle)
        .join(WorkoutPlan, WorkoutCycle.workout_plan_id == WorkoutPlan.id)
        .where(
            WorkoutCycle.user_id == user_id,
            WorkoutCycle.status == WorkoutCycleStatus.ACTIVE,
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.status == WorkoutPlanStatus.ACTIVE,
            WorkoutPlan.deleted_at.is_(None),
        )
        .order_by(WorkoutCycle.started_at.desc(), WorkoutCycle.id.desc())
    )
    if lock:
        query = query.with_for_update()
    return list(db.scalars(query).all())


def _current_active_workout_plan(db: Session, *, user_id: UUID) -> WorkoutPlan | None:
    return db.scalar(
        select(WorkoutPlan)
        .where(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.status == WorkoutPlanStatus.ACTIVE,
            WorkoutPlan.deleted_at.is_(None),
        )
        .order_by(WorkoutPlan.created_at.desc(), WorkoutPlan.id.desc())
        .limit(1)
    )


def _current_executable_cycle(
    db: Session,
    *,
    user_id: UUID,
    lock: bool,
    now: datetime | None = None,
) -> WorkoutCycle | None:
    cycles = _current_plan_cycles(db, user_id=user_id, lock=lock)
    profile_timezone = db.scalar(select(UserProfile.timezone).where(UserProfile.user_id == user_id))
    return next(
        (
            cycle
            for cycle in cycles
            if workout_cycle_has_started(
                cycle,
                timezone_name=member_timezone_or_default(profile_timezone, cycle.start_timezone),
                now=now,
            )
        ),
        None,
    )


def _locked_current_cycle(db: Session, *, user_id: UUID) -> WorkoutCycle | None:
    return _current_executable_cycle(db, user_id=user_id, lock=True)


def _locked_current_session(
    db: Session,
    *,
    user_id: UUID,
    session_id: UUID,
) -> WorkoutCycleSession:
    session = db.scalar(
        select(WorkoutCycleSession)
        .join(WorkoutCycle, WorkoutCycle.id == WorkoutCycleSession.cycle_id)
        .join(WorkoutPlan, WorkoutPlan.id == WorkoutCycle.workout_plan_id)
        .where(
            WorkoutCycleSession.id == session_id,
            WorkoutCycle.user_id == user_id,
            WorkoutCycle.status == WorkoutCycleStatus.ACTIVE,
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.status == WorkoutPlanStatus.ACTIVE,
            WorkoutPlan.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if session is None:
        raise WorkoutCycleSessionNotFoundError
    return session


def complete_current_cycle_session(
    db: Session,
    *,
    user_id: UUID,
    session_id: UUID,
    now: datetime | None = None,
) -> WorkoutCycleSession:
    session = _locked_current_session(db, user_id=user_id, session_id=session_id)
    if session.status is not WorkoutCycleSessionStatus.SCHEDULED:
        raise WorkoutCycleSessionAlreadyFinishedError
    _ensure_actionable_session(
        db,
        user_id=user_id,
        session=session,
        now=now,
        require_due=True,
    )
    session.status = WorkoutCycleSessionStatus.COMPLETED
    session.completed_at = _as_utc(now or datetime.now(UTC))
    session.skipped_at = None
    try:
        db.flush()
        db.commit()
        db.refresh(session)
    except SQLAlchemyError:
        db.rollback()
        raise
    return session


def skip_current_cycle_session(
    db: Session,
    *,
    user_id: UUID,
    session_id: UUID,
    now: datetime | None = None,
) -> WorkoutCycleSession:
    session = _locked_current_session(db, user_id=user_id, session_id=session_id)
    if session.status is not WorkoutCycleSessionStatus.SCHEDULED:
        raise WorkoutCycleSessionAlreadyFinishedError
    _ensure_actionable_session(
        db,
        user_id=user_id,
        session=session,
        now=now,
        require_due=True,
    )
    session.status = WorkoutCycleSessionStatus.SKIPPED
    session.skipped_at = _as_utc(now or datetime.now(UTC))
    session.completed_at = None
    try:
        db.flush()
        db.commit()
        db.refresh(session)
    except SQLAlchemyError:
        db.rollback()
        raise
    return session


def reschedule_current_cycle_session(
    db: Session,
    *,
    user_id: UUID,
    session_id: UUID,
    scheduled_date: date,
    now: datetime | None = None,
) -> WorkoutCycleSession:
    session = _locked_current_session(db, user_id=user_id, session_id=session_id)
    if session.status is not WorkoutCycleSessionStatus.SCHEDULED:
        raise WorkoutCycleSessionAlreadyFinishedError

    _ensure_actionable_session(
        db,
        user_id=user_id,
        session=session,
        now=now,
        require_due=False,
    )

    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    timezone_name = member_timezone_or_default(profile.timezone if profile is not None else None)
    cycle_start_date = workout_cycle_start_date(session.cycle, timezone_name=timezone_name)
    if scheduled_date < cycle_start_date:
        raise WorkoutCycleSessionBeforeStartError
    all_sessions = list(
        db.scalars(
            select(WorkoutCycleSession)
            .where(WorkoutCycleSession.cycle_id == session.cycle_id)
            .order_by(WorkoutCycleSession.session_number)
            .with_for_update()
        ).all()
    )
    terminal_dates = {
        item.scheduled_date
        for item in all_sessions
        if item.status is not WorkoutCycleSessionStatus.SCHEDULED
    }
    if scheduled_date in terminal_dates:
        raise WorkoutCycleSessionDateConflictError

    unresolved = [
        item for item in all_sessions if item.status is WorkoutCycleSessionStatus.SCHEDULED
    ]
    if not unresolved or unresolved[0].id != session.id:
        raise WorkoutCycleSessionNotActionableError("Workout cycle session is not actionable")
    original_dates = [item.scheduled_date for item in unresolved]
    delta = scheduled_date - original_dates[0]
    shifted_dates = [scheduled_date]
    for index, original_date in enumerate(original_dates[1:], start=1):
        original_gap = max(1, (original_date - original_dates[index - 1]).days)
        candidate = original_date + delta if delta.days > 0 else original_date
        candidate = max(candidate, shifted_dates[-1] + timedelta(days=original_gap))
        while candidate in terminal_dates:
            candidate += timedelta(days=1)
        shifted_dates.append(candidate)
    for item, next_date in zip(unresolved, shifted_dates, strict=True):
        item.scheduled_date = next_date
    try:
        db.flush()
        db.commit()
        db.refresh(session)
    except SQLAlchemyError:
        db.rollback()
        raise
    return session


def get_cycle_for_user(
    db: Session,
    *,
    cycle_id: UUID,
    user_id: UUID,
) -> WorkoutCycle | None:
    return db.scalar(
        select(WorkoutCycle).where(
            WorkoutCycle.id == cycle_id,
            WorkoutCycle.user_id == user_id,
        )
    )


def get_current_active_cycle_for_user(
    db: Session,
    *,
    user_id: UUID,
) -> WorkoutCycle | None:
    return _current_executable_cycle(db, user_id=user_id, lock=False)


def get_current_completion_feedback_cycle(
    db: Session,
    *,
    user_id: UUID,
) -> WorkoutCycle:
    active_plan = _current_active_workout_plan(db, user_id=user_id)
    if active_plan is not None:
        current = get_current_active_cycle_for_user(db, user_id=user_id)
        if current is not None:
            return current
        current_plan_cycle = db.scalar(
            select(WorkoutCycle)
            .options(joinedload(WorkoutCycle.completion_feedback))
            .where(WorkoutCycle.workout_plan_id == active_plan.id)
        )
        if (
            current_plan_cycle is not None
            and current_plan_cycle.status is WorkoutCycleStatus.COMPLETED
            and current_plan_cycle.completion_feedback is not None
        ):
            return current_plan_cycle
        raise WorkoutCycleCompletionFeedbackNotFoundError

    current = get_current_active_cycle_for_user(db, user_id=user_id)
    if current is not None:
        return current
    if _current_plan_cycles(db, user_id=user_id, lock=False):
        raise WorkoutCycleCompletionFeedbackNotFoundError
    cycles = db.scalars(
        select(WorkoutCycle)
        .options(joinedload(WorkoutCycle.completion_feedback))
        .where(WorkoutCycle.user_id == user_id)
        .order_by(WorkoutCycle.started_at.desc(), WorkoutCycle.id.desc())
    ).all()
    for cycle in cycles:
        if cycle.status is WorkoutCycleStatus.COMPLETED and cycle.completion_feedback is not None:
            return cycle
    raise WorkoutCycleCompletionFeedbackNotFoundError


def completion_feedback_input(
    feedback: WorkoutCycleFeedback | None,
) -> CompletionFeedbackInput | None:
    if feedback is None:
        return None
    return CompletionFeedbackInput(
        adherence_percent=feedback.adherence_percent,
        performance_changes=feedback.performance_changes,
        pain_or_limitation_feedback=feedback.pain_or_limitation_feedback,
        measurements=dict(feedback.measurements),
        overall_difficulty=feedback.overall_difficulty,
        overall_recovery=feedback.overall_recovery,
        overall_satisfaction=feedback.overall_satisfaction,
        strength_progress=feedback.strength_progress,
        muscle_progress=feedback.muscle_progress,
        endurance_progress=feedback.endurance_progress,
        energy_progress=feedback.energy_progress,
        progressed_muscles=(
            [MuscleGroup(value) for value in feedback.progressed_muscles]
            if feedback.progressed_muscles is not None
            else None
        ),
        lagging_muscles=(
            [MuscleGroup(value) for value in feedback.lagging_muscles]
            if feedback.lagging_muscles is not None
            else None
        ),
        goal_changed=feedback.goal_changed,
        next_goal=feedback.next_goal,
        schedule_changed=feedback.schedule_changed,
        next_training_days=feedback.next_training_days,
        next_session_duration_minutes=feedback.next_session_duration_minutes,
        next_preferred_weekdays=(
            tuple(feedback.next_preferred_weekdays)
            if feedback.next_preferred_weekdays is not None
            else None
        ),
        next_training_location=feedback.next_training_location,
        next_home_training_setup=feedback.next_home_training_setup,
        equipment_changed=feedback.equipment_changed,
        new_limitation=feedback.new_limitation,
        note_optional=feedback.note_optional,
    )


def submit_current_completion_feedback(
    db: Session,
    *,
    user_id: UUID,
    feedback: CompletionFeedbackInput,
) -> WorkoutCycle:
    cycle = get_current_completion_feedback_cycle(db, user_id=user_id)
    if cycle.status is WorkoutCycleStatus.COMPLETED:
        return cycle
    if not cycle_has_reached_nominal_end(
        cycle,
        timezone_name=workout_cycle_timezone(db, user_id=user_id, cycle=cycle),
    ):
        raise WorkoutCycleCompletionFeedbackNotDueError
    return complete_cycle(
        db,
        cycle_id=cycle.id,
        user_id=user_id,
        feedback=feedback,
    )


_FEEDBACK_GOAL_TO_PROFILE_GOAL: dict[Goal, FitnessGoal] = {
    Goal.FAT_LOSS: FitnessGoal.FAT_LOSS,
    Goal.HYPERTROPHY: FitnessGoal.BUILD_MUSCLE,
    Goal.MUSCLE_GAIN: FitnessGoal.BUILD_MUSCLE,
    Goal.BODY_RECOMPOSITION: FitnessGoal.BODY_RECOMPOSITION,
    Goal.GENERAL_FITNESS: FitnessGoal.IMPROVE_FITNESS,
    Goal.STRENGTH: FitnessGoal.STRENGTH,
}


def _confirmed_profile_update_from_feedback(
    feedback: CompletionFeedbackInput,
) -> ProfileUpdate | None:
    values: dict[str, object] = {}
    if feedback.goal_changed is True and feedback.next_goal is not None:
        profile_goal = _FEEDBACK_GOAL_TO_PROFILE_GOAL.get(feedback.next_goal)
        if profile_goal is not None:
            values["fitness_goal"] = profile_goal

    if feedback.schedule_changed is True:
        if feedback.next_training_days is not None:
            values["training_days_per_week"] = feedback.next_training_days
        if feedback.next_session_duration_minutes is not None:
            values["session_duration_minutes"] = feedback.next_session_duration_minutes
        if feedback.next_preferred_weekdays is not None:
            values["preferred_weekdays"] = feedback.next_preferred_weekdays

    if feedback.equipment_changed is True and feedback.next_training_location is not None:
        values["training_location"] = feedback.next_training_location
        if feedback.next_training_location is TrainingLocation.HOME:
            values["home_training_setup"] = feedback.next_home_training_setup
        elif feedback.next_training_location is TrainingLocation.GYM:
            values["home_training_setup"] = None

    if not values:
        return None
    return ProfileUpdate.model_validate(values)


def apply_confirmed_end_cycle_profile_changes(
    db: Session,
    *,
    user_id: UUID,
    feedback: CompletionFeedbackInput,
) -> None:
    profile_update = _confirmed_profile_update_from_feedback(feedback)
    if profile_update is not None:
        profile = apply_profile_update_without_commit(db, user_id, profile_update)
    else:
        profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is not None and feedback.new_limitation is not None:
        limitation = feedback.new_limitation.strip()
        if limitation:
            # Preserve the legacy cycle-feedback audit value without exposing it
            # to workout generation or accepting it in the profile API.
            profile.physical_limitations = limitation


def complete_cycle(
    db: Session,
    *,
    cycle_id: UUID,
    user_id: UUID,
    feedback: CompletionFeedbackInput | None = None,
) -> WorkoutCycle:
    cycle = db.scalar(
        select(WorkoutCycle)
        .where(
            WorkoutCycle.id == cycle_id,
            WorkoutCycle.user_id == user_id,
        )
        .with_for_update()
    )
    if cycle is None:
        raise WorkoutCycleNotFoundError
    if cycle.status is WorkoutCycleStatus.COMPLETED:
        raise WorkoutCycleAlreadyCompletedError
    if cycle.sessions and any(
        session.status is WorkoutCycleSessionStatus.SCHEDULED for session in cycle.sessions
    ):
        raise WorkoutCycleCompletionFeedbackNotDueError

    cycle.status = WorkoutCycleStatus.COMPLETED
    cycle.completed_at = datetime.now(UTC)
    if feedback is not None:
        from app.workout_cycles.body_progress_service import compare_cycle_body_progress

        body_progress_comparison = compare_cycle_body_progress(
            db,
            user_id=user_id,
            cycle_id=cycle.id,
            commit=False,
        )
        cycle.completion_feedback = WorkoutCycleFeedback(
            body_progress_comparison_id=body_progress_comparison.id,
            adherence_percent=feedback.adherence_percent,
            performance_changes=feedback.performance_changes,
            pain_or_limitation_feedback=feedback.pain_or_limitation_feedback,
            measurements=dict(feedback.measurements),
            overall_difficulty=feedback.overall_difficulty,
            overall_recovery=feedback.overall_recovery,
            overall_satisfaction=feedback.overall_satisfaction,
            strength_progress=feedback.strength_progress,
            muscle_progress=feedback.muscle_progress,
            endurance_progress=feedback.endurance_progress,
            energy_progress=feedback.energy_progress,
            progressed_muscles=(
                [muscle.value for muscle in feedback.progressed_muscles]
                if feedback.progressed_muscles is not None
                else None
            ),
            lagging_muscles=(
                [muscle.value for muscle in feedback.lagging_muscles]
                if feedback.lagging_muscles is not None
                else None
            ),
            goal_changed=feedback.goal_changed,
            next_goal=feedback.next_goal,
            schedule_changed=feedback.schedule_changed,
            next_training_days=feedback.next_training_days,
            next_session_duration_minutes=feedback.next_session_duration_minutes,
            next_preferred_weekdays=(
                list(feedback.next_preferred_weekdays)
                if feedback.next_preferred_weekdays is not None
                else None
            ),
            next_training_location=feedback.next_training_location,
            next_home_training_setup=feedback.next_home_training_setup,
            equipment_changed=feedback.equipment_changed,
            new_limitation=feedback.new_limitation,
            note_optional=feedback.note_optional,
        )
        apply_confirmed_end_cycle_profile_changes(db, user_id=user_id, feedback=feedback)
    db.flush()
    return cycle


def get_cycle_feedback_body_progress_context(
    db: Session,
    *,
    cycle_id: UUID,
    user_id: UUID,
) -> WorkoutCycleFeedbackBodyProgressContext | None:
    cycle = get_cycle_for_user(db, cycle_id=cycle_id, user_id=user_id)
    if cycle is None:
        raise WorkoutCycleNotFoundError
    feedback = db.scalar(
        select(WorkoutCycleFeedback).where(WorkoutCycleFeedback.cycle_id == cycle.id)
    )
    if feedback is None:
        return None

    comparison = feedback.body_progress_comparison
    comparison_response = None
    if comparison is not None and comparison.user_id == user_id and comparison.cycle_id == cycle.id:
        comparison_response = WorkoutCycleBodyProgressComparisonResponse(
            id=comparison.id,
            cycle_id=comparison.cycle_id,
            result=comparison.comparison_result,
            created_at=comparison.created_at,
            updated_at=comparison.updated_at,
        )
    return WorkoutCycleFeedbackBodyProgressContext(
        feedback_id=feedback.id,
        cycle_id=cycle.id,
        body_progress_comparison=comparison_response,
    )


def _plan_duration_weeks(plan: WorkoutPlan) -> int:
    raw_duration = plan.profile_snapshot.get("plan_duration_weeks")
    if raw_duration is None:
        raw_duration = plan.profile_snapshot.get("program_duration_weeks")
    if isinstance(raw_duration, bool) or not isinstance(raw_duration, int):
        raise ValueError("Workout cycle duration must be 4, 6, or 8 weeks")
    if raw_duration not in SUPPORTED_CYCLE_DURATIONS:
        raise ValueError("Workout cycle duration must be 4, 6, or 8 weeks")
    return raw_duration


def _find_prescribed_exercise(
    cycle: WorkoutCycle,
    *,
    workout_plan_exercise_id: UUID,
) -> WorkoutPlanExercise | None:
    return next(
        (
            item
            for day in cycle.workout_plan.days
            for item in day.exercises
            if item.id == workout_plan_exercise_id
        ),
        None,
    )


def _validate_weekly_check_in_payload(
    cycle: WorkoutCycle,
    *,
    week_number: int,
    sessions_completed: int,
    has_pain_or_limitation: bool,
    pain_workout_plan_exercise_id: UUID | None,
    pain_note_optional: str | None,
) -> None:
    if not 1 <= week_number <= cycle.duration_weeks:
        raise WorkoutCycleWeeklyCheckInWeekOutOfRangeError(
            "Weekly check-in week must be within the workout cycle duration"
        )

    prescribed_training_days = len(cycle.workout_plan.days)
    if not 0 <= sessions_completed <= prescribed_training_days:
        raise WorkoutCycleWeeklyCheckInSessionsOutOfRangeError(
            "Completed sessions must be within the plan's prescribed weekly days"
        )

    if has_pain_or_limitation:
        if pain_workout_plan_exercise_id is None:
            raise WorkoutCycleWeeklyCheckInPainExerciseRequiredError(
                "A prescribed exercise is required when pain or limitation is reported"
            )
        if pain_note_optional is not None and len(pain_note_optional) > 500:
            raise ValueError("Pain or limitation note must be 500 characters or fewer")
        prescribed = _find_prescribed_exercise(
            cycle,
            workout_plan_exercise_id=pain_workout_plan_exercise_id,
        )
        if prescribed is None:
            raise WorkoutCycleWeeklyCheckInPainExerciseNotFoundError
    elif pain_workout_plan_exercise_id is not None or pain_note_optional is not None:
        raise WorkoutCycleWeeklyCheckInPainFollowUpNotAllowedError(
            "Pain follow-up data requires has_pain_or_limitation=True"
        )


def _set_pain_follow_up(
    check_in: WorkoutCycleWeeklyCheckIn,
    *,
    user_id: UUID,
    cycle_id: UUID,
    has_pain_or_limitation: bool,
    pain_workout_plan_exercise_id: UUID | None,
    pain_note_optional: str | None,
    db: Session,
) -> None:
    if check_in.pain_limitation is not None:
        db.delete(check_in.pain_limitation)
        check_in.pain_limitation = None
    if has_pain_or_limitation:
        assert pain_workout_plan_exercise_id is not None
        check_in.pain_limitation = WorkoutCycleWeeklyCheckInPainLimitation(
            user_id=user_id,
            cycle_id=cycle_id,
            workout_plan_exercise_id=pain_workout_plan_exercise_id,
            note_optional=pain_note_optional,
        )


def _allowed_replacement_ids(item: WorkoutPlanExercise) -> set[UUID]:
    substitution_ids = item.substitution_exercise_ids
    if substitution_ids:
        allowed: set[UUID] = set()
        for value in substitution_ids:
            try:
                allowed.add(UUID(value))
            except (TypeError, ValueError):
                continue
        return allowed

    return {
        alternative.alternative_exercise_id
        for alternative in item.exercise.alternatives
        if isinstance(alternative, ExerciseAlternative)
        and alternative.alternative_exercise.is_active
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Workout cycle dates must be timezone-aware")
    return value.astimezone(UTC)
