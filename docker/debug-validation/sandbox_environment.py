"""Minimal child environment; only fixed synthetic databases can cross this boundary."""

from collections.abc import Mapping
from pathlib import Path


def child_environment(workspace: Path, executable_path: str, source: Mapping[str, str]) -> dict[str, str]:
    environment = {
        "PATH": executable_path,
        "HOME": "/scratch",
        "TMPDIR": "/scratch",
        "APP_ENV": "test",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SENTRY_DSN": "",
        "SENTRY_TRACES_SAMPLE_RATE": "0",
        "PYTHONPATH": str(workspace),
        "XDG_CACHE_HOME": "/scratch/cache",
        "MPLCONFIGDIR": "/scratch/matplotlib",
    }
    prefix = "postgresql+psycopg://fitician:fitician_ci@db:5432/"
    for key, database in (
        ("DATABASE_URL", "fitician_test"),
        ("TEST_DATABASE_URL", "fitician_test"),
        ("NUTRITION_AUDIT_DATABASE_URL", "fitician_nutrition_audit"),
    ):
        if key in source:
            if source[key] != prefix + database:
                raise ValueError("isolated_database_required")
            environment[key] = source[key]
    return environment
