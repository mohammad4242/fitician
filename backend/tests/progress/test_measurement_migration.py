from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect

from app.database.base import Base


def test_measurement_schema_round_trip(db, monkeypatch):
    connection = db.connection()
    transaction = connection.begin_nested()
    try:
        path = (
            Path(__file__).resolve().parents[2]
            / "alembic/versions/20261002_167_measurement_observations.py"
        )
        spec = spec_from_file_location("measurements_migration", path)
        migration = module_from_spec(spec)
        spec.loader.exec_module(migration)
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.downgrade()
        assert "shoulder_width_cm" not in {
            c["name"] for c in inspect(connection).get_columns("body_measurements")
        }
        migration.upgrade()
        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda obj, name, type_, reflected, compare_to: (
                    type_ != "table" or name == "body_measurements"
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []
    finally:
        transaction.rollback()
