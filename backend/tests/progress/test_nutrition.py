from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.nutrition.models import (
    NutritionConsumptionEntry,
    NutritionDailyCheckIn,
)
from app.progress.service import overview
from tests.nutrition.test_progress_review_api import _plan


def test_missing_and_single_logged_day_are_truthful(client, db):
    plan = _plan(client, db)
    result = overview(db, plan.user_id, preset="week", timezone="UTC")
    assert all(p.actual_kcal is None for p in result.nutrition.series)
    assert result.nutrition.logged_days == 0
    assert result.nutrition.adherence_percent is None
    yesterday = result.context.today - timedelta(days=1)
    planned = plan.days[(yesterday - plan.start_date).days % 7]
    target = Decimal(str(planned.nutrient_totals["energy_kcal"]))
    db.add(
        NutritionDailyCheckIn(
            user_id=plan.user_id, entry_date=yesterday, status="on_plan", plan_revision_id=plan.id
        )
    )
    db.add(
        NutritionConsumptionEntry(
            user_id=plan.user_id,
            entry_date=yesterday,
            plan_revision_id=plan.id,
            display_name="Recorded",
            source="planned_confirmed",
            confidence="high",
            user_confirmed=True,
            nutrients={"energy_kcal": float(target)},
            warning_codes=[],
        )
    )
    db.flush()
    result = overview(db, plan.user_id, preset="four_weeks", timezone="UTC")
    point = next(p for p in result.nutrition.series if p.date == yesterday)
    assert point.target_kcal == float(target)
    assert point.actual_kcal == float(target)
    assert result.nutrition.logged_days == 1
    assert result.nutrition.comparable_days == 1
    assert result.nutrition.adherent_days == 1
    assert result.nutrition.average_difference_kcal == 0
    assert result.nutrition.adherence_percent == 100
    assert result.nutrition.complete_day_intake_verified is False


def test_lifecycle_cannot_apply_current_target_retroactively(client, db):
    from zoneinfo import ZoneInfo

    from app.nutrition.lifecycle_history import record_lifecycle
    from app.progress.nutrition import nutrition_series

    plan = _plan(client, db)
    # Explicit snapshots model an activation followed by an archive. No duplicated targets.
    first = datetime(2026, 9, 10, 12, tzinfo=UTC)
    plan.start_date = first.date()
    plan.started_at = first
    record_lifecycle(db, plan, now=first)
    plan.lifecycle_status = "archived"
    record_lifecycle(db, plan, now=first + timedelta(days=5))
    db.flush()
    summary = nutrition_series(
        db,
        plan.user_id,
        first.date(),
        first.date() + timedelta(days=7),
        first.date() + timedelta(days=8),
        ZoneInfo("UTC"),
    )
    assert summary.series[0].target_plan_id == plan.id
    assert summary.series[4].target_kcal is not None
    assert summary.series[5].target_kcal is None
    assert summary.series[0].actual_kcal is None


def test_plan_revisions_full_week_missing_invalid_and_timezone(client, db):
    from zoneinfo import ZoneInfo

    from sqlalchemy import inspect

    from app.nutrition.lifecycle_history import record_lifecycle
    from app.nutrition.models import (
        NutritionPlanGeneration,
        NutritionWeeklyPlan,
        NutritionWeeklyPlanDay,
    )
    from app.progress.nutrition import nutrition_series

    plan = _plan(client, db)
    start = datetime(2026, 9, 26, 23, 30, tzinfo=UTC)
    plan.start_date = start.date()
    plan.started_at = start
    record_lifecycle(db, plan, now=start)
    generation = db.get(NutritionPlanGeneration, plan.generation_id)
    values = {
        a.key: getattr(generation, a.key) for a in inspect(NutritionPlanGeneration).column_attrs
    }
    values.update(id=uuid4(), bundle_id=None)
    copied = NutritionPlanGeneration(**values)
    db.add(copied)
    db.flush()
    values = {a.key: getattr(plan, a.key) for a in inspect(NutritionWeeklyPlan).column_attrs}
    values.update(
        id=uuid4(),
        generation_id=copied.id,
        revision=plan.revision + 1,
        started_at=start + timedelta(days=3),
        supersedes_plan_id=plan.id,
    )
    revised = NutritionWeeklyPlan(**values)
    revised.days = [
        NutritionWeeklyPlanDay(
            day_index=i,
            plan_date=start.date() + timedelta(days=i),
            cost_irr=0,
            nutrient_totals={"energy_kcal": 2000},
        )
        for i in range(7)
    ]
    db.add(revised)
    record_lifecycle(db, revised, now=start + timedelta(days=3))
    db.flush()
    for i in range(7):
        day = start.date() + timedelta(days=i)
        db.add(
            NutritionDailyCheckIn(
                user_id=plan.user_id,
                entry_date=day,
                status="on_plan",
                plan_revision_id=plan.id if i < 3 else revised.id,
            )
        )
        if i == 1:
            continue  # missing means null, never zero
        db.add(
            NutritionConsumptionEntry(
                user_id=plan.user_id,
                entry_date=day,
                plan_revision_id=plan.id if i < 3 else revised.id,
                display_name="Recorded",
                source="catalogue_manual",
                confidence="high",
                user_confirmed=True,
                nutrients={} if i == 2 else {"energy_kcal": 2000},
                warning_codes=[],
            )
        )
    db.flush()
    summary = nutrition_series(
        db,
        plan.user_id,
        start.date(),
        start.date() + timedelta(days=6),
        start.date() + timedelta(days=6),
        ZoneInfo("UTC"),
    )
    assert summary.series[0].target_revision == plan.revision
    assert summary.series[2].target_revision == plan.revision
    assert summary.series[3].target_revision == revised.revision
    assert summary.series[3].target_kcal == 2000
    assert summary.series[1].actual_kcal is None
    assert summary.series[2].actual_kcal is None and summary.series[2].logging_state == "invalid"
    assert summary.elapsed_days == 6 and summary.logged_days == 4
    assert summary.comparable_days == 4
    assert summary.adherence_percent == summary.adherent_days / summary.comparable_days * 100
    assert summary.series[-1].in_progress and summary.series[-1].near_target is None
    # Events keep the member's local effective date, independent of query timezone.
    from app.nutrition.models import NutritionPlanLifecycleEvent
    from app.profile.models import UserProfile

    db.get(UserProfile, plan.user_id).timezone = "Asia/Tehran"
    record_lifecycle(db, revised, now=start + timedelta(days=3))
    db.flush()
    history = list(
        db.scalars(
            select(NutritionPlanLifecycleEvent).where(
                NutritionPlanLifecycleEvent.plan_id == revised.id
            )
        )
    )
    assert any(e.effective_on == (start + timedelta(days=4)).date() for e in history)


def test_medical_block_hides_plan_context_and_historical_targets(client, db, monkeypatch):
    from types import SimpleNamespace

    from app.nutrition.enums import SafetyOutcome

    plan = _plan(client, db)
    decision = SimpleNamespace(outcome=SafetyOutcome.UNSUPPORTED_OR_HARD_BLOCKED)
    monkeypatch.setattr("app.progress.service.current_medical_safety_decision", lambda *_: decision)
    monkeypatch.setattr(
        "app.progress.nutrition.current_medical_safety_decision", lambda *_: decision
    )
    result = overview(db, plan.user_id, preset="week", timezone="UTC")
    assert result.context.current_program_id is None
    assert all(p.target_kcal is None and p.target_plan_id is None for p in result.nutrition.series)
