"""Fail-open Sentry capture. Only explicitly permitted serialized evidence leaves the process."""

from __future__ import annotations

import atexit
import os
import re
from typing import Any, cast

from sentry_sdk.types import Event

_INITIALIZED = False
_TOKEN = re.compile(r"^[A-Za-z0-9_.:@/-]{1,160}$")


def _token(value: Any) -> str | None:
    return value if isinstance(value, str) and _TOKEN.fullmatch(value) else None


def sanitize_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Rebuild, rather than blacklist, the event; preserve exception ordering and frame order."""
    clean = {
        key: event[key]
        for key in (
            "event_id",
            "timestamp",
            "level",
            "platform",
            "release",
            "environment",
            "dist",
            "sdk",
            "type",
            "start_timestamp",
        )
        if key in event
    }
    values = []
    for exception in event.get("exception", {}).get("values", [])[:16]:
        item: dict[str, Any] = {
            "type": _token(exception.get("type")) or "Error",
            "value": "[redacted]",
        }
        frames = []
        for frame in exception.get("stacktrace", {}).get("frames", [])[-100:]:
            filename = str(frame.get("filename", ""))
            filename = filename.replace("\\", "/")
            # Absolute host/user paths are never exported.
            match = re.search(r"(?:^|/)(app/[^?#]+|src/[^?#]+|platform/[^?#]+)$", filename)
            safe: dict[str, Any] = {}
            if match and ".." not in match[1].split("/"):
                safe["filename"] = match[1][:240]
            function = _token(frame.get("function"))
            if function:
                safe["function"] = function
            if isinstance(frame.get("lineno"), int):
                safe["lineno"] = frame["lineno"]
            frames.append(safe)
        if frames:
            item["stacktrace"] = {"frames": frames}
        values.append(item)
    if values:
        clean["exception"] = {"values": values}
    tags = {}
    for key in (
        "service",
        "diagnostic_event_id",
        "request_id",
        "operation_id",
        "job_id",
        "resource_id",
        "stage",
        "error_code",
    ):
        value = _token(event.get("tags", {}).get(key))
        if value:
            tags[key] = value
    clean["tags"] = tags
    # Rich SDK contexts (request, AI, device identity) and arbitrary span attributes are excluded.
    trace = event.get("contexts", {}).get("trace", {})
    safe_trace = {
        key: trace[key]
        for key in ("trace_id", "span_id", "parent_span_id", "status")
        if _token(trace.get(key))
    }
    if safe_trace:
        clean["contexts"] = {"trace": safe_trace}
    if event.get("type") == "transaction":
        clean["transaction"] = "request"
        clean["spans"] = []
    return clean


def _before_send(event: Event, hint: dict[str, Any]) -> Event:
    return cast(Event, sanitize_event(cast(dict[str, Any], event), hint))


def initialize_sentry(service: str) -> bool:
    global _INITIALIZED
    if _INITIALIZED or not os.environ.get("SENTRY_DSN"):
        return _INITIALIZED
    try:
        import sentry_sdk
        from sentry_sdk.integrations.dedupe import DedupeIntegration
        from sentry_sdk.integrations.excepthook import ExcepthookIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.threading import ThreadingIntegration

        commit = os.environ.get("APP_BUILD_SHA", "")
        release = f"fitician-{service}@{commit}" if re.fullmatch(r"[a-f0-9]{40}", commit) else None
        sentry_sdk.init(
            dsn=os.environ["SENTRY_DSN"],
            environment=(
                os.environ.get("DIAGNOSTICS_ENVIRONMENT")
                or os.environ.get("SENTRY_ENVIRONMENT")
                or os.environ.get("APP_ENV")
                or "development"
            ),
            release=release,
            default_integrations=False,
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
                DedupeIntegration(),
                ExcepthookIntegration(),
                ThreadingIntegration(propagate_scope=False),
            ],
            send_default_pii=False,
            include_local_variables=False,
            max_request_body_size="never",
            max_breadcrumbs=0,
            sample_rate=1.0,
            traces_sample_rate=0.05,
            before_send=_before_send,
            before_send_transaction=_before_send,
            before_breadcrumb=lambda breadcrumb, hint: None,
            transport_queue_size=256,
            shutdown_timeout=2,
            https_proxy=os.environ.get("SENTRY_HTTPS_PROXY") or None,
            enable_logs=False,
        )
        sentry_sdk.set_tag("service", service)
        atexit.register(flush_sentry)
        _INITIALIZED = True
    except Exception:
        return False
    return True


def flush_sentry() -> None:
    if _INITIALIZED:
        try:
            import sentry_sdk

            sentry_sdk.flush(timeout=2)
        except Exception:
            pass


def capture_operational_exception(error: BaseException, event_id: str) -> str | None:
    """Capture the original handled exception independently of diagnostics persistence."""
    if not _INITIALIZED:
        return None
    try:
        import sentry_sdk

        with sentry_sdk.new_scope() as scope:
            scope.set_tag("diagnostic_event_id", event_id)
            return sentry_sdk.capture_exception(error)
    except Exception:
        return None
