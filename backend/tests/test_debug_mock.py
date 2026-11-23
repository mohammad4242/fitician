import asyncio

import pytest


@pytest.mark.parametrize(
    "mode,kind", [("mock", "diagnosis"), ("real", "diagnosis"), ("mock", "tool_call")]
)
def test_claude_mock_cannot_become_real_execution_or_invoke_laptop_tools(
    db, test_settings, monkeypatch, mode, kind
):
    from app.debugging import agent_runtime
    from tests.test_debug_gateway import setup_run

    _, run, _, _ = setup_run(db)
    config = {
        "agent_name": "claude",
        "agent_model_id": "mock-claude",
        "agent_profile_id": "claude-mock-debug",
        "agent_profile_fingerprint": "a" * 16,
        "timeout_seconds": 30,
        "authorized_action": "prepare_fix",
        "connector_capabilities": {"supports_tests": True, "supports_validation": True},
    }

    async def infer(client, **kwargs):
        assert kwargs["json_body"]["tools"] == []
        return {
            "agent": "claude",
            "model_id": "mock-claude",
            "profile_id": "claude-mock-debug",
            "execution_mode": mode,
            "request_id": "mock-request",
            "payload": {
                "kind": kind,
                "happened": "MOCK: no model or tools executed",
                "facts": [],
                "tool": "fitician_read_file",
                "arguments_json": '{"path":"bug.py"}',
            },
        }

    async def forbidden(*args, **kwargs):
        pytest.fail("MOCK reached a real execution target")

    monkeypatch.setattr(agent_runtime, "_agent_service_json", infer)
    monkeypatch.setattr(agent_runtime, "call_connector", forbidden)
    call = agent_runtime.run_agent(
        test_settings,
        db.connection(),
        run.id,
        run.lease_token,
        config,
        [{"role": "user", "content": "Investigate"}],
    )
    if mode == "mock" and kind == "diagnosis":
        assert "MOCK" in asyncio.run(call)
    else:
        with pytest.raises(ValueError, match="mock_execution_not_authorized"):
            asyncio.run(call)


def test_admin_can_verify_only_the_explicit_claude_mock_profile_without_real_login(
    client, db, monkeypatch
):
    from datetime import UTC, datetime

    from app.body_analysis.admin_config.enums import AITaskType
    from app.body_analysis.admin_config.models import AIAgentProfileVerification
    from app.body_analysis.admin_config.schemas import AgentServiceCapabilitiesResponse
    from app.debugging.connectors import enroll_connector
    from tests.admin.test_ai_task_settings_api import _admin

    actor = _admin(client, db)
    target, _ = enroll_connector(db, actor.id, "Laptop")
    target.capabilities = {"execution_role": "repository_worker"}
    db.add(
        AIAgentProfileVerification(
            profile_id="claude-mock-debug",
            task_type=AITaskType.DEBUG_AGENT,
            profile_fingerprint="a" * 16,
            status="passed",
            checked_at=datetime.now(UTC),
        )
    )
    db.flush()
    caps = AgentServiceCapabilitiesResponse.model_validate(
        {
            "runners": [
                {
                    "agent": "claude",
                    "installed": False,
                    "auth_state": "unknown",
                    "debug_status": "mock",
                    "models": [],
                    "profiles": [
                        {
                            "profile_id": "claude-mock-debug",
                            "agent": "claude",
                            "model_id": "mock-claude",
                            "display_name": "Claude MOCK",
                            "fingerprint": "a" * 16,
                            "task_kinds": ["debug_agent"],
                            "supports_text_input": True,
                            "supports_image_input": False,
                            "supports_structured_output": True,
                            "verification_status": "passed",
                        }
                    ],
                }
            ]
        }
    )

    async def capability(**kwargs):
        return caps

    monkeypatch.setattr(
        "app.body_analysis.admin_config.router.get_agent_service_capabilities", capability
    )
    response = client.put(
        "/api/v1/admin/ai/task-configs/debug_agent",
        json={
            "enabled": True,
            "execution_backend": "agent_service",
            "agent_name": "claude",
            "agent_model_id": "mock-claude",
            "agent_profile_id": "claude-mock-debug",
            "debug_connector_id": str(target.id),
        },
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("execution_mode", ["mock", "real"])
def test_mock_smoke_cannot_verify_a_real_provider_response(
    db, test_settings, monkeypatch, execution_mode
):
    import httpx

    from app.body_analysis.admin_config.enums import AIAgentName, AITaskType
    from app.body_analysis.admin_config.schemas import AgentServiceCapabilitiesResponse
    from app.body_analysis.admin_config.task_smoke import run_task_smoke

    caps = AgentServiceCapabilitiesResponse.model_validate(
        {
            "runners": [
                {
                    "agent": "claude",
                    "installed": False,
                    "debug_status": "mock",
                    "models": [],
                    "profiles": [
                        {
                            "profile_id": "claude-mock-debug",
                            "agent": "claude",
                            "model_id": "mock-claude",
                            "display_name": "MOCK",
                            "task_kinds": ["debug_agent"],
                            "fingerprint": "a" * 16,
                            "supports_text_input": True,
                            "supports_image_input": False,
                            "supports_structured_output": True,
                        }
                    ],
                }
            ]
        }
    )

    async def capabilities(**kwargs):
        return caps

    async def response(*args, **kwargs):
        return {
            "agent": "claude",
            "model_id": "mock-claude",
            "profile_id": "claude-mock-debug",
            "execution_mode": execution_mode,
            "payload": {"kind": "diagnosis"},
        }

    monkeypatch.setattr(
        "app.body_analysis.admin_config.task_smoke.get_agent_service_capabilities", capabilities
    )
    monkeypatch.setattr("app.body_analysis.admin_config.service._agent_service_json", response)

    async def exercise():
        async with httpx.AsyncClient() as client:
            result, _ = await run_task_smoke(
                db,
                task_type=AITaskType.DEBUG_AGENT,
                agent=AIAgentName.CLAUDE,
                profile_id="claude-mock-debug",
                settings=test_settings,
                client=client,
            )
            assert result.passed is (execution_mode == "mock")

    asyncio.run(exercise())
