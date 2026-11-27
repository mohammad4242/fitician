import asyncio
import json
import shlex
import subprocess

import pytest

from app.runners.antigravity_debug import native_policy


@pytest.mark.parametrize(
    "name",
    [
        "view_file",
        "write_to_file",
        "run_command",
        "search_web",
        "mcp/private",
        "invoke_subagent",
        "run_workflow",
        "finish; unsafe",
        "finish",
    ],
)
def test_native_hook_allows_only_the_schema_output_formatter(tmp_path, name):
    with native_policy(tmp_path) as policy:
        hooks = json.loads((tmp_path / ".agents/hooks.json").read_text())
        command = hooks["fitician-debug-native-deny"]["PreToolUse"][0]["hooks"][0]["command"]
        assert json.loads(policy)["toolPermission"] == "strict"
        result = subprocess.run(
            shlex.split(command),
            input=json.dumps({"toolCall": {"name": name}}),
            capture_output=True,
            text=True,
            check=True,
        )
        assert json.loads(result.stdout)["decision"] == ("allow" if name == "finish" else "deny")
        bad = subprocess.run(
            shlex.split(command), input="invalid json", capture_output=True, text=True, check=True
        )
        assert json.loads(bad.stdout)["decision"] == "deny"
    assert not list(tmp_path.iterdir())


def test_native_policy_cannot_overwrite_existing_customizations(tmp_path):
    (tmp_path / ".agents").mkdir()
    old = tmp_path / ".agents/hooks.json"
    old.write_text("preserve")
    with pytest.raises(ValueError, match="native_tool_isolation_unavailable"):
        with native_policy(tmp_path):
            pytest.fail("preexisting customization was accepted")
    assert old.read_text() == "preserve"


def test_agy_debug_runner_has_request_scoped_denial_and_keeps_generation_policy(
    tmp_path, monkeypatch
):
    from app.process import ProcessResult
    from app.runners.antigravity import AntigravityRunner
    from app.runners.base import RunnerRequest

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

    runner = AntigravityRunner(tmp_path)

    async def version():
        return "1.5.14"

    monkeypatch.setattr(runner._metadata, "version", version)
    monkeypatch.setattr(runner, "_cli_log_snapshot", lambda: {})
    monkeypatch.setattr(runner, "_cli_log_diagnostics", lambda _: "")

    async def process(command, **kwargs):
        assert "--dangerously-skip-permissions" not in command
        settings = json.loads(command[command.index("--settings") + 1])
        assert settings["permissions"]["deny"] == [
            "command(*)",
            "read_file(*)",
            "write_file(*)",
            "read_url(*)",
            "execute_url(*)",
            "mcp(*)",
        ]
        assert "--disable-slash-commands" in command
        assert kwargs["max_output_bytes"] == 1048576
        assert (tmp_path / ".agents/hooks.json").is_file()
        return ProcessResult(0, json.dumps({"status": "SUCCESS", "structured_output": {}}), "")

    monkeypatch.setattr("app.runners.antigravity.run_process", process)
    assert asyncio.run(runner.run(request())).payload == {}
    assert not list(tmp_path.iterdir())
