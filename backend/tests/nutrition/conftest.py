from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.audit_nutrition_engine_100_profiles import DEFAULT_DB_URL
from tests.database_lifecycle import (
    ensure_database_exists,
    hold_database_lock,
    reset_public_schema,
    upgrade_database,
)

NUTRITION_AUDIT_DATABASE_NAME = "fitsho_nutrition_audit"


@pytest.fixture(scope="session", autouse=True)
def prepared_nutrition_audit_database() -> Iterator[None]:
    ensure_database_exists(
        DEFAULT_DB_URL,
        expected_database=NUTRITION_AUDIT_DATABASE_NAME,
    )
    with hold_database_lock(
        DEFAULT_DB_URL,
        expected_database=NUTRITION_AUDIT_DATABASE_NAME,
    ):
        reset_public_schema(
            DEFAULT_DB_URL,
            expected_database=NUTRITION_AUDIT_DATABASE_NAME,
        )
        upgrade_database(
            DEFAULT_DB_URL,
            expected_database=NUTRITION_AUDIT_DATABASE_NAME,
        )
        environment = {**os.environ, "DATABASE_URL": DEFAULT_DB_URL}
        subprocess.run(
            [sys.executable, "-m", "scripts.seed_nutrition_benchmark"],
            check=True,
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
        )
        yield
