from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect

from app.database.base import Base


def test_reschedule_schema_round_trip(db, monkeypatch):
    connection = db.connection()
    transaction = connection.begin_nested()
    try:
        path = (
            Path(__file__).resolve().parents[2]
            / "alembic/versions/20261002_169_session_reschedule_history.py"
        )
        spec = spec_from_file_location("reschedule_migration", path)
        migration = module_from_spec(spec)
        spec.loader.exec_module(migration)
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.downgrade()
        assert "workout_session_reschedule_events" not in inspect(connection).get_table_names()
        migration.upgrade()
        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda obj, name, type_, reflected, compare_to: (
                    (
                        type_ != "table"
                        or name in {"workout_session_reschedule_events", "workout_cycle_sessions"}
                    )
                    and (
                        type_ != "column"
                        or obj.table.name != "workout_cycle_sessions"
                        or name == "reschedule_history_started_at"
                    )
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []
    finally:
        transaction.rollback()
