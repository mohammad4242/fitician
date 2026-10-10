import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app
from app.runners.base import AgentRunner, RunnerError, RunnerRequest, RunnerResult
from app.runners.registry import RunnerRegistry
from app.schemas import AgentName, AuthState, RunnerCapabilities, RunnerModelCapabilities

TOKEN = "a" * 32


class FakeRunner(AgentRunner):
    name = AgentName.ANTIGRAVITY

    def __init__(self) -> None:
        self.run_calls = 0

    async def capabilities(self) -> RunnerCapabilities:
        return RunnerCapabilities(
            agent=self.name,
            installed=True,
            auth_state=AuthState.UNKNOWN,
            models=[
                RunnerModelCapabilities(
                    model_id="fake-model",
                    supports_text_input=True,
                    supports_image_input=False,
                    supports_structured_output=True,
                )
            ],
        )

    async def run(self, request: RunnerRequest) -> RunnerResult:
        self.run_calls += 1
        return RunnerResult(
            payload={"ok": True},
            model_id=request.model_id,
            input_tokens=1,
            output_tokens=2,
            duration_seconds=0.01,
        )


def test_capabilities_are_owned_by_runners_and_do_not_run_generation(tmp_path: Path) -> None:
    settings = Settings(agent_service_token=SecretStr(TOKEN), agent_workspace_root=tmp_path)
    runner = FakeRunner()
    app = create_app(settings, registry=RunnerRegistry([runner]))
    response = TestClient(app).get(
        "/v1/capabilities", headers={"Authorization": f"Bearer {TOKEN}"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "runners": [
            {
                "agent": "antigravity",
                "installed": True,
                "version": None,
                "auth_state": "unknown",
                "auth_mode": "unknown",
                "models": [
                    {
                        "model_id": "fake-model",
                        "supports_text_input": True,
                        "supports_image_input": False,
                        "supports_structured_output": True,
                        "supports_live_web": False,
                        "supports_temperature": False,
                        "supports_max_output_tokens": False,
                    }
                ],
            }
        ]
    }
    assert runner.run_calls == 0


def _write_runner_probe(
    path: Path, *, version: str, auth_command: tuple[str, ...], auth_output: str, auth_code: int
) -> Path:
    path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"version = {version!r}\n"
        f"auth_command = {auth_command!r}\n"
        f"auth_output = {auth_output!r}\n"
        f"auth_code = {auth_code}\n"
        "args = tuple(sys.argv[1:])\n"
        "if args == ('--version',):\n"
        "    print(version)\n"
        "elif args == auth_command:\n"
        "    print(auth_output)\n"
        "    raise SystemExit(auth_code)\n"
        "elif args == ('models',):\n"
        "    raise SystemExit(0)\n"
        "else:\n"
        "    raise SystemExit(2)\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def test_default_registry_has_no_invented_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    agy_version = "1.1.22"
    codex_version = "codex-cli 0.151.0"
    claude_version = "2.1.220 (Claude Code)"
    settings = Settings(
        agent_service_token=SecretStr(TOKEN),
        agent_workspace_root=tmp_path / "workspace",
        agent_antigravity_executable=str(
            _write_runner_probe(
                tmp_path / "agy",
                version=agy_version,
                auth_command=(),
                auth_output="",
                auth_code=0,
            )
        ),
        agent_codex_executable=str(
            _write_runner_probe(
                tmp_path / "codex",
                version=codex_version,
                auth_command=("login", "status"),
                auth_output="Not logged in",
                auth_code=1,
            )
        ),
        agent_claude_executable=str(
            _write_runner_probe(
                tmp_path / "claude",
                version=claude_version,
                auth_command=("auth", "status", "--json"),
                auth_output='{"loggedIn":false}',
                auth_code=0,
            )
        ),
    )
    response = TestClient(create_app(settings)).get(
        "/v1/capabilities", headers={"Authorization": f"Bearer {TOKEN}"}
    )

    assert response.status_code == 200
    runners = {runner["agent"]: runner for runner in response.json()["runners"]}
    assert set(runners) == {"antigravity", "codex", "claude"}
    assert runners["antigravity"]["version"] == agy_version
    assert runners["antigravity"]["auth_mode"] == "browser_link"
    assert runners["codex"]["auth_mode"] == "browser_link"
    assert runners["claude"]["auth_mode"] == "browser_link"
    assert runners["codex"]["version"] == codex_version
    assert runners["claude"]["version"] == claude_version
    assert all(runner["installed"] is True for runner in runners.values())
    assert all(runner["models"] == [] for runner in runners.values())
    assert runners["antigravity"]["auth_state"] == "unauthenticated"
    assert runners["codex"]["auth_state"] == "unauthenticated"
    assert runners["claude"]["auth_state"] == "unauthenticated"


def test_capability_probe_failure_is_reported_without_a_500(tmp_path: Path) -> None:
    class BrokenRunner(FakeRunner):
        async def capabilities(self) -> RunnerCapabilities:
            raise RuntimeError("private capability failure")

    settings = Settings(agent_service_token=SecretStr(TOKEN), agent_workspace_root=tmp_path)
    response = TestClient(create_app(settings, registry=RunnerRegistry([BrokenRunner()]))).get(
        "/v1/capabilities", headers={"Authorization": f"Bearer {TOKEN}"}
    )

    assert response.status_code == 200
    assert response.json()["runners"] == [
        {
            "agent": "antigravity",
            "installed": False,
            "version": None,
            "auth_state": "unknown",
            "auth_mode": "unknown",
            "models": [],
        }
    ]


def test_successful_test_marks_runner_authenticated_without_model_quota_probe(
    tmp_path: Path,
) -> None:
    settings = Settings(agent_service_token=SecretStr(TOKEN), agent_workspace_root=tmp_path)
    runner = FakeRunner()
    registry = RunnerRegistry([runner])
    app = create_app(settings, registry=registry)
    client = TestClient(app)

    response = client.post(
        "/v1/test",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"agent": "antigravity", "model_id": "fake-model"},
    )

    assert response.status_code == 200
    assert runner.run_calls == 1
    capabilities = client.get(
        "/v1/capabilities", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert capabilities.json()["runners"][0]["auth_state"] == "authenticated"


def test_auth_probe_error_is_exposed_as_unknown_instead_of_stale_unauthenticated(
    tmp_path: Path,
) -> None:
    class ProbeUnknownRunner(FakeRunner):
        async def probe_auth_state(self) -> AuthState:
            return AuthState.UNKNOWN

    settings = Settings(agent_service_token=SecretStr(TOKEN), agent_workspace_root=tmp_path)
    runner = ProbeUnknownRunner()
    registry = RunnerRegistry([runner])
    registry.set_auth_state(AgentName.ANTIGRAVITY, AuthState.UNAUTHENTICATED)
    client = TestClient(create_app(settings, registry=registry))

    capabilities = client.get(
        "/v1/capabilities", headers={"Authorization": f"Bearer {TOKEN}"}
    )

    assert capabilities.status_code == 200
    assert capabilities.json()["runners"][0]["auth_state"] == "unknown"


def test_unauthorized_test_marks_runner_unauthenticated(tmp_path: Path) -> None:
    class UnauthorizedRunner(FakeRunner):
        async def run(self, request: RunnerRequest) -> RunnerResult:
            del request
            raise RunnerError("unauthorized", "private runner error")

    settings = Settings(agent_service_token=SecretStr(TOKEN), agent_workspace_root=tmp_path)
    runner = UnauthorizedRunner()
    registry = RunnerRegistry([runner])
    client = TestClient(create_app(settings, registry=registry))

    response = client.post(
        "/v1/test",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"agent": "antigravity", "model_id": "fake-model"},
    )

    assert response.status_code == 401
    assert "private runner error" not in response.text
    capabilities = client.get(
        "/v1/capabilities", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert capabilities.json()["runners"][0]["auth_state"] == "unauthenticated"
