from jsonschema import validate

from app.debugging.catalog import tool_catalog


def test_analysis_has_no_mutating_or_deployment_tools():
    read = {x["name"] for x in tool_catalog(allow_write=False)}
    write = {x["name"] for x in tool_catalog(allow_write=True)}
    assert "fitician_write_file" not in read
    assert "fitician_write_file" in write
    assert not any("deploy" in name or "shell" in name for name in write)
    for tool in tool_catalog(allow_write=True):
        assert tool["inputSchema"]["additionalProperties"] is False
    validate({"path": "backend/app/main.py"}, tool_catalog(allow_write=False)[0]["inputSchema"])


def test_delegated_ci_is_explicit_and_never_grants_local_docker_or_github_access():
    tools = tool_catalog(
        allow_write=True, supports_tests=False, supports_github=False, supports_ci=True
    )
    names = {t["name"] for t in tools}
    assert {"fitician_ci_validate", "fitician_ci_status"} <= names
    assert not names & {"fitician_run_tests", "fitician_commit", "fitician_create_pr"}
    assert not any("deploy" in t["name"] for t in tools)
    without = {t["name"] for t in tool_catalog(allow_write=False, supports_ci=False)}
    assert "fitician_ci_validate" not in without
    selected = next(t for t in tools if t["name"] == "fitician_ci_validate")
    validate(
        {"profile": "backend", "tests": ["backend/tests/test_debug_runs.py"]},
        selected["inputSchema"],
    )
