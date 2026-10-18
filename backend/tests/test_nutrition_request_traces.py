"""Real API/persistence traces using existing nutrition acceptance fixtures."""

import json
import os
from pathlib import Path

from fastapi.encoders import jsonable_encoder

from app.observability.diagnostics_runtime import DiagnosticsRuntime
from app.observability.diagnostics_service import record_event
from app.observability.trace_queries import trace_detail
from tests.nutrition import test_weekly_plan_api as acceptance


def _capture(client, test_settings):
    rows = []
    client.app.state.diagnostics_runtime = DiagnosticsRuntime(
        test_settings, injected_sink=lambda event, user: rows.append((event, user))
    )
    return rows


def _nutrition_detail(db, rows):
    terminal = next(
        event
        for event, user in rows
        if event.record_type == "event"
        and event.operation == "nutrition_generation"
        and event.outcome not in {"started", "stage"}
    )
    for event, user in rows:
        if event.trace_id == terminal.trace_id:
            record_event(db, event, user_id=user)
    return trace_detail(db, terminal.trace_id)


def _evidence(name, detail):
    directory = os.environ.get("TRACE_EVIDENCE_DIR")
    if directory:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        (path / f"nutrition-{name}.json").write_text(
            json.dumps(
                jsonable_encoder(
                    {"environment": "isolated local test database; not production", **detail}
                ),
                ensure_ascii=False,
                indent=2,
            )
        )


def test_real_safety_block_is_http_201_and_business_blocked(client, db, test_settings):
    rows = _capture(client, test_settings)
    acceptance.test_safety_block_is_persisted_without_creating_a_plan(client, db)
    detail = _nutrition_detail(db, rows)
    assert detail["trace"]["http_status"] == 201
    assert detail["trace"]["outcome"] == "blocked"
    assert detail["trace"]["failure_stage"] == "medical_safety"
    assert (
        next(s for s in detail["spans"] if s["stage"] == "medical_safety")["outcome"] == "blocked"
    )
    assert (
        next(s for s in detail["spans"] if s["stage"] == "response_serialization")["outcome"]
        == "success"
    )
    _evidence("safety-blocked", detail)


def test_real_candidate_failure_keeps_construction_red_and_serialization_successful(
    client, db, test_settings, monkeypatch
):
    rows = _capture(client, test_settings)
    acceptance.test_generation_aggregates_all_candidate_failures_without_persisting_a_plan(
        client, db, monkeypatch
    )
    detail = _nutrition_detail(db, rows)
    _evidence("failure", detail)
    assert detail["trace"]["http_status"] == 201 and detail["trace"]["outcome"] == "failure"
    assert detail["trace"]["failure_stage"] == "meal_construction"
    assert (
        next(s for s in detail["spans"] if s["stage"] == "meal_construction")["outcome"]
        == "failure"
    )
    assert (
        next(s for s in detail["spans"] if s["stage"] == "response_serialization")["outcome"]
        == "success"
    )
    assert detail["summary"]["persistence"] == "unknown"
    _evidence("failure", detail)


def test_real_nutrition_success_has_verified_persistence(client, db, test_settings):
    rows = _capture(client, test_settings)
    acceptance.test_base_nutrition_activates_without_physician_review(client, db)
    detail = _nutrition_detail(db, rows)
    assert detail["trace"]["http_status"] == 201 and detail["trace"]["outcome"] == "success"
    assert detail["summary"]["persistence"] == "confirmed"
    assert any(
        span["stage"] == "transaction_commit" and span["outcome"] == "success"
        for span in detail["spans"]
    )
    _evidence("success", detail)
