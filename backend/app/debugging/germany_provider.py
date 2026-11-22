"""Germany-only model credentials and fail-closed OpenRouter execution policy."""

from __future__ import annotations

import fcntl
import json
import math
import os
import re
import stat
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

from .api_runtime import model_supports_tools, request_analysis, run_api_tools
from .appserver import ProgressHandler, ToolHandler

BASE_URL = "https://openrouter.ai/api/v1"
MAX_DAILY_USD = 1.0
REQUESTS_PER_MINUTE = 6


@dataclass(frozen=True)
class ModelCredential:
    revision: str
    key: str = field(repr=False)


def load_credential(path: Path) -> ModelCredential:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        raise ValueError("dedicated_model_credential_required") from None
    except OSError:
        raise ValueError("dedicated_model_credential_invalid") from None
    try:
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                raise ValueError
            raw = source.read(8193)
            if len(raw) > 8192:
                raise ValueError
        value = json.loads(raw)
        if set(value) != {"purpose", "provider", "revision", "FITICIAN_DEBUG_OPENROUTER_API_KEY"}:
            raise ValueError
        key = value["FITICIAN_DEBUG_OPENROUTER_API_KEY"]
        revision = str(UUID(value["revision"]))
        if (
            value["purpose"] != "fitician_debug_agent"
            or value["provider"] != "openrouter"
            or not isinstance(key, str)
            or not re.fullmatch(r"sk-or-v1-[A-Za-z0-9_-]{32,128}", key)
        ):
            raise ValueError
        return ModelCredential(revision, key)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, AttributeError):
        raise ValueError("dedicated_model_credential_invalid") from None


def reserve_request(state: Path, *, now: float | None = None) -> None:
    """Reserve before dispatch, including unknown outcomes. No paid request auto-retry."""
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = time.time() if now is None else now
    path = state / "model-rate.json"
    fd = os.open(state / "model-rate.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        history: list[float] = []
        if path.exists():
            if path.is_symlink() or path.stat().st_size > 4096:
                raise ValueError("dedicated_model_rate_state_invalid")
            try:
                history = json.loads(path.read_text())["requests"]
                if len(history) > REQUESTS_PER_MINUTE or any(
                    type(t) not in {int, float} or not math.isfinite(t) for t in history
                ):
                    raise ValueError
            except (ValueError, TypeError, KeyError):
                raise ValueError("dedicated_model_rate_state_invalid") from None
        history = [t for t in history if stamp - t < 60]
        if len(history) >= REQUESTS_PER_MINUTE:
            raise ValueError("provider_rate_limited")
        history.append(stamp)
        temporary = path.with_suffix(".new")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as output:
            os.fchmod(output.fileno(), 0o600)
            json.dump({"requests": history}, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)


async def bounded_json(response: httpx.Response) -> dict[str, Any]:
    if response.status_code == 429:
        raise ValueError("provider_rate_limited")
    if response.status_code != 200:
        raise ValueError("provider_rejected")
    data = bytearray()
    async for chunk in response.aiter_bytes():
        data.extend(chunk)
        if len(data) > 65536:
            raise ValueError("provider_response_too_large")
    result = json.loads(data)
    if not isinstance(result, dict):
        raise ValueError("provider_invalid_response")
    return result


class GermanyProvider:
    def __init__(self, credential_file: Path, state: Path, client: httpx.AsyncClient):
        self.credential_file = credential_file
        self.state = state
        self.client = client

    async def verify(self) -> ModelCredential:
        credential = load_credential(self.credential_file)
        try:
            async with self.client.stream(
                "GET",
                BASE_URL + "/key",
                headers={"Authorization": "Bearer " + credential.key},
                timeout=10,
            ) as response:
                data = (await bounded_json(response)).get("data", {})
            limit, remaining = data.get("limit"), data.get("limit_remaining")
            if (
                type(limit) not in {float, int}
                or not math.isfinite(limit)
                or not 0 < limit <= MAX_DAILY_USD
                or type(remaining) not in {float, int}
                or not math.isfinite(remaining)
                or not 0 < remaining <= limit
                or data.get("limit_reset") != "daily"
                or data.get("include_byok_in_limit") is not True
                or data.get("is_management_key") is True
                or data.get("is_provisioning_key") is True
            ):
                raise ValueError("dedicated_model_spending_policy_required")
            return credential
        except httpx.HTTPError:
            raise ValueError("provider_unreachable") from None
        except (KeyError, TypeError, AttributeError, json.JSONDecodeError):
            raise ValueError("provider_invalid_response") from None

    async def execute(
        self,
        *,
        config: dict[str, Any],
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        handler: ToolHandler,
        progress: ProgressHandler,
        allow_write: bool,
        expected_revision: str | None,
    ) -> dict[str, Any]:
        credential = await self.verify()
        if credential.revision != expected_revision:
            raise ValueError("dedicated_model_credential_changed")
        model = config.get("primary_model_id")
        if not isinstance(model, str) or not model:
            raise ValueError("model_not_configured")
        if config.get("provider", "openrouter") != "openrouter":
            raise ValueError("debug_provider_not_supported")
        if any(
            m.get("role") not in {"system", "user", "assistant"}
            or not isinstance(m.get("content"), str)
            for m in messages
        ):
            raise ValueError("provider_message_not_authorized")

        async def before_request() -> None:
            reserve_request(self.state)

        try:
            supports_tools = await model_supports_tools(
                self.client, BASE_URL, credential.key, model
            )
            mode = "api_tools" if supports_tools else "analysis_only"
            await progress("capabilities", {"mode": mode, "model": model})
            if supports_tools:
                content = await run_api_tools(
                    self.client,
                    base_url=BASE_URL,
                    api_key=credential.key,
                    config=config,
                    messages=messages,
                    tools=tools,
                    handler=handler,
                    progress=progress,
                    before_request=before_request,
                )
            else:
                if allow_write:
                    raise ValueError("repair_executor_not_configured")
                content = await request_analysis(
                    self.client,
                    base_url=BASE_URL,
                    api_key=credential.key,
                    config=config,
                    messages=messages,
                    before_request=before_request,
                )
            return {"output": content, "model": model, "mode": mode}
        except httpx.HTTPError:
            raise ValueError("provider_unreachable") from None
        except (KeyError, IndexError, TypeError):
            raise ValueError("provider_invalid_response") from None
