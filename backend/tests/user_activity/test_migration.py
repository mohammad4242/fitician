"""Exercise the concurrent index migration on the guarded test database, outside a savepoint."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

from tests.conftest import TEST_DATABASE_URL


def test_activity_migration_round_trip(migrated_database) -> None:
    assert make_url(TEST_DATABASE_URL).database == "fitician_test"
    backend = Path(__file__).resolve().parents[2]
    engine = create_engine(TEST_DATABASE_URL)
    environment = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}

    def migrate(*args: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=backend,
            env=environment,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    try:
        migrate("downgrade", "20261007_171")
        assert "user_activity_events" not in inspect(engine).get_table_names()
        assert "ix_users_created_at" not in {
            index["name"] for index in inspect(engine).get_indexes("users")
        }
        migrate("upgrade", "head")
        inspector = inspect(engine)
        assert {
            "ix_user_activity_events_user_id_occurred_at",
            "ix_user_activity_events_event_type_occurred_at",
            "ix_user_activity_events_user_resource",
        } <= {index["name"] for index in inspector.get_indexes("user_activity_events")}
        assert "ix_users_created_at" in {index["name"] for index in inspector.get_indexes("users")}
        assert (
            inspector.get_foreign_keys("user_activity_events")[0]["options"]["ondelete"]
            == "CASCADE"
        )
    finally:
        migrate("upgrade", "head")
        engine.dispose()
