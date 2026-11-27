from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app
from app.runners.registry import RunnerRegistry
from app.schemas import AgentName, AuthState, RunnerCapabilities

TOKEN = "m" * 32


class ClaudeNoExecution:
    name = AgentName.CLAUDE

    async def capabilities(self):
        return RunnerCapabilities(agent=self.name, installed=False, auth_state=AuthState.UNKNOWN)

    async def run(self, request):
        raise AssertionError("MOCK must never execute Claude CLI or a provider")


def test_claude_mock_is_available_without_installation_login_or_tool_execution(tmp_path):
    client = TestClient(
        create_app(
            Settings(agent_service_token=SecretStr(TOKEN), agent_workspace_root=tmp_path),
            registry=RunnerRegistry([ClaudeNoExecution()]),
        )
    )
    headers = {"Authorization": "Bearer " + TOKEN}
    capability = client.get("/v1/capabilities", headers=headers).json()["runners"][0]
    assert capability["debug_status"] == "mock"
    assert capability["auth_state"] != "authenticated"
    profile = next(p for p in capability["profiles"] if p["profile_id"] == "claude-mock-debug")
    assert "MOCK" in profile["display_name"]
    request = {
        "agent": "claude",
        "model_id": profile["model_id"],
        "profile_id": profile["profile_id"],
        "profile_fingerprint": profile["fingerprint"],
        "timeout_seconds": 5,
        "messages": [{"role": "user", "content": "Sensitive fixture: never echo this sentence"}],
        "tools": [{"name": "fitician_write_file", "inputSchema": {"type": "object"}}],
    }
    result = client.post("/v1/debug/turn", headers=headers, json=request)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["execution_mode"] == "mock"
    assert body["input_tokens"] == body["output_tokens"] == 0
    assert body["payload"]["kind"] == "diagnosis"
    assert body["payload"]["facts"] == []
    assert "MOCK" in body["payload"]["happened"]
    assert "Sensitive fixture" not in result.text
    request["model_id"] = "real-claude-model"
    assert client.post("/v1/debug/turn", headers=headers, json=request).status_code == 422
    assert client.post("/v1/debug/turn", json=request).status_code == 401


def test_debug_discovery_does_not_probe_or_authenticate_claude(tmp_path):
    calls = []

    class NoClaudeProbe(ClaudeNoExecution):
        async def capabilities(self):
            calls.append("real Claude probe")
            return await super().capabilities()

    client = TestClient(
        create_app(
            Settings(agent_service_token=SecretStr(TOKEN), agent_workspace_root=tmp_path),
            registry=RunnerRegistry([NoClaudeProbe()]),
        )
    )
    result = client.get(
        "/v1/capabilities?task_kind=debug_agent", headers={"Authorization": "Bearer " + TOKEN}
    )
    assert result.status_code == 200
    assert result.json()["runners"][0]["debug_status"] == "mock"
    assert calls == []
