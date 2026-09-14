"""Prepare the isolated PostgreSQL database used by Playwright E2E tests."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATABASE_NAME_PATTERN = re.compile(r"[A-Za-z0-9_]+_e2e\Z")


def _validated_database_url() -> tuple[str, URL, str]:
    raw_url = os.environ.get("E2E_DATABASE_URL", "").strip()
    if not raw_url:
        raise RuntimeError("E2E_DATABASE_URL is required")
    url = make_url(raw_url)
    database = url.database or ""
    if url.get_backend_name() != "postgresql":
        raise RuntimeError("E2E_DATABASE_URL must use PostgreSQL")
    if not DATABASE_NAME_PATTERN.fullmatch(database):
        raise RuntimeError("E2E_DATABASE_URL database must end with _e2e")
    if database in {"postgres", "template0", "template1"}:
        raise RuntimeError("E2E database cannot be a PostgreSQL system database")
    return raw_url, url, database


def _ensure_database(url: URL, database: str) -> None:
    maintenance_engine = create_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )
    try:
        with maintenance_engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :database"),
                {"database": database},
            )
            if exists is None:
                connection.exec_driver_sql(f'CREATE DATABASE "{database}"')
    finally:
        maintenance_engine.dispose()


def _reset_schema(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
            connection.exec_driver_sql("CREATE SCHEMA public")
    finally:
        engine.dispose()


def _run_migrations(database_url: str) -> None:
    environment = {**os.environ, "DATABASE_URL": database_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=environment,
        check=True,
    )


def _seed_catalogues(database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url

    # Import the application before opening a session so every model relationship is registered.
    import app.main  # noqa: F401
    from app.database.session import get_engine
    from app.exercises.service import seed_exercises
    from app.training_templates.service import seed_training_program_templates
    from scripts.seed_benchmark_catalog import seed_benchmark_catalog
    from scripts.seed_nutrition_benchmark import seed_nutrition_benchmark

    with Session(get_engine(database_url)) as db:
        seed_exercises(db)
        seed_benchmark_catalog(db)
        seed_training_program_templates(db)
        seed_nutrition_benchmark(db)


def main() -> None:
    database_url, parsed_url, database = _validated_database_url()
    _ensure_database(parsed_url, database)
    _reset_schema(database_url)
    _run_migrations(database_url)
    _seed_catalogues(database_url)
    print(f"Prepared isolated E2E database: {database}")


if __name__ == "__main__":
    main()
