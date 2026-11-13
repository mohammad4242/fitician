"""Shared declared limits; reject unsupported settings instead of silently clamping."""

from typing import Any

MIN_TIMEOUT = 10
MAX_TIMEOUT = 600
MIN_API_TOKENS = 128
MAX_API_TOKENS = 16384


def validate_runtime_config(config: dict[str, Any]) -> None:
    timeout = config.get("timeout_seconds", 420)
    if type(timeout) is not int or not MIN_TIMEOUT <= timeout <= MAX_TIMEOUT:
        raise ValueError("debug_runtime_options_unsupported")
    if config.get("execution_backend", "api") == "api":
        tokens = config.get("max_output_tokens", 4096)
        if type(tokens) is not int or not MIN_API_TOKENS <= tokens <= MAX_API_TOKENS:
            raise ValueError("debug_runtime_options_unsupported")
