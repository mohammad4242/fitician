"""Inference is remote; no repository or native CLI tool authority is granted."""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app
from app.profiles import claude_profiles, codex_profiles, debug_profiles
from app.runners.base import RunnerRequest, RunnerResult
from app.runners.registry import RunnerRegistry
from app.schemas import AgentName, AuthState, RunnerCapabilities

TOKEN = "d" * 32


class DebugRunner:
    name = AgentName.CODEX

    def __init__(self, name=AgentName.CODEX):
        self.name = name
        self.requests = []

    async def capabilities(self):
        return RunnerCapabilities(
            agent=self.name,
            installed=True,
            version="0.151.0" if self.name == AgentName.CODEX else "2.1.220",
            auth_state=AuthState.AUTHENTICATED,
            profiles=list(
                debug_profiles(
                    (codex_profiles if self.name == AgentName.CODEX else claude_profiles)(
                        version="0.151.0" if self.name == AgentName.CODEX else "2.1.220",
                        configured_models=("discovered-model",),
                        supports_image_input=False,
                    ),
                    version="0.151.0" if self.name == AgentName.CODEX else "2.1.220",
                )
            ),
        )

    async def run(self, request: RunnerRequest):
        self.requests.append(request)
        return RunnerResult(
            payload={
                "kind": "tool_call",
                "tool": "fitician_read_file",
                "arguments_json": '{"path": "backend/app/main.py"}',
            },
            model_id=request.model_id,
            input_tokens=10,
            output_tokens=10,
            duration_seconds=0.1,
        )


@pytest.mark.parametrize("agent", [AgentName.CODEX, AgentName.CLAUDE])
def test_debug_turn_uses_selected_profile_without_repository_access(tmp_path: Path, agent):
    runner = DebugRunner(agent)
    client = TestClient(
        create_app(
            Settings(agent_service_token=SecretStr(TOKEN), agent_workspace_root=tmp_path),
            registry=RunnerRegistry([runner]),
        )
    )
    assert (
        client.get("/v1/capabilities", headers={"Authorization": "Bearer " + TOKEN}).json()[
            "runners"
        ][0]["debug_status"]
        == "available"
    )
    request = {
        "agent": agent.value,
        "model_id": "discovered-model",
        "profile_id": (asyncio.run(runner.capabilities()).profiles or [])[0].profile_id,
        "profile_fingerprint": (asyncio.run(runner.capabilities()).profiles or [])[0].fingerprint,
        "timeout_seconds": 5,
        "messages": [{"role": "user", "content": "Investigate evidence e1"}],
        "tools": [{"name": "fitician_read_file", "inputSchema": {"type": "object"}}],
    }
    response = client.post(
        "/v1/debug/turn", json=request, headers={"Authorization": "Bearer " + TOKEN}
    )
    assert response.status_code == 200, response.text
    assert response.json()["payload"]["tool"] == "fitician_read_file"
    assert runner.requests[0].external_tools_only is True
    assert runner.requests[0].web_access == "disabled"
    assert runner.requests[0].image_paths == ()
    assert not list(tmp_path.iterdir())
    assert client.post("/v1/debug/turn", json=request).status_code == 401


@pytest.mark.parametrize("agent", ["codex", "claude", "antigravity"])
def test_debugging_is_not_advertised_for_unverified_native_tool_policy(agent):
    from app.runners.debug_policy import supports_external_tools

    assert not supports_external_tools(AgentName(agent), "0.0.1")


def test_debug_backend_disconnect_cancels_only_its_inference():
    from app.debug_turn import while_connected

    stopped = []

    async def inference():
        try:
            await asyncio.Event().wait()
        finally:
            stopped.append(True)

    async def disconnected():
        return True

    async def exercise():
        with pytest.raises(asyncio.CancelledError):
            await while_connected(inference(), disconnected)

    asyncio.run(exercise())
    assert stopped == [True]
