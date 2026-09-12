from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
_ALLOWED_DATABASE_NAMES = frozenset(("fitsho_test", "fitsho_nutrition_audit"))
_DATABASE_LOCK_KEYS = {
    "fitsho_test": 58421901,
    "fitsho_nutrition_audit": 58421902,
}


def _validated_database_url(database_url: str, *, expected_database: str) -> URL:
    url = make_url(database_url)
    if (
        expected_database not in _ALLOWED_DATABASE_NAMES
        or url.get_backend_name() != "postgresql"
        or url.database != expected_database
    ):
        raise RuntimeError(
            "Refusing test database lifecycle operation: "
            f"expected PostgreSQL database {expected_database!r}, got {url.database!r}"
        )
    return url


def ensure_database_exists(database_url: str, *, expected_database: str) -> None:
    url = _validated_database_url(database_url, expected_database=expected_database)
    maintenance_engine = create_engine(url.set(database="postgres"))
    try:
        with maintenance_engine.connect() as connection:
            autocommit_connection = connection.execution_options(isolation_level="AUTOCOMMIT")
            exists = autocommit_connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": expected_database},
            ).scalar()
            if exists is None:
                autocommit_connection.exec_driver_sql(f'CREATE DATABASE "{expected_database}"')
    finally:
        maintenance_engine.dispose()


@contextmanager
def hold_database_lock(database_url: str, *, expected_database: str) -> Iterator[None]:
    url = _validated_database_url(database_url, expected_database=expected_database)
    lock_key = _DATABASE_LOCK_KEYS[expected_database]
    engine = create_engine(url)
    connection = engine.connect()
    locked = False
    try:
        connection.execute(
            text("SELECT pg_advisory_lock(:lock_key)"),
            {"lock_key": lock_key},
        )
        connection.commit()
        locked = True
        yield
    finally:
        if locked:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_key)"),
                {"lock_key": lock_key},
            )
            connection.commit()
        connection.close()
        engine.dispose()


def reset_public_schema(database_url: str, *, expected_database: str) -> None:
    url = _validated_database_url(database_url, expected_database=expected_database)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            autocommit_connection = connection.execution_options(isolation_level="AUTOCOMMIT")
            autocommit_connection.exec_driver_sql("DROP SCHEMA public CASCADE")
            autocommit_connection.exec_driver_sql("CREATE SCHEMA public")
    finally:
        engine.dispose()


def upgrade_database(database_url: str, *, expected_database: str) -> None:
    _validated_database_url(database_url, expected_database=expected_database)
    environment = {**os.environ, "DATABASE_URL": database_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        cwd=BACKEND_DIR,
        env=environment,
    )
