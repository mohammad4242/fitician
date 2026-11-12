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
