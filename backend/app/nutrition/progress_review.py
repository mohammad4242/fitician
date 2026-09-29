"""Conservative review of observed progress, not a causal weight-change model."""

import json
from collections import defaultdict
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from statistics import median
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.nutrition.adherence_service import AdherenceError
from app.nutrition.calendar import effective_nutrition_plan_for_date, nutrition_pattern_day_index
from app.nutrition.enums import SafetyOutcome, WeightRateMode
from app.nutrition.estimate_service import _estimate_context, create_estimate
from app.nutrition.exceptions import (
    NutritionEstimateBlockedError,
    NutritionProductModeError,
    NutritionProfileNotFoundError,
    StructuredExerciseRequiredError,
)
from app.nutrition.models import (
    NutritionConsumptionEntry,
    NutritionDailyCheckIn,
    NutritionEstimate,
    NutritionProfile,
    NutritionTargetUpdateConsent,
)
from app.nutrition.schemas import (
    NutritionProgressConfirmationResponse,
    NutritionProgressReviewResponse,
)
from app.nutrition.scientific import (
    GoalReselectionRequiredError,
    TargetInfeasibleError,
    calculate_targets,
)
from app.nutrition.service import current_safety_decision
from app.profile.models import BodyMeasurement, UserProfile

LOSS_GOALS = {"lose_weight", "fat_loss"}
GAIN_GOALS = {"gain_weight", "build_muscle"}


def weight_rate(points: list[tuple[date, Decimal]], start: date, end: date) -> Decimal | None:
    """Compare two halves using daily medians; duplicate same-day weighings count once."""
    days: defaultdict[date, list[Decimal]] = defaultdict(list)
    for measured, weight in points:
        if start <= measured <= end and weight.is_finite() and weight > 0:
            days[measured].append(weight)
    ordered = sorted((day, Decimal(str(median(values)))) for day, values in days.items())
    if len(ordered) < 4 or (ordered[-1][0] - ordered[0][0]).days < 14:
        return None
    if (end - ordered[-1][0]).days > 7:
        return None
    midpoint = start + timedelta(days=((end - start).days + 1) // 2)
    first = [(day, weight) for day, weight in ordered if day < midpoint]
    last = [(day, weight) for day, weight in ordered if day >= midpoint]
    if len(first) < 2 or len(last) < 2:
        return None
    if max(weight for _, weight in ordered) - min(weight for _, weight in ordered) > median(
        weight for _, weight in ordered
    ) * Decimal(".1"):
        return None
    first_day = sum((Decimal(day.toordinal()) for day, _ in first), Decimal()) / len(first)
    last_day = sum((Decimal(day.toordinal()) for day, _ in last), Decimal()) / len(last)
    return (
        (
            Decimal(str(median(weight for _, weight in last)))
            - Decimal(str(median(weight for _, weight in first)))
        )
        * 7
        / (last_day - first_day)
    ).quantize(Decimal("0.001"))


def _logged_energy(rows: list[NutritionConsumptionEntry]) -> Decimal | None:
    try:
        values = [Decimal(str(row.nutrients.get("energy_kcal", 0))) for row in rows]
        if any(not value.is_finite() or value < 0 for value in values):
            return None
        return sum(values, Decimal())
    except (InvalidOperation, ValueError, TypeError):
        return None


def review_progress(
    db: Session, user_id: UUID, *, now: datetime | None = None
) -> NutritionProgressReviewResponse:
    profile = db.get(UserProfile, user_id)
    local_today = (
        (now or datetime.now(UTC))
        .astimezone(ZoneInfo(profile.timezone if profile and profile.timezone else "Asia/Tehran"))
        .date()
    )
    end = local_today - timedelta(days=1)
    plan = effective_nutrition_plan_for_date(db, user_id, local_today)
    start = (
        min(end, max(end - timedelta(days=27), plan.start_date))
        if plan
        else end - timedelta(days=27)
    )
    result = NutritionProgressReviewResponse(
        status="insufficient_data",
        start=start,
        end=end,
        plan_id=plan.id if plan else None,
        goal=profile.fitness_goal if profile else None,
    )
    if plan is None or profile is None:
        result.reason_codes = ["NO_ACTIVE_PLAN"]
        return result
    estimate = db.get(NutritionEstimate, plan.estimate_id)
    if estimate:
        energy = next(
            (target for target in estimate.targets if target.metric.value == "goal_calories"), None
        )
        result.current_calories = (
            float(energy.preferred_value) if energy and energy.preferred_value else None
        )
    checkins = db.scalars(
        select(NutritionDailyCheckIn).where(
            NutritionDailyCheckIn.user_id == user_id,
            NutritionDailyCheckIn.entry_date.between(start, end),
        )
    ).all()
    entries = db.scalars(
        select(NutritionConsumptionEntry).where(
            NutritionConsumptionEntry.user_id == user_id,
            NutritionConsumptionEntry.entry_date.between(start, end),
        )
    ).all()
    timezone = ZoneInfo(profile.timezone or "Asia/Tehran")
    measurements = db.scalars(
        select(BodyMeasurement).where(
            BodyMeasurement.user_id == user_id,
            BodyMeasurement.measured_at >= datetime.combine(start, time.min, tzinfo=timezone),
            BodyMeasurement.measured_at < datetime.combine(local_today, time.min, tzinfo=timezone),
        )
    ).all()
    weights = [(row.measured_at.astimezone(timezone).date(), row.weight_kg) for row in measurements]
    result.weighing_days = len({day for day, _ in weights})
    observed = weight_rate(weights, start, end)
    result.observed_kg_per_week = float(observed) if observed is not None else None
    valid_checkins = {row.entry_date: row for row in checkins if row.status.value != "not_recorded"}
    result.checked_in_days = len(valid_checkins)
    result.adherence_percent = (
        round(
            sum(
                1
                if row.status.value == "on_plan"
                else 0.75
                if row.status.value == "mostly_on_plan"
                else 0
                for row in valid_checkins.values()
            )
            / len(valid_checkins)
            * 100,
            1,
        )
        if valid_checkins
        else None
    )
    by_day: defaultdict[date, list[NutritionConsumptionEntry]] = defaultdict(list)
    for row in entries:
        by_day[row.entry_date].append(row)
    totals = {day: _logged_energy(rows) for day, rows in by_day.items()}
    logged = {day: value for day, value in totals.items() if value is not None and value > 0}
    result.logged_days = len(logged)
    result.average_logged_kcal = (
        round(float(sum(logged.values()) / len(logged)), 1) if logged else None
    )
    reliable = {
        day: value
        for day, value in logged.items()
        if day in valid_checkins
        and all(row.confidence.value == "high" and row.user_confirmed for row in by_day[day])
    }
    result.reliable_logged_days = len(reliable)
    near_plan = 0
    for day, actual in reliable.items():
        planned_day = next(
            (
                row
                for row in plan.days
                if row.day_index == nutrition_pattern_day_index(plan.start_date, day)
            ),
            None,
        )
        target = (
            Decimal(str(planned_day.nutrient_totals.get("energy_kcal", 0)))
            if planned_day
            else Decimal()
        )
        near_plan += int(target > 0 and Decimal(".8") <= actual / target <= Decimal("1.2"))
    safety = current_safety_decision(db, user_id)
    nutrition_profile = db.get(NutritionProfile, user_id)
    if (
        safety.outcome is not SafetyOutcome.STANDARD_AUTOMATIC
        or plan.review is not None
        or nutrition_profile is None
        or nutrition_profile.weight_rate_mode is not WeightRateMode.SAFE
    ):
        result.status = "specialist_review"
        result.reason_codes = ["SPECIALIST_TARGET_REVIEW_REQUIRED"]
        return result
    previous_consent = db.scalar(
        select(NutritionTargetUpdateConsent)
        .where(
            NutritionTargetUpdateConsent.user_id == user_id,
            NutritionTargetUpdateConsent.progress_signature.is_not(None),
        )
        .order_by(NutritionTargetUpdateConsent.confirmed_at.desc())
        .limit(1)
    )
    if previous_consent and (now or datetime.now(UTC)) - previous_consent.confirmed_at < timedelta(
        days=7
    ):
        result.status = "cooldown"
        result.reason_codes = ["WAIT_SEVEN_DAYS_AFTER_TARGET_CHANGE"]
        return result
    goal = profile.fitness_goal.value if profile.fitness_goal else ""
    if estimate is None or estimate.input_snapshot.get("fitness_goal") != goal:
        result.status = "specialist_review"
        result.reason_codes = ["PLAN_GOAL_CHANGED"]
        return result
    stored_rate = estimate.input_snapshot.get("target_weight_change_kg_per_week")
    if (
        Decimal(str(stored_rate)) if stored_rate is not None else None
    ) != nutrition_profile.target_weight_change_kg_per_week:
        result.status = "new_plan_required"
        result.reason_codes = ["START_A_PLAN_WITH_CURRENT_TARGETS"]
        return result
    if (end - start).days < 13 or observed is None or len(reliable) < 14:
        result.reason_codes = ["MORE_COMPLETE_DAYS_AND_WEIGHTS_REQUIRED"]
        return result
    if (
        result.adherence_percent is None
        or result.adherence_percent < 80
        or near_plan / len(reliable) < 0.8
    ):
        result.status = "improve_adherence"
        result.reason_codes = ["REVIEW_ADHERENCE_BEFORE_TARGETS"]
        return result
    try:
        context = _estimate_context(db, user_id)
        baseline = calculate_targets(context.inputs)
    except (
        GoalReselectionRequiredError,
        TargetInfeasibleError,
        NutritionProfileNotFoundError,
        StructuredExerciseRequiredError,
        NutritionEstimateBlockedError,
        NutritionProductModeError,
    ):
        result.status = "specialist_review"
        result.reason_codes = ["CURRENT_TARGETS_REQUIRE_REVIEW"]
        return result
    rate = (
        baseline.goal_strategy.target_weight_rate.applied_kg_per_week
        if baseline.goal_strategy
        else None
    )
    if goal not in LOSS_GOALS | GAIN_GOALS or rate is None or rate <= 0:
        result.status = "continue" if abs(observed) <= Decimal(".2") else "specialist_review"
        result.reason_codes = ["SCALE_WEIGHT_ALONE_CANNOT_ASSESS_THIS_GOAL"]
        return result
    direction = Decimal(-1 if goal in LOSS_GOALS else 1)
    result.target_kg_per_week = float(rate * direction)
    progress = observed * direction
    if rate * Decimal(".5") <= progress <= rate * Decimal("1.5"):
        result.status = "continue"
        result.reason_codes = ["TREND_ALIGNED_WITH_TARGET"]
        return result
    requested = nutrition_profile.target_weight_change_kg_per_week
    reference_rate = (
        requested
        or (
            baseline.goal_strategy.target_weight_rate.recommended_kg_per_week
            if baseline.goal_strategy
            else rate
        )
        or rate
    )
    slower_than_target = progress < rate * Decimal(".5")
    candidate_rate = reference_rate + (Decimal(".1") if slower_than_target else Decimal("-.1"))
    candidate: Decimal | None = (
        min(Decimal("2"), candidate_rate) if candidate_rate >= Decimal(".3") else None
    )
    try:
        proposed = calculate_targets(
            replace(
                context.inputs,
                requested_weight_change_kg_per_week=candidate,
                weight_rate_mode="safe",
            )
        )
    except (GoalReselectionRequiredError, TargetInfeasibleError):
        result.status = "specialist_review"
        result.reason_codes = ["PROPOSED_TARGETS_REQUIRE_REVIEW"]
        return result
    current = baseline.goal_calories.preferred
    new = proposed.goal_calories.preferred
    if (
        current is None
        or new is None
        or candidate == requested
        or (new - current) * (direction if slower_than_target else -direction) <= 0
        or abs(new - current) < 20
        or result.current_calories is None
        or abs(new - Decimal(str(result.current_calories)))
        > Decimal(str(result.current_calories)) * Decimal(".1")
    ):
        result.status = "specialist_review"
        result.reason_codes = ["EXISTING_TARGET_LIMITS_REQUIRE_REVIEW"]
        return result
    result.status = "adjustment_available"
    result.proposed_rate_kg_per_week = float(candidate) if candidate is not None else None
    result.proposed_calories = float(new)
    result.can_confirm = True
    result.reason_codes = ["SMALL_SAFE_RATE_ADJUSTMENT", "OBSERVED_SCALE_TREND_NOT_CAUSAL"]
    evidence = {
        "review": result.model_dump(mode="json"),
        "context": context.snapshot,
        "requested_rate": str(requested),
        "checkins": sorted(
            (str(row.id), str(row.updated_at), row.status.value, str(row.plan_revision_id))
            for row in checkins
        ),
        "entries": sorted(
            (
                str(row.id),
                str(row.updated_at),
                row.nutrients,
                row.confidence.value,
                row.user_confirmed,
            )
            for row in entries
        ),
        "weights": sorted(
            (str(row.id), str(row.measured_at), str(row.weight_kg)) for row in measurements
        ),
    }
    result.signature = sha256(
        json.dumps(evidence, sort_keys=True, default=str).encode()
    ).hexdigest()
    return result


def confirm_progress(
    db: Session, user_id: UUID, expected_plan_id: UUID, signature: str, confirmed: bool
) -> NutritionProgressConfirmationResponse:
    if not confirmed:
        raise AdherenceError("TARGET_UPDATE_CONFIRMATION_REQUIRED")
    db.scalar(select(UserProfile).where(UserProfile.user_id == user_id).with_for_update())
    existing = db.scalar(
        select(NutritionTargetUpdateConsent).where(
            NutritionTargetUpdateConsent.user_id == user_id,
            NutritionTargetUpdateConsent.progress_signature == signature,
        )
    )
    if existing and existing.estimate_id:
        if (existing.progress_snapshot or {}).get("plan_id") != str(expected_plan_id):
            raise AdherenceError("PROGRESS_REVIEW_STALE_OR_UNAVAILABLE")
        return NutritionProgressConfirmationResponse(
            estimate_id=existing.estimate_id,
            targets_updated=True,
            needs_new_plan=True,
            user_confirmed=True,
        )
    nutrition_profile = db.scalar(
        select(NutritionProfile).where(NutritionProfile.user_id == user_id).with_for_update()
    )
    review = review_progress(db, user_id)
    if (
        not review.can_confirm
        or review.signature != signature
        or review.plan_id != expected_plan_id
    ):
        raise AdherenceError("PROGRESS_REVIEW_STALE_OR_UNAVAILABLE")
    assert nutrition_profile is not None and review.goal is not None
    previous_rate = nutrition_profile.target_weight_change_kg_per_week
    try:
        nutrition_profile.target_weight_change_kg_per_week = (
            Decimal(str(review.proposed_rate_kg_per_week))
            if review.proposed_rate_kg_per_week is not None
            else None
        )
        audit = NutritionTargetUpdateConsent(
            user_id=user_id,
            previous_goal=review.goal.value,
            requested_goal=review.goal.value,
            reason_codes=["USER_CONFIRMED_PROGRESS_REVIEW"],
            confirmed_at=datetime.now(UTC),
            progress_signature=signature,
            progress_snapshot={
                **review.model_dump(mode="json"),
                "previous_requested_rate": str(previous_rate)
                if previous_rate is not None
                else None,
            },
        )
        db.add(audit)
        estimate = create_estimate(db, user_id, commit=False)
        audit.estimate_id = estimate.id
        db.commit()
    except Exception:
        db.rollback()
        raise
    return NutritionProgressConfirmationResponse(
        estimate_id=estimate.id, targets_updated=True, needs_new_plan=True, user_confirmed=True
    )
