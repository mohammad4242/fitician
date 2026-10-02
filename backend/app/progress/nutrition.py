from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, load_only

from app.nutrition.adherence_policy import CALORIE_ALIGNMENT_LOWER, CALORIE_ALIGNMENT_UPPER
from app.nutrition.calendar import nutrition_pattern_day_index
from app.nutrition.enums import SafetyOutcome
from app.nutrition.medical_context import current_medical_safety_decision
from app.nutrition.models import (
    NutritionConsumptionEntry,
    NutritionDailyCheckIn,
    NutritionPlanLifecycleEvent,
    NutritionWeeklyPlan,
    NutritionWeeklyPlanDay,
)
from app.progress.schemas import CaloriePoint, ProgressNutrition


def energy(value: object) -> Decimal | None:
    try:
        number = Decimal(str(value))
        return number if number.is_finite() and number >= 0 else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def nutrition_series(
    db: Session, user_id: UUID, start: date, end: date, today: date, zone: ZoneInfo
) -> ProgressNutrition:
    entries = db.scalars(
        select(NutritionConsumptionEntry)
        .options(
            load_only(
                NutritionConsumptionEntry.entry_date,
                NutritionConsumptionEntry.plan_revision_id,
                NutritionConsumptionEntry.nutrients,
                NutritionConsumptionEntry.confidence,
                NutritionConsumptionEntry.user_confirmed,
            )
        )
        .where(
            NutritionConsumptionEntry.user_id == user_id,
            NutritionConsumptionEntry.entry_date >= start,
            NutritionConsumptionEntry.entry_date <= min(end, today),
        )
    ).all()
    by_day: defaultdict[date, list[NutritionConsumptionEntry]] = defaultdict(list)
    for entry in entries:
        by_day[entry.entry_date].append(entry)
    checkins = {
        c.entry_date: c
        for c in db.scalars(
            select(NutritionDailyCheckIn)
            .options(
                load_only(
                    NutritionDailyCheckIn.entry_date,
                    NutritionDailyCheckIn.plan_revision_id,
                    NutritionDailyCheckIn.status,
                )
            )
            .where(
                NutritionDailyCheckIn.user_id == user_id,
                NutritionDailyCheckIn.entry_date >= start,
                NutritionDailyCheckIn.entry_date <= min(end, today),
            )
        )
    }
    # One latest pre-range observation per plan + in-range transitions, no per-day queries.
    from sqlalchemy import func

    baseline = (
        select(
            NutritionPlanLifecycleEvent.id,
            func.row_number()
            .over(
                partition_by=NutritionPlanLifecycleEvent.plan_id,
                order_by=(
                    NutritionPlanLifecycleEvent.occurred_at.desc(),
                    NutritionPlanLifecycleEvent.id.desc(),
                ),
            )
            .label("rank"),
        )
        .where(
            NutritionPlanLifecycleEvent.user_id == user_id,
            NutritionPlanLifecycleEvent.effective_on < start,
        )
        .subquery()
    )
    events = list(
        db.scalars(
            select(NutritionPlanLifecycleEvent)
            .where(
                NutritionPlanLifecycleEvent.user_id == user_id,
                (
                    NutritionPlanLifecycleEvent.id.in_(
                        select(baseline.c.id).where(baseline.c.rank == 1)
                    )
                )
                | (
                    (NutritionPlanLifecycleEvent.effective_on >= start)
                    & (NutritionPlanLifecycleEvent.effective_on <= end)
                ),
            )
            .order_by(
                NutritionPlanLifecycleEvent.effective_on,
                NutritionPlanLifecycleEvent.occurred_at,
                NutritionPlanLifecycleEvent.id,
            )
        )
    )
    ids = (
        {e.plan_id for e in events}
        | {c.plan_revision_id for c in checkins.values() if c.plan_revision_id}
        | {e.plan_revision_id for e in entries if e.plan_revision_id}
    )
    plans = {
        p.id: p
        for p in db.scalars(
            select(NutritionWeeklyPlan)
            .options(
                load_only(
                    NutritionWeeklyPlan.id,
                    NutritionWeeklyPlan.start_date,
                    NutritionWeeklyPlan.revision,
                )
            )
            .where(NutritionWeeklyPlan.user_id == user_id, NutritionWeeklyPlan.id.in_(ids))
        )
    }
    targets = {
        (p.plan_id, p.day_index): energy(p.nutrient_totals.get("energy_kcal"))
        for p in db.scalars(
            select(NutritionWeeklyPlanDay)
            .options(
                load_only(
                    NutritionWeeklyPlanDay.plan_id,
                    NutritionWeeklyPlanDay.day_index,
                    NutritionWeeklyPlanDay.nutrient_totals,
                )
            )
            .where(NutritionWeeklyPlanDay.plan_id.in_(plans))
        )
    }
    decision = current_medical_safety_decision(db, user_id)
    blocked = decision is not None and decision.outcome == SafetyOutcome.UNSUPPORTED_OR_HARD_BLOCKED
    series = []
    state: dict[UUID, NutritionPlanLifecycleEvent] = {}
    index = 0
    day = start
    while day <= end:
        while index < len(events) and events[index].effective_on <= day:
            state[events[index].plan_id] = events[index]
            index += 1
        candidates = [
            e
            for e in state.values()
            if e.lifecycle_status == "active"
            and e.is_user_visible
            and e.start_date <= day
            and e.plan_id in plans
        ]
        selected = max(
            candidates,
            key=lambda e: (e.start_date, e.occurred_at, plans[e.plan_id].revision),
            default=None,
        )
        plan_id = selected.plan_id if selected else None
        source = "lifecycle_history" if selected else None
        start_date = selected.start_date if selected else None
        rows = by_day[day]
        checkin = checkins.get(day)
        refs = {r.plan_revision_id for r in rows if r.plan_revision_id}
        # Legacy references are evidence for this date only, never today's plan.
        pinned = (
            checkin.plan_revision_id if checkin else next(iter(refs)) if len(refs) == 1 else None
        )
        if (
            not selected
            and pinned in plans
            and pinned not in state
            and (not refs or refs == {pinned})
        ):
            plan_id = pinned
            start_date = plans[pinned].start_date
            source = "recorded_plan_reference"
        target = (
            targets.get((plan_id, nutrition_pattern_day_index(start_date, day)))
            if plan_id and start_date
            else None
        )
        if blocked:
            target = None
            plan_id = None
            source = None
        values = [energy(row.nutrients.get("energy_kcal")) for row in rows]
        actual = (
            sum((v for v in values if v is not None), Decimal())
            if rows and all(v is not None for v in values)
            else None
        )
        reliable = bool(
            actual is not None
            and checkin
            and str(checkin.status) != "not_recorded"
            and all(str(r.confidence) == "high" and r.user_confirmed for r in rows)
        )
        comparable = bool(reliable and day < today and target is not None and target > 0)
        near = (
            bool(CALORIE_ALIGNMENT_LOWER <= actual / target <= CALORIE_ALIGNMENT_UPPER)
            if comparable and actual is not None and target is not None
            else None
        )
        series.append(
            CaloriePoint(
                date=day,
                target_kcal=float(target) if target is not None else None,
                actual_kcal=float(actual) if actual is not None else None,
                target_plan_id=plan_id,
                target_revision=plans[plan_id].revision if plan_id else None,
                target_source=source,
                logging_state="recorded"
                if actual is not None
                else "invalid"
                if rows
                else "missing",
                reliable=reliable,
                in_progress=day == today,
                near_target=near,
            )
        )
        day += timedelta(days=1)
    past = [p for p in series if p.date < today]
    logged = [p for p in past if p.actual_kcal is not None]
    comparable_points = [p for p in past if p.near_target is not None]
    adherent = sum(p.near_target is True for p in comparable_points)

    def average(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 1) if values else None

    return ProgressNutrition(
        series=series,
        days_in_range=len(series),
        elapsed_days=len(past),
        logged_days=len(logged),
        reliable_logged_days=sum(p.reliable for p in logged),
        comparable_days=len(comparable_points),
        adherent_days=adherent,
        adherence_percent=round(adherent * 100 / len(comparable_points), 1)
        if comparable_points
        else None,
        average_target_kcal=average(
            [p.target_kcal for p in comparable_points if p.target_kcal is not None]
        ),
        average_actual_kcal=average([p.actual_kcal for p in logged if p.actual_kcal is not None]),
        average_difference_kcal=average(
            [
                p.actual_kcal - p.target_kcal
                for p in comparable_points
                if p.actual_kcal is not None and p.target_kcal is not None
            ]
        ),
    )
