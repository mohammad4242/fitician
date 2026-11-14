import asyncio
import json

import httpx

from app.debugging.worker import request_analysis


def test_api_runtime_uses_selected_model_without_tools_or_fallback_and_scrubs_output():
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "Observed issue evidence-id. email=member@example.com"}}
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await request_analysis(
                client,
                base_url="https://openrouter.ai/api/v1",
                api_key="test-key",
                config={
                    "primary_model_id": "chosen/model",
                    "max_output_tokens": 1200,
                    "routing_restrictions": ["zero_data_retention"],
                },
                messages=[{"role": "user", "content": "inspect evidence-id"}],
            )

    output = asyncio.run(run())
    assert requests[0]["model"] == "chosen/model"
    assert "tools" not in requests[0]
    assert requests[0]["provider"]["allow_fallbacks"] is False
    assert requests[0]["provider"]["zdr"] is True
    assert "member@example.com" not in output


def test_debug_worker_honors_its_configured_heartbeat_path(tmp_path, monkeypatch):
    from contextlib import asynccontextmanager

    from app.debugging.worker import main
    from app.jobs import heartbeat, runtime
    from app.observability import sentry

    expected = tmp_path / "worker-health.json"
    seen = []

    @asynccontextmanager
    async def record(path, **kwargs):
        seen.append(path)
        yield

    monkeypatch.setenv("JOB_HEARTBEAT_PATH", str(expected))
    monkeypatch.setattr(heartbeat, "async_heartbeat", record)
    monkeypatch.setattr(runtime, "install_async_signal_handlers", lambda stop: stop.set())
    monkeypatch.setattr(sentry, "initialize_sentry", lambda service: False)
    asyncio.run(main())
    assert seen == [expected]
