#!/usr/bin/env python3
"""Probe the isolated Iran-to-NL Agent path; also acts as a safe fake Codex CLI."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from io import BytesIO
from pathlib import Path


def _fake_codex(args: list[str]) -> int:
    if args and args[0] == "workspace-cleanup":
        if len(args) != 2:
            return 2
        image_path = Path(args[1])
        if not str(image_path).startswith("/tmp/fitician-agent/") or image_path.exists():
            return 1
        print("WORKSPACE_CLEANUP: removed")
        return 0
    if args == ["--version"]:
        print("codex-cli 0.0.0-split-test")
        return 0
    if args[:2] == ["login", "status"]:
        print("not authenticated")
        return 1

    try:
        output_file = Path(args[args.index("--output-last-message") + 1])
        image_file = Path(args[args.index("--image") + 1])
        image_data = image_file.read_bytes()
        result = {
            "image_sha256": hashlib.sha256(image_data).hexdigest(),
            "image_bytes": len(image_data),
            "agent_workspace_image": str(image_file),
        }
        output_file.write_text(json.dumps(result), encoding="utf-8")
        return 0
    except (OSError, ValueError, IndexError) as error:
        print(f"split test fake runner failed: {type(error).__name__}", file=sys.stderr)
        return 2


def _connected_probe(base_url: str, token: str) -> None:
    import httpx
    from PIL import Image
    from pydantic import SecretStr

    from app.body_analysis.providers.agent_service import AgentServiceProvider
    from app.body_analysis.providers.models import (
        AIProviderError,
        ImageInput,
        ModelRoute,
        StructuredGenerationRequest,
    )
    from app.config import Settings
    from app.private_media import PrivateMediaResolver

    client = httpx.Client(timeout=3, trust_env=False)
    assert client.get(f"{base_url}/healthz").status_code == 200
    denied = client.get(f"{base_url}/v1/capabilities")
    assert denied.status_code == 401
    response = client.get(
        f"{base_url}/v1/capabilities", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, "authenticated capabilities probe failed"
    runners = response.json().get("runners")
    assert isinstance(runners, list), "capabilities runners must be an array"
    codex = next((item for item in runners if item.get("agent") == "codex"), None)
    assert isinstance(codex, dict) and codex.get("installed") is True
    assert any(
        model.get("model_id") == "split-test-model" and model.get("supports_image_input")
        for model in codex.get("models", [])
    ), "fake runner image capability is missing"
    profile = next(
        (
            item
            for item in codex.get("profiles", [])
            if item.get("model_id") == "split-test-model" and item.get("supports_image_input")
        ),
        None,
    )
    assert isinstance(profile, dict), "fake runner image profile is missing"
    try:
        client.get("http://split-agent:9001/healthz", timeout=1)
    except httpx.RequestError:
        pass
    else:
        raise AssertionError("Iran network can bypass the ingress proxy to reach the Agent")
    client.close()

    private_root = Path("/tmp/split-test-private")
    body_root = private_root / "body"
    food_root = private_root / "food"
    image_key = "ab/abcdef0123456789abcdef0123456789.jpg"
    image_path = body_root / image_key
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_buffer = BytesIO()
    Image.new("RGB", (16, 12), (32, 96, 160)).save(image_buffer, format="JPEG", quality=87)
    image_bytes = image_buffer.getvalue()
    image_path.write_bytes(image_bytes)
    settings = Settings(
        app_env="test",
        cookie_secure=False,
        session_cookie_name="fitician_session",
        media_storage_backend="local",
        media_root=private_root / "public",
        body_photo_storage_root=body_root,
        food_photo_storage_root=food_root,
        _env_file=None,
    )
    provider_responses: list[tuple[int, str | None, str | None]] = []

    async def record_provider_response(response: httpx.Response) -> None:
        if response.status_code >= 400:
            await response.aread()
            try:
                detail = response.json().get("error", {}).get("code")
                message = response.json().get("error", {}).get("message")
            except (ValueError, AttributeError):
                detail = None
                message = None
            provider_responses.append((response.status_code, detail, message))

    provider_client = httpx.AsyncClient(
        trust_env=False,
        event_hooks={"response": [record_provider_response]},
    )
    provider = AgentServiceProvider(
        provider_client,
        base_url=base_url,
        token=SecretStr(token),
        agent_name="codex",
        profile_id=profile["profile_id"],
        timeout_seconds=60,
        private_media_resolver=PrivateMediaResolver(settings),
    )
    request = StructuredGenerationRequest(
        system_prompt="Return the image hash and byte count from the supplied image.",
        input_payload={"probe": "split-region-image-transport"},
        response_schema={
            "type": "object",
            "properties": {
                "image_sha256": {"type": "string"},
                "image_bytes": {"type": "integer"},
                "agent_workspace_image": {"type": "string"},
            },
            "required": ["image_sha256", "image_bytes"],
            "additionalProperties": False,
        },
        schema_name="split_region_image_probe",
        route=ModelRoute(primary_model="split-test-model"),
        temperature=0,
        max_output_tokens=64,
    )
    image = ImageInput(
        label="split-test-image",
        mime_type="image/jpeg",
        storage_scope="body",
        storage_key=image_key,
    )
    async def analyze_and_close():
        try:
            return await provider.analyze_images(request, images=(image,))
        finally:
            await provider_client.aclose()

    try:
        result = asyncio.run(analyze_and_close())
    except AIProviderError as error:
        print(
            f"IMAGE_REQUEST_FAILED: code={error.code.value} status={error.provider_status_code} "
            f"agent_error={provider_responses[-1][1:] if provider_responses else None}",
            file=sys.stderr,
        )
        raise
    expected_hash = hashlib.sha256(image_bytes).hexdigest()
    assert result.payload["image_sha256"] == expected_hash
    assert result.payload["image_bytes"] == len(image_bytes)
    workspace_image = Path(result.payload["agent_workspace_image"])
    assert "/tmp/fitician-agent/" in str(workspace_image)
    assert image_path.exists(), "Iran private-media source changed during transport"
    print("CONNECTED: auth, capabilities, proxy isolation, resolver multipart passed")
    print(f"WORKSPACE_IMAGE={workspace_image}")


def _disconnected_probe() -> None:
    import httpx
    from pydantic import SecretStr

    from app.body_analysis.providers.agent_service import AgentServiceProvider
    from app.body_analysis.providers.models import (
        AIProviderError,
        ModelRoute,
        ProviderErrorCode,
        StructuredGenerationRequest,
    )

    for base_url in ("http://127.0.0.1:8000", "http://iran-backend-2:8000"):
        response = httpx.get(f"{base_url}/readyz", timeout=5, trust_env=False)
        assert response.status_code == 200, f"Backend API unavailable: {base_url}"
        assert response.json().get("status") == "ok"

    async def request_agent_while_disconnected() -> None:
        client = httpx.AsyncClient(trust_env=False)
        provider = AgentServiceProvider(
            client,
            base_url="http://split-gateway:9001",
            token=SecretStr(os.environ["AGENT_SERVICE_TOKEN"]),
            agent_name="codex",
            timeout_seconds=2,
            connect_timeout_seconds=1,
        )
        request = StructuredGenerationRequest(
            system_prompt="Return an empty object.",
            input_payload={"probe": "agent-disconnected"},
            response_schema={"type": "object", "properties": {}, "additionalProperties": False},
            schema_name="split_disconnected_probe",
            route=ModelRoute(primary_model="split-test-model"),
            max_output_tokens=16,
        )
        try:
            try:
                await provider.generate_structured_text(request)
            except AIProviderError as error:
                assert error.code in {
                    ProviderErrorCode.PROVIDER_UNAVAILABLE,
                    ProviderErrorCode.CONNECTION_FAILURE,
                }
                safe_message = error.safe_message.lower()
                assert "split-gateway" not in safe_message
                assert "split-agent" not in safe_message
                assert "private" not in safe_message
                print(f"DISCONNECTED_PROVIDER: normalized={error.code.value} sanitized=true")
            else:
                raise AssertionError("Agent request unexpectedly succeeded while Agent was stopped")
        finally:
            await client.aclose()

    asyncio.run(request_agent_while_disconnected())
    print("DISCONNECTED: both Backend API replicas remain healthy")


def main() -> int:
    if sys.argv[1:2] == ["workspace-cleanup"]:
        return _fake_codex(sys.argv[1:])
    if "--output-last-message" in sys.argv[1:]:
        return _fake_codex(sys.argv[1:])
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("connected", "disconnected"))
    parser.add_argument("--agent-url", default="http://split-gateway:9001")
    args = parser.parse_args()
    if args.mode == "connected":
        token = os.environ["AGENT_SERVICE_TOKEN"]
        _connected_probe(args.agent_url, token)
    else:
        _disconnected_probe()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
