import asyncio
import json
from uuid import uuid4

import httpx
import pytest

KEY = "sk-or-v1-" + "a" * 64


def credential(path):
    value = {
        "purpose": "fitician_debug_agent",
        "provider": "openrouter",
        "revision": str(uuid4()),
        "FITICIAN_DEBUG_OPENROUTER_API_KEY": KEY,
    }
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return value


def test_dedicated_credential_is_private_purpose_bound_and_never_in_environment(
    tmp_path, monkeypatch
):
    from app.debugging.germany_provider import load_credential

    path = tmp_path / "model-api.json"
    value = credential(path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "production-key-must-not-be-read")
    item = load_credential(path)
    assert item.revision == value["revision"] and item.key == KEY
    assert KEY not in repr(item)
    path.chmod(0o644)
    with pytest.raises(ValueError, match="dedicated_model_credential_invalid"):
        load_credential(path)
    path.chmod(0o600)
    value["purpose"] = "production"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="dedicated_model_credential_invalid"):
        load_credential(path)


def test_missing_file_never_falls_back_to_any_application_or_github_key(tmp_path, monkeypatch):
    from app.debugging.germany_provider import load_credential

    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-github")
    with pytest.raises(ValueError, match="dedicated_model_credential_required"):
        load_credential(tmp_path / "absent.json")


@pytest.mark.parametrize(
    "patch",
    [
        {"limit": None},
        {"limit": 2},
        {"limit_reset": "monthly"},
        {"limit_remaining": 0},
        {"is_management_key": True},
        {"include_byok_in_limit": False},
    ],
)
def test_provider_spending_policy_fails_closed_before_inference(tmp_path, patch):
    from app.debugging.germany_provider import GermanyProvider

    p = tmp_path / "model-api.json"
    credential(p)
    requests = []

    def handle(request):
        requests.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "data": {
                    "limit": 1,
                    "limit_reset": "daily",
                    "limit_remaining": 1,
                    "include_byok_in_limit": True,
                    "is_management_key": False,
                    **patch,
                }
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            provider = GermanyProvider(p, tmp_path / "state", client)
            with pytest.raises(ValueError, match="dedicated_model_spending_policy_required"):
                await provider.verify()

    asyncio.run(run())
    assert requests == ["/api/v1/key"]


def test_durable_rate_reservations_survive_restart_and_unknown_dispatch(tmp_path):
    from app.debugging.germany_provider import reserve_request

    state = tmp_path / "state"
    state.mkdir()
    for _ in range(6):
        reserve_request(state, now=100)
    with pytest.raises(ValueError, match="provider_rate_limited"):
        reserve_request(state, now=101)
    reserve_request(state, now=161)
    assert len(json.loads((state / "model-rate.json").read_text())["requests"]) == 1
    assert (state / "model-rate.json").stat().st_mode & 0o777 == 0o600


def test_selected_model_and_real_tool_dispatch_use_only_the_dedicated_key(tmp_path):
    from app.debugging.germany_provider import GermanyProvider

    p = tmp_path / "model-api.json"
    value = credential(p)
    requests = []
    calls = []
    events = []

    def handle(request):
        assert request.headers["Authorization"] == "Bearer " + KEY
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 1,
                        "limit_reset": "daily",
                        "limit_remaining": 1,
                        "include_byok_in_limit": True,
                        "is_management_key": False,
                    }
                },
            )
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "chosen/model", "supported_parameters": ["tools", "tool_choice"]}
                    ]
                },
            )
        body = json.loads(request.content)
        requests.append(body)
        message = (
            {
                "role": "assistant",
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
            if len(requests) == 1
            else {"role": "assistant", "content": "مدرک ثبت شد."}
        )
        return httpx.Response(
            200, json={"choices": [{"message": message}], "usage": {"completion_tokens": 50}}
        )

    async def tool(name, args):
        calls.append((name, args))
        return "return a - b"

    async def progress(kind, payload):
        events.append((kind, payload))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            provider = GermanyProvider(p, tmp_path / "state", client)
            return await provider.execute(
                config={
                    "primary_model_id": "chosen/model",
                    "execution_backend": "api",
                    "max_output_tokens": 512,
                },
                messages=[{"role": "user", "content": "inspect"}],
                tools=[
                    {
                        "name": "fitician_read_file",
                        "description": "read",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"],
                        },
                    }
                ],
                handler=tool,
                progress=progress,
                allow_write=False,
                expected_revision=value["revision"],
            )

    result = asyncio.run(run())
    assert result["model"] == "chosen/model" and result["mode"] == "api_tools"
    assert calls == [("fitician_read_file", {"path": "bug.py"})]
    assert len(requests) == 2 and all(r["model"] == "chosen/model" for r in requests)
    assert KEY not in json.dumps(events) + json.dumps(result)
