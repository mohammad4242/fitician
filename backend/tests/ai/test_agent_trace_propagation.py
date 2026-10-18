from __future__ import annotations

import asyncio
import base64
from collections.abc import Awaitable

import httpx

from app.body_analysis.providers.agent_service import AgentServiceProvider
from app.body_analysis.providers.models import ImageInput, ModelRoute, StructuredGenerationRequest
from app.observability.diagnostics_runtime import RequestDiagnosticsContext, bind_request_context


def _run[T](awaitable: Awaitable[T]) -> T:
    return asyncio.run(awaitable)


def _request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        system_prompt="Return the requested object.",
        input_payload={"test": True},
        response_schema={"type": "object", "properties": {"value": {"type": "integer"}}},
        schema_name="trace_test",
        route=ModelRoute(primary_model="gemini-test"),
        temperature=0,
        max_output_tokens=32,
    )


def test_json_multipart_and_stored_requests_propagate_trace_and_create_spans() -> None:
    trace_id = "1" * 32
    root_span_id = "2" * 16
    events = []
    traceparents: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/healthz":
            return httpx.Response(200, json={"status": "ok"})
        traceparents[request.url.path] = request.headers["traceparent"]
        return httpx.Response(
            200,
            json={
                "payload": {"value": 1},
                "agent": "antigravity",
                "model_id": "gemini-test",
                "request_id": "agent-req-1",
                "duration_seconds": 0.1,
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AgentServiceProvider(
        client,
        base_url="http://agent-service:9001",
        token="test-token",
        agent_name="antigravity",
    )
    context = RequestDiagnosticsContext(
        submit=lambda event, _user_id: events.append(event) or True,
        request_id="request-trace-test",
        operation_id="operation-trace-test",
        operation="body_analysis",
        trace_id=trace_id,
        root_span_id=root_span_id,
    )

    async def run_requests() -> None:
        with bind_request_context(context):
            await provider.generate_structured_text(_request())
            inline = ImageInput(
                label="front",
                mime_type="image/jpeg",
                base64_data=base64.b64encode(b"image-bytes").decode("ascii"),
            )
            await provider.analyze_images(_request(), images=(inline,))
            stored = ImageInput(
                label="front",
                mime_type="image/jpeg",
                storage_scope="body",
                storage_key="ab/abcdef0123456789abcdef0123456789.jpg",
            )
            await provider.analyze_images(_request(), images=(stored,))
        await client.aclose()

    _run(run_requests())

    assert set(traceparents) == {
        "/v1/generate",
        "/v1/analyze-images",
        "/v1/analyze-stored-images",
    }
    for value in traceparents.values():
        version, observed_trace_id, parent_span_id, flags = value.split("-")
        assert version == "00"
        assert observed_trace_id == trace_id
        assert parent_span_id != root_span_id
        assert flags == "01"
    spans = [
        event
        for event in events
        if event.record_type == "span" and event.stage == "agent_service_call"
    ]
    assert len(spans) >= 4
    assert {event.outcome for event in spans} == {"started", "success"}
    assert all(event.trace_id == trace_id for event in spans)
