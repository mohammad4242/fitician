import asyncio
import json

import pytest

from app.debugging.runtime_profiles import snapshot_connector
from tests.test_debug_runtime_profiles import target_fixture


def test_agent_profile_and_laptop_are_independent(db):
    _, laptop = target_fixture(db, "Laptop")
    for agent in ("codex", "claude", "antigravity"):
        assert snapshot_connector(
            db,
            {
                "execution_backend": "agent_service",
                "agent_name": agent,
                "agent_profile_id": agent + "-real-model",
                "debug_connector_id": str(laptop.id),
            },
        ) == str(laptop.id)
    assert (
        snapshot_connector(
            db, {"execution_backend": "agent_service", "agent_profile_id": "unrelated"}
        )
        is None
    )


def test_backend_orchestrates_actual_tool_result_before_next_inference():
    from app.debugging.agent_runtime import tool_loop

    requests, calls = [], []

    async def infer(messages, tools, step):
        requests.append(json.loads(json.dumps(messages)))
        if step == 0:
            return {
                "kind": "tool_call",
                "tool": "fitician_read_file",
                "arguments_json": '{"path":"backend/app/main.py"}',
            }
        return {
            "kind": "diagnosis",
            "happened": "خطای آزمایشی",
            "facts": ["e1"],
            "hypotheses": [],
            "evidence_ids": ["e1"],
        }

    async def invoke(name, args, step):
        calls.append((name, args))
        return {"output": '{"evidence_id":"e1","output":"source excerpt"}'}

    result = asyncio.run(
        tool_loop(
            [{"role": "user", "content": "Investigate"}],
            [
                {
                    "name": "fitician_read_file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                }
            ],
            infer,
            invoke,
        )
    )
    assert len(calls) == 1
    assert "source excerpt" in requests[1][-1]["content"]
    assert result["happened"] == "خطای آزمایشی"


def test_backend_rejects_model_proposed_unlisted_tool():
    from app.debugging.agent_runtime import tool_loop

    async def infer(*args):
        return {"kind": "tool_call", "tool": "shell", "arguments_json": '{"command":"id"}'}

    async def invoke(*args):
        pytest.fail("unauthorized tool reached execution target")

    with pytest.raises(ValueError, match="tool_not_authorized"):
        asyncio.run(tool_loop([{"role": "user", "content": "test"}], [], infer, invoke))


def test_repository_worker_never_discovers_or_runs_a_model(tmp_path, monkeypatch):
    from app.debugging.connector import LaptopConnector
    from tests.test_debug_tools import repository

    repo = tmp_path / "source"
    commit = repository(repo)
    from app.debugging.tools import _git

    _git(repo, "remote", "add", "origin", "git@github.com:mohammad4242/fitician.git")
    config = {
        "id": str(__import__("uuid").uuid4()),
        "token": "a" * 48,
        "server": "https://fitician.example",
        "repository_name": "mohammad4242/fitician",
        "environment": "test",
        "repository": str(repo),
        "workspace_root": str(tmp_path / "private"),
        "execution_role": "repository_worker",
        "workspace_min_free_bytes": 2147483648,
        "codex_home": "/must/not/be/opened",
        "repository_probe_path": "bug.py",
    }
    import httpx

    worker = LaptopConnector(config, httpx.AsyncClient())
    monkeypatch.setattr(worker, "codex_server", lambda: pytest.fail("laptop started AI"))
    asyncio.run(worker.discover())
    assert not worker.models

    async def exercise():
        result = await worker.execute_probe(
            {
                "id": str(__import__("uuid").uuid4()),
                "model": "repository",
                "execution_backend": "repository",
                "release_commit": commit,
            }
        )
        assert result["read_tool_executed"] is True
        assert result.get("error_code") is None

    # The fixture has a different allowed file; a repository connection probe
    # checks Git identity rather than requiring the latest application source.
    asyncio.run(exercise())


def test_repository_worker_rejects_wrong_repository_identity(tmp_path):
    import httpx

    from app.debugging.connector import LaptopConnector
    from tests.test_debug_tools import repository

    repo = tmp_path / "other"
    repository(repo)
    config = {
        "id": str(__import__("uuid").uuid4()),
        "server": "https://fitician.example",
        "repository_name": "mohammad4242/fitician",
        "repository": str(repo),
        "workspace_root": str(tmp_path / "private"),
        "execution_role": "repository_worker",
    }
    with pytest.raises(ValueError, match="repository_identity_mismatch"):
        LaptopConnector(config, httpx.AsyncClient())


def test_agent_run_rejects_fabricated_evidence_and_preserves_model_binding(
    db, test_settings, monkeypatch
):
    from app.debugging import agent_runtime
    from tests.test_debug_gateway import setup_run

    _, run, _, _ = setup_run(db)
    config = {
        "agent_name": "codex",
        "agent_model_id": "selected-account-model",
        "agent_profile_id": "codex-selected-low",
        "agent_profile_fingerprint": "a" * 16,
        "timeout_seconds": 30,
        "connector_capabilities": {},
    }

    async def infer(client, **kwargs):
        assert client.headers.get("X-Correlation-ID") == str(run.id)
        assert kwargs["path"] == "/v1/debug/turn"
        assert kwargs["json_body"]["model_id"] == config["agent_model_id"]
        assert kwargs["json_body"]["profile_fingerprint"] == "a" * 16
        return {
            "agent": "codex",
            "model_id": config["agent_model_id"],
            "profile_id": config["agent_profile_id"],
            "payload": {
                "kind": "diagnosis",
                "facts": ["Claim without supporting evidence"],
                "evidence_ids": ["00000000-0000-4000-8000-000000000001"],
            },
        }

    monkeypatch.setattr(agent_runtime, "_agent_service_json", infer)
    with pytest.raises(ValueError, match="finding_evidence_not_found"):
        asyncio.run(
            agent_runtime.run_agent(
                test_settings,
                db.connection(),
                run.id,
                run.lease_token,
                config,
                [{"role": "user", "content": "Investigate"}],
            )
        )


def test_laptop_validation_progress_is_a_real_testing_state(db):
    from uuid import UUID

    from app.debugging.connectors import claim_call, enqueue_call, update_call
    from tests.test_debug_gateway import setup_run

    _, run, connector, _ = setup_run(db, action="prepare_fix")
    row = enqueue_call(
        db,
        run,
        connector,
        "validate-progress",
        "fitician_validate",
        {"profile": "backend", "tests": ["backend/tests/test_debug_runs.py"]},
    )
    job = claim_call(db, connector)
    update_call(
        db,
        connector,
        row.id,
        UUID(job["lease_token"]),
        1,
        "tool_started",
        {"tool": "fitician_validate"},
    )
    assert run.state == "testing"


def test_midrun_laptop_disconnect_blocks_without_fallback(db):
    from datetime import UTC, datetime, timedelta

    from app.debugging.gateway import call_connector
    from tests.test_debug_gateway import setup_run

    _, run, connector, _ = setup_run(db)
    run.config_snapshot = {**run.config_snapshot, "connector_id": str(connector.id)}
    connector.last_seen = datetime.now(UTC) - timedelta(seconds=60)
    db.flush()

    async def exercise():
        with pytest.raises(ValueError, match="execution_target_offline"):
            await asyncio.wait_for(
                call_connector(
                    db.connection(),
                    run.id,
                    run.lease_token,
                    "offline-read",
                    "fitician_read_file",
                    {"path": "bug.py"},
                ),
                1,
            )

    asyncio.run(exercise())


def test_gateway_completion_survives_session_close_and_keeps_target_identity(db, monkeypatch):
    from datetime import UTC, datetime
    from uuid import UUID

    from app.debugging import gateway
    from app.debugging.connectors import claim_call, finish_call
    from tests.test_debug_gateway import setup_run

    _, run, connector, _ = setup_run(db)
    run.config_snapshot = {**run.config_snapshot, "connector_id": str(connector.id)}
    connector.last_seen = datetime.now(UTC)
    db.flush()

    async def finish(_):
        db.expire_all()
        job = claim_call(db, connector)
        assert job
        finish_call(
            db,
            connector,
            UUID(job["id"]),
            UUID(job["lease_token"]),
            {"output": "bounded repository evidence"},
        )
        db.flush()

    monkeypatch.setattr(gateway.asyncio, "sleep", finish)
    result = asyncio.run(
        gateway.call_connector(
            db.connection(),
            run.id,
            run.lease_token,
            "complete-read",
            "fitician_read_file",
            {"path": "bug.py"},
        )
    )
    assert result["output"] == "bounded repository evidence"


def test_unified_debug_settings_cannot_enable_a_laptop_or_separate_api_model(db, test_settings):
    from app.body_analysis.admin_config.enums import AITaskType
    from app.body_analysis.admin_config.schemas import AITaskConfigUpdate
    from app.body_analysis.admin_config.service import AIConfigError, save_task_config

    actor, _ = target_fixture(db, "Laptop")
    with pytest.raises(AIConfigError, match="requires Agent Service"):
        save_task_config(
            db,
            task_type=AITaskType.DEBUG_AGENT,
            payload=AITaskConfigUpdate(enabled=True, execution_backend="api"),
            actor=actor,
            settings=test_settings,
        )


def test_long_persistent_history_keeps_latest_request_and_marks_omissions():
    from app.debugging.agent_runtime import tool_loop

    async def infer(history, tools, step):
        assert len(json.dumps(history, ensure_ascii=False).encode()) <= 82000
        assert any("Selected occurrence" in m["content"] for m in history)
        assert any(m["content"] == "Latest scoped request" for m in history)
        assert any("context excerpt" in m["content"] for m in history)
        return {"kind": "diagnosis", "happened": "bounded context"}

    async def forbidden(*args):
        pytest.fail("no tool requested")

    history = [{"role": "system", "content": "Selected occurrence " + ("ش" * 40000)}]
    history += [{"role": "assistant", "content": "old context " + ("x" * 8000)} for _ in range(20)]
    history += [{"role": "user", "content": "Latest scoped request"}]
    result = asyncio.run(tool_loop(history, [], infer, forbidden))
    assert result["happened"] == "bounded context"


@pytest.mark.parametrize("uncertain", [False, True])
def test_worker_recovery_reuses_inference_receipts_without_repeating_paid_turns(
    db, test_settings, monkeypatch, uncertain
):
    from uuid import uuid4

    from app.debugging import agent_runtime
    from tests.test_debug_gateway import setup_run

    _, run, _, _ = setup_run(db)
    config = {
        "agent_name": "codex",
        "agent_model_id": "selected-model",
        "agent_profile_id": "codex-selected-low-debug",
        "agent_profile_fingerprint": "b" * 16,
        "timeout_seconds": 30,
        "connector_capabilities": {},
    }
    calls = []

    async def infer(*args, **kwargs):
        calls.append(True)
        if uncertain:
            raise TimeoutError
        return {
            "agent": "codex",
            "model_id": "selected-model",
            "profile_id": config["agent_profile_id"],
            "request_id": str(run.id),
            "payload": {"kind": "diagnosis", "happened": "Observed synthetic test", "facts": []},
        }

    monkeypatch.setattr(agent_runtime, "_agent_service_json", infer)
    if uncertain:
        with pytest.raises(TimeoutError):
            asyncio.run(
                agent_runtime.run_agent(
                    test_settings,
                    db.connection(),
                    run.id,
                    run.lease_token,
                    config,
                    [{"role": "user", "content": "Investigate"}],
                )
            )
    else:
        asyncio.run(
            agent_runtime.run_agent(
                test_settings,
                db.connection(),
                run.id,
                run.lease_token,
                config,
                [{"role": "user", "content": "Investigate"}],
            )
        )
    run.lease_token = uuid4()
    db.flush()
    if uncertain:
        with pytest.raises(ValueError, match="interrupted_call_requires_new_run"):
            asyncio.run(
                agent_runtime.run_agent(
                    test_settings,
                    db.connection(),
                    run.id,
                    run.lease_token,
                    config,
                    [{"role": "user", "content": "Investigate"}],
                )
            )
    else:
        asyncio.run(
            agent_runtime.run_agent(
                test_settings,
                db.connection(),
                run.id,
                run.lease_token,
                config,
                [{"role": "user", "content": "Investigate"}],
            )
        )
    assert calls == [True]


def test_admin_cannot_enable_debugging_using_an_old_verification_when_service_is_unavailable(
    client, db, monkeypatch
):
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.body_analysis.admin_config.enums import AITaskType
    from app.body_analysis.admin_config.models import AIAgentProfileVerification, AITaskConfig
    from app.body_analysis.providers import AIProviderError, ProviderErrorCode
    from app.debugging.connectors import enroll_connector
    from tests.admin.test_ai_task_settings_api import _admin

    actor = _admin(client, db)
    target, _ = enroll_connector(db, actor.id, "Laptop")
    target.capabilities = {"execution_role": "repository_worker"}
    db.add(
        AIAgentProfileVerification(
            profile_id="codex-chosen-low-debug",
            task_type=AITaskType.DEBUG_AGENT,
            profile_fingerprint="a" * 16,
            status="passed",
            checked_at=datetime.now(UTC),
        )
    )
    db.flush()
    calls = []

    async def unavailable(**kwargs):
        calls.append(True)
        raise AIProviderError(ProviderErrorCode.PROVIDER_UNAVAILABLE, "Service unavailable")

    monkeypatch.setattr(
        "app.body_analysis.admin_config.router.get_agent_service_capabilities", unavailable
    )
    response = client.put(
        "/api/v1/admin/ai/task-configs/debug_agent",
        json={
            "enabled": True,
            "execution_backend": "agent_service",
            "agent_name": "codex",
            "agent_model_id": "chosen",
            "agent_profile_id": "codex-chosen-low-debug",
            "debug_connector_id": str(target.id),
        },
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code in {502, 503}
    assert calls == [True]
    config = db.scalar(select(AITaskConfig).where(AITaskConfig.task_type == AITaskType.DEBUG_AGENT))
    assert config is None or not config.enabled
