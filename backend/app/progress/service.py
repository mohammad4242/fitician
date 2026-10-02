from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.body_analysis.models import BodyAnalysis
from app.body_photos.models import BodyPhotoSession
from app.nutrition.enums import NutritionPlanLifecycleStatus, SafetyOutcome
from app.nutrition.medical_context import current_medical_safety_decision
from app.nutrition.models import NutritionWeeklyPlan
from app.profile.enums import ProductMode
from app.profile.models import UserProfile
from app.progress.body import body_series
from app.progress.nutrition import nutrition_series
from app.progress.schemas import (
    AnalysisSummary,
    Preset,
    ProgressContext,
    ProgressInsight,
    ProgressOverview,
    ProgressTraining,
    RecoveryPoint,
    TrainingWeek,
)
from app.workout_cycles.enums import WorkoutCycleSessionStatus, WorkoutCycleStatus
from app.workout_cycles.models import (
    WorkoutCycle,
    WorkoutCycleFeedback,
    WorkoutCycleSession,
    WorkoutCycleWeeklyCheckIn,
    WorkoutSessionRescheduleEvent,
)


def week_start(day: date) -> date:
    # Fitician's member calendar week starts on Saturday.
    return day - timedelta(days=(day.weekday() + 2) % 7)


def period_dates(preset: Preset, today: date, program_start: date | None) -> tuple[date, date]:
    if preset == "week":
        start = week_start(today)
        return start, start + timedelta(days=6)
    start = (
        program_start
        if preset == "current_program" and program_start
        else today - timedelta(days=27)
    )
    return max(start, today - timedelta(days=365)), today


def overview(
    db: Session,
    user_id: UUID,
    *,
    preset: Preset,
    timezone: str | None = None,
    now: datetime | None = None,
) -> ProgressOverview:
    profile = db.get(UserProfile, user_id)
    zone = timezone or (profile.timezone if profile else "Asia/Tehran")
    try:
        tz = ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, detail={"code": "INVALID_TIMEZONE"}) from None
    current = now or datetime.now(UTC)
    today = current.astimezone(tz).date()
    training_enabled = profile is not None and profile.product_mode != ProductMode.NUTRITION
    nutrition_enabled = profile is not None and profile.product_mode != ProductMode.TRAINING
    cycle = (
        db.scalar(
            select(WorkoutCycle)
            .where(
                WorkoutCycle.user_id == user_id, WorkoutCycle.status == WorkoutCycleStatus.ACTIVE
            )
            .order_by(WorkoutCycle.start_date.desc(), WorkoutCycle.id.desc())
            .limit(1)
        )
        if training_enabled
        else None
    )
    safety = current_medical_safety_decision(db, user_id) if nutrition_enabled else None
    nutrition_blocked = (
        safety is not None and safety.outcome == SafetyOutcome.UNSUPPORTED_OR_HARD_BLOCKED
    )
    nutrition_plan = (
        db.scalar(
            select(NutritionWeeklyPlan)
            .where(
                NutritionWeeklyPlan.user_id == user_id,
                NutritionWeeklyPlan.lifecycle_status == NutritionPlanLifecycleStatus.ACTIVE,
                NutritionWeeklyPlan.started_at.is_not(None),
                NutritionWeeklyPlan.is_user_visible.is_(True),
                NutritionWeeklyPlan.start_date <= today,
            )
            .order_by(NutritionWeeklyPlan.started_at.desc(), NutritionWeeklyPlan.revision.desc())
            .limit(1)
        )
        if nutrition_enabled and not nutrition_blocked
        else None
    )
    program_start = (
        cycle.start_date if cycle else nutrition_plan.start_date if nutrition_plan else None
    )
    start, end = period_dates(preset, today, program_start)
    result = ProgressOverview(
        context=ProgressContext(
            preset=preset,
            timezone=zone,
            today=today,
            start_date=start,
            end_date=end,
            range_clipped=bool(
                preset == "current_program" and program_start and start > program_start
            ),
            goal=profile.fitness_goal.value if profile and profile.fitness_goal else None,
            product_mode=profile.product_mode.value if profile else None,
            training_enabled=training_enabled,
            nutrition_enabled=nutrition_enabled,
            current_cycle_id=cycle.id if cycle else None,
            current_program_id=cycle.workout_plan_id
            if cycle
            else nutrition_plan.id
            if nutrition_plan
            else None,
            week_number=max(1, min(cycle.duration_weeks, (today - cycle.start_date).days // 7 + 1))
            if cycle
            else None,
        )
    )
    if training_enabled:
        sessions = list(
            db.scalars(
                select(WorkoutCycleSession)
                .join(WorkoutCycle)
                .where(
                    WorkoutCycle.user_id == user_id,
                    WorkoutCycleSession.scheduled_date >= start,
                    WorkoutCycleSession.scheduled_date <= end,
                )
            )
        )
        due = [
            s
            for s in sessions
            if s.scheduled_date < today
            or (s.scheduled_date == today and s.status != WorkoutCycleSessionStatus.SCHEDULED)
        ]
        completed = sum(s.status == WorkoutCycleSessionStatus.COMPLETED for s in due)
        weeks: defaultdict[date, list[WorkoutCycleSession]] = defaultdict(list)
        for session in sessions:
            weeks[week_start(session.scheduled_date)].append(session)
        feedback = db.scalar(
            select(WorkoutCycleFeedback)
            .join(WorkoutCycle)
            .where(
                WorkoutCycle.user_id == user_id,
                WorkoutCycleFeedback.submitted_at
                >= datetime.combine(start, datetime.min.time(), tz),
                WorkoutCycleFeedback.submitted_at
                < datetime.combine(min(end, today) + timedelta(days=1), datetime.min.time(), tz),
            )
            .order_by(WorkoutCycleFeedback.submitted_at.desc())
            .limit(1)
        )
        # A legacy session may have moved out of this period. Current schedule rows
        # cannot prove that the historical reschedule count was zero.
        history_from = db.scalar(
            select(func.max(WorkoutCycleSession.reschedule_history_started_at))
            .join(WorkoutCycle)
            .where(
                WorkoutCycle.user_id == user_id,
                WorkoutCycleSession.created_at < WorkoutCycleSession.reschedule_history_started_at,
                WorkoutCycleSession.reschedule_history_started_at
                > datetime.combine(start, datetime.min.time(), tz),
            )
        )
        rescheduled = (
            db.scalar(
                select(func.count(func.distinct(WorkoutSessionRescheduleEvent.session_id)))
                .join(
                    WorkoutCycleSession,
                    WorkoutCycleSession.id == WorkoutSessionRescheduleEvent.session_id,
                )
                .join(WorkoutCycle)
                .where(
                    WorkoutCycle.user_id == user_id,
                    WorkoutSessionRescheduleEvent.is_requested.is_(True),
                    WorkoutSessionRescheduleEvent.occurred_at
                    >= datetime.combine(start, datetime.min.time(), tz),
                    WorkoutSessionRescheduleEvent.occurred_at <= current,
                )
            )
            or 0
        )
        result.training = ProgressTraining(
            rescheduled_sessions=None if history_from else rescheduled,
            reschedule_history_from=history_from,
            planned_sessions=len(sessions),
            due_sessions=len(due),
            completed_sessions=completed,
            skipped_sessions=sum(s.status == WorkoutCycleSessionStatus.SKIPPED for s in due),
            overdue_sessions=sum(s.status == WorkoutCycleSessionStatus.SCHEDULED for s in due),
            adherence_percent=round(completed * 100 / len(due), 1) if due else None,
            weeks=[
                TrainingWeek(
                    start_date=day,
                    planned=len(rows),
                    completed=sum(
                        s.status == WorkoutCycleSessionStatus.COMPLETED
                        and s.scheduled_date <= today
                        for s in rows
                    ),
                )
                for day, rows in sorted(weeks.items())
            ],
            self_reported_cycle_progress=feedback.strength_progress.value
            if feedback and feedback.strength_progress
            else None,
        )
        result.insights.append(
            ProgressInsight(code="training", values={"completed": completed, "due": len(due)})
        )
        checkins = db.scalars(
            select(WorkoutCycleWeeklyCheckIn)
            .where(
                WorkoutCycleWeeklyCheckIn.user_id == user_id,
                WorkoutCycleWeeklyCheckIn.submitted_at
                >= datetime.combine(start, datetime.min.time(), tz),
                WorkoutCycleWeeklyCheckIn.submitted_at <= current,
            )
            .order_by(WorkoutCycleWeeklyCheckIn.submitted_at, WorkoutCycleWeeklyCheckIn.id)
        )
        result.recovery = [
            RecoveryPoint(
                recorded_at=c.submitted_at,
                week_number=c.week_number,
                recovery=c.recovery_rating.value,
                difficulty=c.perceived_difficulty.value,
            )
            for c in checkins
        ]
    latest = db.execute(
        select(
            BodyPhotoSession.id, BodyPhotoSession.created_at, BodyAnalysis.id, BodyAnalysis.status
        )
        .outerjoin(BodyAnalysis, BodyAnalysis.session_id == BodyPhotoSession.id)
        .where(BodyPhotoSession.user_id == user_id)
        .order_by(BodyPhotoSession.created_at.desc(), BodyAnalysis.revision.desc())
        .limit(1)
    ).first()
    if latest:
        result.body_analysis = AnalysisSummary(
            latest_session_id=latest[0],
            latest_at=latest[1],
            latest_analysis_id=latest[2],
            latest_status=str(latest[3]) if latest[3] else None,
        )
    if nutrition_enabled:
        result.nutrition = nutrition_series(db, user_id, start, end, today, tz)
        result.insights.append(
            ProgressInsight(
                code="nutrition_tracking",
                values={
                    "logged": result.nutrition.logged_days,
                    "elapsed": result.nutrition.elapsed_days,
                },
            )
        )
    result.body_measurements = body_series(db, user_id, start, min(end, today), tz)
    return result
