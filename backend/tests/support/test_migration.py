from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect

from app.database.base import Base


def test_support_schema_matches_models_and_round_trips(db, monkeypatch):
    connection = db.connection()
    transaction = connection.begin_nested()
    try:
        path = (
            Path(__file__).resolve().parents[2] / "alembic/versions/20261002_166_support_tickets.py"
        )
        spec = spec_from_file_location("support_migration", path)
        migration = module_from_spec(spec)
        spec.loader.exec_module(migration)
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.downgrade()
        assert "support_tickets" not in inspect(connection).get_table_names()
        migration.upgrade()
        tables = {
            "support_tickets",
            "support_messages",
            "support_message_reads",
            "support_status_events",
        }
        assert tables <= set(inspect(connection).get_table_names())
        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda obj, name, type_, reflected, compare_to: (
                    type_ != "table" or name in tables
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []
    finally:
        transaction.rollback()
