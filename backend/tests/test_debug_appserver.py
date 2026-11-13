import asyncio
import os
from pathlib import Path

import pytest

from app.debugging.appserver import AppServer, thread_parameters


def test_selected_model_and_profile_options_are_not_substituted():
    params = thread_parameters(
        "selected/model",
        Path("/workspace/run"),
        [{"name": "fitician_read_file", "description": "read", "inputSchema": {"type": "object"}}],
    )
    assert params["model"] == "selected/model"
    assert params["ephemeral"] is False
    assert params["sandbox"] == "read-only"
    assert params["config"]["features.shell_tool"] is False
    assert params["dynamicTools"][0]["name"] == "fitician_read_file"


@pytest.mark.skipif(
    os.environ.get("FITICIAN_TEST_CODEX_APP_SERVER") != "1",
    reason="Requires the explicitly installed pinned Codex CLI",
)
def test_installed_protocol_handshake_and_model_catalog_without_generation():
    async def run():
        async with AppServer(
            executable=os.environ.get("FITICIAN_TEST_CODEX_EXECUTABLE", "codex")
        ) as server:
            models = await server.call("model/list", {"limit": 2})
            assert isinstance(models["data"], list)
            assert server.version == "0.167.2"

    asyncio.run(run())
