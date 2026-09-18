from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

_REDACTED = "[REDACTED]"
_SECRET_KEY_PARTS = frozenset(
    {
        "authorization",
        "cookie",
        "credential",
        "key",
        "password",
        "private",
        "secret",
        "token",
    }
)
_SAFE_FIELDS = frozenset(
    {
        "attempt",
        "duration_ms",
        "error_code",
        "event",
        "instance",
        "job_id",
        "level",
        "logger",
        "provider",
        "queue",
        "request_id",
        "service",
        "status",
        "worker_id",
    }
)


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized.split("_") for part in _SECRET_KEY_PARTS)


def redact_fields(value: object, *, key: str | None = None, depth: int = 0) -> object:
    """Return a bounded, JSON-safe value with credential-like fields removed."""

    if key is not None and _is_secret_key(key):
        return _REDACTED
    if depth > 4:
        return "[TRUNCATED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:500]
    if isinstance(value, Mapping):
        return {
            str(item_key)[:80]: redact_fields(item_value, key=str(item_key), depth=depth + 1)
            for item_key, item_value in value.items()
            if isinstance(item_key, str)
        }
    if isinstance(value, (list, tuple, set)):
        return [redact_fields(item, depth=depth + 1) for item in list(value)[:50]]
    return str(value)[:500]


class JsonLogFormatter(logging.Formatter):
    """Small allow-listed JSON formatter for service and worker logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name[:120],
            "event": record.getMessage()[:500],
        }
        for field in _SAFE_FIELDS:
            if field == "event":
                continue
            if not hasattr(record, field):
                continue
            value = redact_fields(getattr(record, field), key=field)
            if value is not None:
                payload[field] = value
        if record.exc_info and record.exc_info[0] is not None:
            payload["error_code"] = record.exc_info[0].__name__[:120]
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_structured_logging() -> None:
    """Use the safe formatter on existing process handlers without duplicating them."""

    root = logging.getLogger()
    if not root.handlers:
        handler: logging.Handler = logging.StreamHandler()
        root.addHandler(handler)
    formatter = JsonLogFormatter()
    for handler in root.handlers:
        handler.setFormatter(formatter)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit an allow-listed structured event without payloads or secrets."""

    safe_fields = {
        key: redact_fields(value, key=key)
        for key, value in fields.items()
        if key in _SAFE_FIELDS and key != "event"
    }
    logger.info(event[:500], extra=safe_fields)
