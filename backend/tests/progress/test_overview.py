from datetime import UTC, date, datetime

import pytest

from app.profile.enums import ProductMode
from app.profile.models import UserProfile
from app.progress.service import overview, period_dates
from tests.workout_cycles.test_session_service import begin_cycle, make_plan, make_profile
from tests.workout_reviews.test_review_access import _login, _user


def test_periods_and_timezone_boundaries():
    assert period_dates("week", date(2026, 10, 2), None) == (date(2026, 9, 26), date(2026, 10, 2))
    assert period_dates("four_weeks", date(2026, 10, 2), None)[0] == date(2026, 9, 5)


@pytest.mark.parametrize("mode", list(ProductMode))
def test_empty_overview_product_modes(db, mode):
    user = _user(db)
    make_profile(db, user.id)
    db.get(UserProfile, user.id).product_mode = mode
    result = overview(
        db, user.id, preset="week", timezone="UTC", now=datetime(2026, 10, 2, tzinfo=UTC)
    )
    assert (result.training is not None) == (mode != ProductMode.NUTRITION)
    assert result.context.nutrition_enabled == (mode != ProductMode.TRAINING)
    assert result.recovery == []
    if result.training:
        assert result.training.adherence_percent is None


def test_training_denominator_excludes_today_pending_and_future(db):
    from app.workout_cycles.enums import WorkoutCycleSessionStatus

    user = _user(db)
    make_profile(db, user.id)
    cycle = begin_cycle(db, user.id, make_plan(db, user.id, weekdays=(0, 2, 4)), date(2026, 9, 26))
    sessions = sorted(cycle.sessions, key=lambda x: x.scheduled_date)
    today = sessions[2].scheduled_date
    sessions[0].status = WorkoutCycleSessionStatus.COMPLETED
    sessions[0].completed_at = datetime.combine(
        sessions[0].scheduled_date, datetime.min.time(), UTC
    )
    sessions[1].status = WorkoutCycleSessionStatus.SKIPPED
    sessions[1].skipped_at = datetime.combine(sessions[1].scheduled_date, datetime.min.time(), UTC)
    db.flush()
    result = overview(
        db,
        user.id,
        preset="current_program",
        timezone="UTC",
        now=datetime.combine(today, datetime.min.time(), UTC),
    )
    assert result.training.due_sessions == 2
    assert result.training.completed_sessions == 1
    assert result.training.skipped_sessions == 1
    assert result.training.adherence_percent == 50
    assert result.training.overdue_sessions == 0
    assert result.context.week_number == 1


def test_api_authentication_owner_scope_and_timezone(client, db, test_settings):
    first = _user(db)
    make_profile(db, first.id)
    _login(client, db, test_settings, first)
    response = client.get("/api/v1/progress/overview?timezone=invalid")
    assert response.status_code == 422
    other = _user(db)
    _login(client, db, test_settings, other)
    payload = client.get("/api/v1/progress/overview").json()
    assert payload["context"]["goal"] is None
    assert payload["training"] is None
    assert "user_id" not in payload
    client.cookies.clear()
    assert client.get("/api/v1/progress/overview").status_code == 401
