from sqlalchemy import event

from app.progress.service import overview
from tests.nutrition.test_progress_review_api import _plan


def test_overview_queries_are_bounded_and_exclude_plan_snapshots(client, db):
    plan = _plan(client, db)
    owner = plan.user_id
    db.flush()
    db.expire_all()
    statements = []
    connection = db.connection()

    def collect(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", collect)
    try:
        result = overview(db, owner, preset="four_weeks", timezone="UTC")
    finally:
        event.remove(connection, "before_cursor_execute", collect)
    assert len(result.nutrition.series) == 28
    assert len(statements) <= 20
    assert not any("nutrition_weekly_plans.input_snapshot" in sql for sql in statements)
    assert not any("nutrition_weekly_plans.repair_snapshot" in sql for sql in statements)
    assert not any("nutrition_consumption_entries.notes" in sql for sql in statements)
