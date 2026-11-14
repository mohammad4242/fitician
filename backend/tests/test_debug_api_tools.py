import asyncio
import json

import httpx
import pytest

from app.debugging.api_runtime import run_api_tools


@pytest.mark.parametrize(
    "status,expected",
    [(429, "provider_rate_limited"), (401, "provider_rejected"), (503, "provider_rejected")],
)
def test_tool_provider_failure_keeps_the_selected_model_and_never_replays_or_exports_body(
    status, expected
):
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(status, json={"error": "private-provider-response-fixture"})

    async def forbidden(name, arguments):
        raise AssertionError("Rejected provider requests cannot execute tools")

    async def progress(kind, payload):
        assert "private-provider-response-fixture" not in json.dumps(payload)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            await run_api_tools(
                client,
                base_url="https://openrouter.ai/api/v1",
                api_key="synthetic",
                config={"primary_model_id": "selected/model", "max_output_tokens": 512},
                messages=[{"role": "user", "content": "Inspect synthetic evidence"}],
                tools=[],
                handler=forbidden,
                progress=progress,
            )

    with pytest.raises(ValueError, match="^" + expected + "$"):
        asyncio.run(run())
    assert len(requests) == 1
    assert requests[0]["model"] == "selected/model"
    assert requests[0]["provider"]["allow_fallbacks"] is False


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


def test_budget_tracks_reported_usage_across_tool_rounds_instead_of_reserved_maximums():
    requests, usage_events = [], []

    def handle(request):
        payload = json.loads(request.content)
        requests.append(payload)
        number = len(requests)
        message = (
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"read-{number}",
                        "type": "function",
                        "function": {
                            "name": "fitician_read_file",
                            "arguments": '{"path":"bug.py"}',
                        },
                    }
                ],
            }
            if number < 4
            else {"role": "assistant", "content": "Completed bounded investigation"}
        )
        return httpx.Response(
            200, json={"choices": [{"message": message}], "usage": {"completion_tokens": 100}}
        )

    async def tool(name, arguments):
        return "Citable sanitized source"

    async def progress(kind, payload):
        if kind == "model_usage":
            usage_events.append(payload)

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

    assert asyncio.run(run()) == "Completed bounded investigation"
    assert len(requests) == 4
    assert usage_events[-1]["budget_remaining"] == 3696
    assert all(v["usage_source"] == "provider_reported" for v in usage_events)


@pytest.mark.parametrize("usage", [None, {"completion_tokens": -1}, {"completion_tokens": True}])
def test_missing_or_invalid_usage_reserves_the_full_allocation_without_expanding_budget(usage):
    records = []

    def handle(request):
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "Analysis complete"}}], "usage": usage}
        )

    async def progress(kind, payload):
        if kind == "model_usage":
            records.append(payload)

    async def tool(name, arguments):
        raise AssertionError("No tool requested")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await run_api_tools(
                client,
                base_url="https://openrouter.ai/api/v1",
                api_key="test-key",
                config={"primary_model_id": "selected/model", "max_output_tokens": 512},
                messages=[{"role": "user", "content": "inspect"}],
                tools=[],
                handler=tool,
                progress=progress,
            )

    assert asyncio.run(run()) == "Analysis complete"
    assert records == [
        {"completion_tokens": 512, "budget_remaining": 0, "usage_source": "reserved_unreported"}
    ]
