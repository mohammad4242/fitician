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
