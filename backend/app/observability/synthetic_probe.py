"""Operator-only synthetic capture; no route, user fixture or business mutation."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from .diagnostics_schemas import EventInput
from .diagnostics_service import record_event
from .environment import diagnostics_environment
from .evidence import attach_exception
from .sentry import flush_sentry, initialize_sentry


def raise_synthetic_failure() -> None:
    raise RuntimeError("FITICIAN_DIAGNOSTIC_SYNTHETIC_FAILURE")


def record_synthetic_failure(db: Session, build: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{40}", build):
        raise ValueError("exact_release_commit_required")
    configured = initialize_sentry("backend")
    event = EventInput(
        event_id=uuid4(),
        component="diagnostics",
        operation="sentry_verification",
        stage="synthetic_probe",
        platform="backend",
        category="infrastructure_failure",
        severity="error",
        error_code="DIAGNOSTIC_SYNTHETIC_FAILURE",
        outcome="failure",
        build=build,
    )
    try:
        raise_synthetic_failure()
    except RuntimeError as error:
        event = attach_exception(event, error)
    row = record_event(db, event)
    flush_sentry()
    return {
        "event_id": str(row.id),
        "issue_id": str(row.issue_id),
        "sentry_event_id": event.sentry_event_id,
        "build": build,
        "environment": diagnostics_environment(),
        "delivery": "unconfirmed" if configured else "not_configured",
    }


def main() -> None:
    from app.config import get_settings
    from app.database.session import get_engine

    settings = get_settings()
    if not os.environ.get("SENTRY_DSN"):
        raise SystemExit("Sentry DSN is not configured; no synthetic event was created")
    with Session(get_engine(settings)) as db:
        result = record_synthetic_failure(db, os.environ.get("APP_BUILD_SHA", ""))
        db.commit()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
