from __future__ import annotations

import asyncio
import base64
from collections.abc import Awaitable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, TypeVar

import httpx
from pydantic import SecretStr

from app.ai.task_provider import build_task_provider
from app.body_analysis.admin_config.enums import AIExecutionBackend
from app.body_analysis.providers.agent_service import AgentServiceProvider
from app.body_analysis.providers.models import (
    AIProviderError,
    ImageInput,
    ModelRoute,
    ProviderErrorCode,
    StructuredGenerationRequest,
)
from app.config import Settings
from app.private_media import PrivateMediaResolver

T = TypeVar("T")


def _run[T](awaitable: Awaitable[T]) -> T:
    return asyncio.run(awaitable)


def _request(*, images: bool = False) -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        system_prompt="Return the requested object.",
        input_payload={"probe": True},
        response_schema={
            "type": "object",
            "properties": {
                "image_sha256": {"type": "string"},
                "image_bytes": {"type": "integer"},
            },
            "required": ["image_sha256", "image_bytes"] if images else [],
            "additionalProperties": False,
        },
        schema_name="remote_agent_probe",
        route=ModelRoute(primary_model="test-model"),
        temperature=0,
        max_output_tokens=128,
    )


def _output() -> dict[str, Any]:
    return {
        "payload": {"image_sha256": "", "image_bytes": 0},
        "agent": "codex",
        "model_id": "test-model",
        "request_id": "split-test-request",
        "duration_seconds": 0.01,
    }


def _configured_provider(client: httpx.AsyncClient):
    task = SimpleNamespace(
        execution_backend=AIExecutionBackend.AGENT_SERVICE,
        provider="agent_service",
        agent_name="codex",
        agent_model_id="test-model",
        agent_profile_id=None,
        timeout_seconds=9,
        routing_restrictions=(),
    )
    settings = SimpleNamespace(
        app_env="test",
        agent_service_base_url="https://de-agent.example.test",
        agent_service_token=SecretStr("split-test-token-" + "x" * 32),
        agent_service_max_image_bytes=8 * 1024 * 1024,
        agent_service_connect_timeout_seconds=2.5,
        media_storage_backend="local",
    )
    return build_task_provider(
        task,
        settings=settings,  # type: ignore[arg-type]
        http_client=client,
        agent_http_client=client,
    ).provider


def test_remote_agent_url_is_used_and_connection_errors_are_sanitized() -> None:
    seen: list[str] = []
    timeouts: list[dict[str, float]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        timeouts.append(request.extensions["timeout"])
        return httpx.Response(200, json=_output())

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    provider = _configured_provider(client)
    _run(provider.generate_structured_text(_request()))
    assert seen == ["https://de-agent.example.test/v1/generate"]
    assert timeouts[0]["connect"] == 2.5
    assert timeouts[0]["read"] == 9
    assert timeouts[0]["write"] == 9

    def disconnected(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private topology detail")

    disconnected_provider = _configured_provider(
        httpx.AsyncClient(transport=httpx.MockTransport(disconnected))
    )
    try:
        _run(disconnected_provider.generate_structured_text(_request()))
    except AIProviderError as error:
        assert error.code is ProviderErrorCode.CONNECTION_FAILURE
        assert "private topology detail" not in error.safe_message
    else:
        raise AssertionError("disconnected remote Agent must map to a safe connection error")


def test_remote_agent_image_bytes_are_resolved_and_sent_without_storage_refs(
    tmp_path: Path,
) -> None:
    image_bytes = b"private image bytes from Iran-side storage"
    image_key = "ab/abcdef0123456789abcdef0123456789.jpg"
    body_root = tmp_path / "body-photos"
    image_path = body_root / image_key
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(image_bytes)
    resolver = PrivateMediaResolver(
        Settings(
            app_env="test",
            cookie_secure=False,
            session_cookie_name="fitician_session",
            media_root=tmp_path / "media",
            body_photo_storage_root=body_root,
            food_photo_storage_root=tmp_path / "food-photos",
            _env_file=None,
        )
    )
    received: dict[str, Any] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        received["url"] = str(request.url)
        received["content_type"] = request.headers.get("content-type", "")
        received["body"] = request.content
        return httpx.Response(200, json=_output())

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    provider = AgentServiceProvider(
        client,
        base_url="https://de-agent.example.test",
        token=SecretStr("split-test-token-" + "x" * 32),
        agent_name="codex",
        timeout_seconds=9,
        private_media_resolver=resolver,
    )
    # The Agent receives multipart bytes from the backend's local private store.
    image = ImageInput(
        label="front",
        mime_type="image/jpeg",
        storage_scope="body",
        storage_key=image_key,
    )

    _run(provider.analyze_images(_request(images=True), images=(image,)))

    assert received["url"] == "https://de-agent.example.test/v1/analyze-images"
    assert received["content_type"].startswith("multipart/form-data;")
    assert image_bytes in received["body"]
    assert image_key.encode() not in received["body"]
    assert base64.b64encode(image_bytes) not in received["body"]
    assert b"storage_scope" not in received["body"]
    assert b"storage_key" not in received["body"]
