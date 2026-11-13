"""Bounded OpenRouter tool orchestration. Execution is supplied by the scoped gateway."""

from __future__ import annotations

import json
from typing import Any, cast

import httpx
from jsonschema import ValidationError, validate

from .appserver import ProgressHandler, ToolHandler
from .limits import validate_runtime_config
from .privacy import sanitize_text


async def model_supports_tools(
    client: httpx.AsyncClient, base_url: str, api_key: str, model: str
) -> bool:
    async with client.stream(
        "GET", base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {api_key}"}
    ) as response:
        if response.status_code != 200:
            raise ValueError("model_capability_discovery_failed")
        payload = bytearray()
        async for chunk in response.aiter_bytes():
            payload.extend(chunk)
            if len(payload) > 8_388_608:
                raise ValueError("model_catalog_too_large")
        catalog = json.loads(payload)
    for item in catalog.get("data", []):
        if item.get("id") == model:
            parameters = item.get("supported_parameters", [])
            return "tools" in parameters and "tool_choice" in parameters
    raise ValueError("selected_model_not_available")


async def run_api_tools(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    api_key: str,
    config: dict[str, Any],
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    handler: ToolHandler,
    progress: ProgressHandler,
) -> str:
    model = config.get("primary_model_id")
    if not isinstance(model, str) or not model:
        raise ValueError("model_not_configured")
    catalog = {tool["name"]: tool for tool in tools}
    history = list(messages)
    validate_runtime_config(config)
    remaining = int(config.get("max_output_tokens", 4096))
    provider: dict[str, Any] = {"data_collection": "deny", "allow_fallbacks": False}
    if "zero_data_retention" in config.get("routing_restrictions", []):
        provider["zdr"] = True
    if "require_supported_parameters" in config.get("routing_restrictions", []):
        provider["require_parameters"] = True
    for step in range(8):
        if remaining < 128 or len(json.dumps(history).encode()) > 262144:
            raise ValueError("tool_run_budget_exhausted")
        allocation = min(remaining, 2048)
        await progress("model_request", {"step": step + 1, "model": model})
        async with client.stream(
            "POST",
            base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": history,
                "max_tokens": allocation,
                "provider": provider,
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool["inputSchema"],
                        },
                    }
                    for tool in tools
                ],
                "tool_choice": "auto",
            },
        ) as response:
            if response.status_code != 200:
                raise ValueError("provider_tool_request_failed")
            payload = bytearray()
            async for chunk in response.aiter_bytes():
                payload.extend(chunk)
                if len(payload) > 1_048_576:
                    raise ValueError("provider_response_too_large")
            body = json.loads(payload)
        message = body["choices"][0]["message"]
        usage = body.get("usage")
        used = usage.get("completion_tokens") if isinstance(usage, dict) else None
        reported = type(used) is int and 0 < used <= allocation
        if type(used) is int and used > allocation:
            raise ValueError("provider_usage_invalid")
        consumed = cast(int, used) if reported else allocation
        remaining -= consumed
        await progress(
            "model_usage",
            {
                "completion_tokens": consumed,
                "budget_remaining": remaining,
                "usage_source": "provider_reported" if reported else "reserved_unreported",
            },
        )
        calls = message.get("tool_calls") or []
        if not calls:
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("provider_invalid_response")
            return sanitize_text(content)
        if len(calls) > 8:
            raise ValueError("too_many_tool_calls")
        history.append({"role": "assistant", "content": None, "tool_calls": calls})
        for call in calls:
            function = call.get("function", {})
            name = function.get("name", "")
            if name not in catalog:
                output = "tool_not_authorized"
            else:
                try:
                    arguments = json.loads(function["arguments"])
                    validate(arguments, catalog[name]["inputSchema"])
                    await progress("tool_started", {"tool": name, "step": step + 1})
                    output = sanitize_text(await handler(name, arguments))
                    await progress("tool_completed", {"tool": name, "step": step + 1})
                except (ValidationError, ValueError, OSError):
                    output = "tool_rejected_or_failed"
                    await progress("tool_failed", {"tool": name})
            history.append({"role": "tool", "tool_call_id": call["id"], "content": output[:32000]})
    raise ValueError("tool_run_budget_exhausted")
