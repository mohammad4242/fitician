import asyncio
import json

import httpx

from app.debugging.api_runtime import run_api_tools


def test_selected_api_model_executes_a_real_tool_loop_without_model_fallback():
    calls, requests = [], []

    def handle(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "fitician_read_file",
                            "arguments": '{"path":"bug.py"}',
                        },
                    }
                ],
            }
        else:
            assert payload["messages"][-1]["role"] == "tool"
            assert "return a - b" in payload["messages"][-1]["content"]
            message = {"role": "assistant", "content": "Observed subtraction in evidence fixture."}
        return httpx.Response(200, json={"choices": [{"message": message}]})

    async def tool(name, arguments):
        calls.append((name, arguments))
        return "1: def add(a, b):\n2:     return a - b"

    async def progress(kind, payload):
        pass

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await run_api_tools(
                client,
                base_url="https://openrouter.ai/api/v1",
                api_key="test-key",
                config={"primary_model_id": "selected/model", "max_output_tokens": 4096},
                messages=[{"role": "user", "content": "inspect"}],
                tools=[
                    {
                        "name": "fitician_read_file",
                        "description": "read",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"],
                            "additionalProperties": False,
                        },
                    }
                ],
                handler=tool,
                progress=progress,
            )

    result = asyncio.run(run())
    assert result == "Observed subtraction in evidence fixture."
    assert calls == [("fitician_read_file", {"path": "bug.py"})]
    assert all(request["model"] == "selected/model" for request in requests)
    assert all(request["provider"]["allow_fallbacks"] is False for request in requests)
