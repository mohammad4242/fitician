import json

from app.runners.codex import CodexRunner
from app.schemas import AgentTaskKind


def test_codex_debug_models_come_from_cli_cache_not_generation_defaults(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cache = home / ".codex/models_cache.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(
        json.dumps(
            {
                "models": [
                    {"slug": "account-model", "visibility": "list"},
                    {"slug": "hidden-model", "visibility": "hide"},
                ]
            }
        )
    )
    monkeypatch.setenv("HOME", str(home))
    runner = CodexRunner(tmp_path)
    import asyncio

    monkeypatch.setattr(runner, "_is_installed", lambda: True)

    async def version():
        return "codex-cli 0.151.0"

    monkeypatch.setattr(runner._metadata, "version", version)
    profiles = asyncio.run(runner.capabilities()).profiles or []
    debug = [p for p in profiles if AgentTaskKind.DEBUG_AGENT in p.task_kinds]
    assert debug and {p.model_id for p in debug} == {"account-model"}
    from app.profiles import codex_profiles

    legacy = codex_profiles(
        version="codex-cli 0.151.0", configured_models=(), supports_image_input=False
    )
    generation = [p for p in profiles if AgentTaskKind.DEBUG_AGENT not in p.task_kinds]
    assert [(p.profile_id, p.fingerprint) for p in generation] == [
        (p.profile_id, p.fingerprint) for p in legacy
    ]


def test_appserver_catalog_uses_metadata_only_and_closes_process(tmp_path):
    import asyncio

    from app.runners.cli_catalog import codex_models

    cli = tmp_path / "codex"
    cli.write_text(
        "#!/usr/bin/env python3\nimport json,sys\n"
        "for line in sys.stdin:\n"
        " m=json.loads(line)\n"
        ' if m.get("method")=="initialize": print(json.dumps({"id":1,"result":{}}),flush=True)\n'
        ' elif m.get("method")=="model/list":\n'
        '  print(json.dumps({"id":2,"result":{"data":[\n'
        '   {"model":"real-account-model","hidden":False},\n'
        '   {"model":"hidden","hidden":True}],"nextCursor":None}}),flush=True)\n'
        ' elif m.get("method")!="initialized": raise SystemExit(99)\n'
    )
    cli.chmod(0o700)
    assert asyncio.run(codex_models(str(cli), tmp_path, {})) == ("real-account-model",)


def test_claude_debug_models_use_explicit_cli_preference(tmp_path, monkeypatch):
    import asyncio

    from app.runners.claude import ClaudeRunner

    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude/settings.json").write_text(
        json.dumps(
            {"model": "claude-account-model", "env": {"SECRET_FIXTURE": "must-not-be-exported"}}
        )
    )
    monkeypatch.setenv("HOME", str(home))
    runner = ClaudeRunner(tmp_path)
    monkeypatch.setattr(runner, "_is_installed", lambda: True)

    async def version():
        return "2.1.220 (Claude Code)"

    monkeypatch.setattr(runner._metadata, "version", version)
    capabilities = asyncio.run(runner.capabilities())
    debug = [p for p in capabilities.profiles or [] if AgentTaskKind.DEBUG_AGENT in p.task_kinds]
    assert debug and {p.model_id for p in debug} == {"claude-account-model"}
    assert "must-not-be-exported" not in capabilities.model_dump_json()


def test_debug_profiles_do_not_change_generation_verification_fingerprints():
    from app.profiles import codex_profiles, debug_profiles

    profiles = codex_profiles(
        version="0.151.0", configured_models=("account-model",), supports_image_input=True
    )
    assert all(AgentTaskKind.DEBUG_AGENT not in p.task_kinds for p in profiles)
    debug = debug_profiles(profiles, version="0.151.0")
    assert debug and all(p.task_kinds == (AgentTaskKind.DEBUG_AGENT,) for p in debug)
    assert not any(p.supports_image_input or p.supports_live_web for p in debug)
    assert {p.profile_id for p in profiles}.isdisjoint(p.profile_id for p in debug)
