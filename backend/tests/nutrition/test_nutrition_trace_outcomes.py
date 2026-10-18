from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Request, Response
from starlette.datastructures import Headers

import app.main  # noqa: F401  # Register all SQLAlchemy models before mapped instances are created.
import app.nutrition.plan_service as plan_service
from app.config import Settings
from app.nutrition.enums import NutritionPlanGenerationOutcome, SafetyOutcome
from app.observability.diagnostics_runtime import DiagnosticsRuntime, diagnostics_middleware


class _PersistRecorder:
    def __init__(self) -> None:
        self.committed = False
        self.row: object | None = None

    def add(self, row: object) -> None:
        self.row = row

    def commit(self) -> None:
        self.committed = True
        if self.row is not None and getattr(self.row, "id", None) is None:
            self.row.id = uuid4()  # type: ignore[attr-defined]

    def refresh(self, _row: object) -> None:
        pass

    def flush(self) -> None:
        pass


@pytest.mark.parametrize(
    ("domain_outcome", "expected_outcome", "expected_category"),
    [
        (NutritionPlanGenerationOutcome.SAFETY_BLOCKED, "blocked", "safety_restriction"),
        (NutritionPlanGenerationOutcome.FAILED, "failure", "engine_validation"),
        (NutritionPlanGenerationOutcome.INFEASIBLE, "failure", "engine_validation"),
        (NutritionPlanGenerationOutcome.TARGET_INFEASIBLE, "failure", "engine_validation"),
        (NutritionPlanGenerationOutcome.LIVE_PRICE_UNAVAILABLE, "failure", "engine_validation"),
    ],
)
def test_persisted_domain_failure_emits_after_commit(
    monkeypatch: pytest.MonkeyPatch,
    domain_outcome: NutritionPlanGenerationOutcome,
    expected_outcome: str,
    expected_category: str,
) -> None:
    db = _PersistRecorder()
    emissions: list[dict[str, object]] = []

    def record_emit(**kwargs: object) -> bool:
        assert db.committed
        emissions.append(kwargs)
        return True

    monkeypatch.setattr(plan_service, "emit", record_emit)

    generation = plan_service._persist_generation(
        db,  # type: ignore[arg-type]
        user_id=uuid4(),
        safety=SimpleNamespace(id=uuid4(), outcome=SafetyOutcome.STANDARD_AUTOMATIC),  # type: ignore[arg-type]
        estimate=None,
        outcome=domain_outcome,
        reasons=("TEST_REASON",),
        warnings=(),
        input_snapshot={},
        diagnostics={},
    )

    assert generation.outcome is domain_outcome
    assert len(emissions) == 1
    assert emissions[0]["outcome"] == expected_outcome
    assert emissions[0]["category"] == expected_category
    assert emissions[0]["resource_id"] == generation.id


def test_uncommitted_generation_does_not_emit_persisted_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _PersistRecorder()
    emissions: list[dict[str, object]] = []
    monkeypatch.setattr(plan_service, "emit", lambda **kwargs: emissions.append(kwargs) or True)

    plan_service._persist_generation(
        db,  # type: ignore[arg-type]
        user_id=uuid4(),
        safety=SimpleNamespace(id=uuid4(), outcome=SafetyOutcome.STANDARD_AUTOMATIC),  # type: ignore[arg-type]
        estimate=None,
        outcome=NutritionPlanGenerationOutcome.FAILED,
        reasons=("TEST_REASON",),
        warnings=(),
        input_snapshot={},
        diagnostics={},
        commit=False,
    )

    assert not db.committed
    assert emissions == []


@pytest.mark.parametrize(
    ("pending_review", "expected_outcome", "expected_code"),
    [
        (False, "success", "NUTRITION_PLAN_SUCCESS"),
        (True, "pending_review", "NUTRITION_PLAN_PENDING_REVIEW"),
    ],
)
def test_success_result_uses_final_plan_state(
    monkeypatch: pytest.MonkeyPatch,
    pending_review: bool,
    expected_outcome: str,
    expected_code: str,
) -> None:
    emissions: list[dict[str, object]] = []
    monkeypatch.setattr(plan_service, "emit", lambda **kwargs: emissions.append(kwargs) or True)

    plan_service._emit_generation_outcome(
        NutritionPlanGenerationOutcome.SUCCESS,
        resource_id=uuid4(),
        version="planner-test",
        pending_review=pending_review,
    )

    assert emissions[0]["outcome"] == expected_outcome
    assert emissions[0]["error_code"] == expected_code


@pytest.mark.parametrize(
    ("decision_stage", "domain_outcome", "diagnostic_outcome"),
    [
        ("medical_safety", NutritionPlanGenerationOutcome.SAFETY_BLOCKED, "blocked"),
        ("dietary_constraints", NutritionPlanGenerationOutcome.FAILED, "failure"),
    ],
)
def test_persisted_domain_failure_keeps_decision_stage_and_serializes_successfully(
    decision_stage: str,
    domain_outcome: NutritionPlanGenerationOutcome,
    diagnostic_outcome: str,
) -> None:
    events = []
    runtime = DiagnosticsRuntime(
        Settings(app_env="test"), injected_sink=lambda event, _user_id: events.append(event)
    )

    async def exercise() -> Response:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/nutrition/plans",
            "headers": Headers().raw,
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
            "state": {},
        }
        request = Request(scope)

        async def endpoint(_request: Request) -> Response:
            plan_service.set_stage(decision_stage, component="nutrition_engine")
            plan_service._emit_generation_outcome(
                domain_outcome,
                resource_id=uuid4(),
                version="planner-test",
                failure_stage=decision_stage,
            )
            plan_service.set_stage("response_serialization")
            return Response(status_code=201)

        return await diagnostics_middleware(request, endpoint, runtime)

    response = asyncio.run(exercise())

    assert response.status_code == 201
    terminal = [event for event in events if event.record_type == "event"][-1]
    assert terminal.stage == decision_stage
    assert terminal.outcome == diagnostic_outcome
    serialization = [
        event
        for event in events
        if event.record_type == "span" and event.stage == "response_serialization"
    ]
    assert serialization[-1].outcome == "success"
