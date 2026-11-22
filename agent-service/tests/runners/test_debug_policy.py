from app.runners.base import RunnerRequest
from app.runners.claude import ClaudeRunner
from app.runners.codex import CodexRunner


def request():
    return RunnerRequest(
        model_id="selected-model",
        system_prompt="Investigate",
        input_payload={},
        response_schema={"type": "object"},
        schema_name="debug_action",
        temperature=0,
        max_output_tokens=100,
        timeout_seconds=5,
        external_tools_only=True,
    )


def test_codex_external_turn_disables_shell_web_apps_and_configured_mcp(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    (home / ".codex/config.toml").write_text('[mcp_servers.private]\ncommand="never-run"\n')
    monkeypatch.setenv("HOME", str(home))
    command = CodexRunner(tmp_path)._command(
        request(), tmp_path, tmp_path / "schema.json", tmp_path / "output.json", []
    )
    assert "features.shell_tool=false" in command
    assert 'web_search="disabled"' in command
    assert 'mcp_servers."private".enabled=false' in command
    assert "features.apps=false" in command
    assert "features.multi_agent=false" in command
    assert "features.plugins=false" in command


def test_claude_external_turn_has_no_builtin_or_user_mcp_tools(tmp_path):
    command = ClaudeRunner(tmp_path)._command(request(), {"type": "object"})
    assert command[command.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in command
    assert command[command.index("--mcp-config") + 1] == '{"mcpServers":{}}'
    assert "--safe-mode" in command
    assert command[command.index("--permission-mode") + 1] == "dontAsk"


def test_version_policy_accepts_actual_cli_version_labels():
    from app.runners.debug_policy import supports_external_tools
    from app.schemas import AgentName

    assert supports_external_tools(AgentName.CODEX, "codex-cli 0.151.0")
    assert supports_external_tools(AgentName.CLAUDE, "2.1.220 (Claude Code)")
    assert not supports_external_tools(AgentName.CLAUDE, "2.1.221 (Claude Code)")


def test_claude_auth_probe_allows_measured_cli_startup_time(tmp_path, monkeypatch):
    import asyncio

    from app.process import ProcessResult
    from app.schemas import AuthState

    async def process(command, **kwargs):
        assert kwargs["timeout_seconds"] >= 6
        return ProcessResult(1, '{"loggedIn":false}', "")

    monkeypatch.setattr("app.runners.probes.run_process", process)
    runner = ClaudeRunner(tmp_path)
    monkeypatch.setattr(runner, "_is_installed", lambda: True)
    assert asyncio.run(runner.probe_auth_state()) == AuthState.UNAUTHENTICATED
