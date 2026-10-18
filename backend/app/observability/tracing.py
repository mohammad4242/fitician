"""Bounded W3C span observations; no payloads or dependency parameters."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast

from starlette.types import ASGIApp, Message, Receive, Scope, Send

if TYPE_CHECKING:
    from .diagnostics_runtime import RequestDiagnosticsContext

from uuid import uuid4

from .diagnostics_schemas import EventInput

P = ParamSpec("P")
R = TypeVar("R")

_SUPPRESSED: ContextVar[bool] = ContextVar("diagnostics_suppressed", default=False)
_PARENT: ContextVar[str | None] = ContextVar("diagnostic_span_parent", default=None)
_TRACEPARENT = re.compile(r"^00-([a-f0-9]{32})-([a-f0-9]{16})-([a-f0-9]{2})$")


def parse_traceparent(value: str | None) -> tuple[str, str, str] | None:
    match = _TRACEPARENT.fullmatch(value or "")
    if match and int(match[1], 16) and int(match[2], 16):
        return match[1], match[2], match[3]
    return None


def current_context() -> RequestDiagnosticsContext | None:
    from .diagnostics_runtime import _REQUEST_CONTEXT

    return _REQUEST_CONTEXT.get()


def propagation_headers() -> dict[str, str]:
    context = current_context()
    if context is None:
        return {}
    parent = _PARENT.get() or context.root_span_id
    return {
        "traceparent": f"00-{context.trace_id}-{parent}-{'01' if context.trace_sampled else '00'}",
        "X-Correlation-ID": context.request_id,
    }


def deliver(event: EventInput) -> None:
    context = current_context()
    if context is None:
        return
    try:
        if context.trace_sampled:
            if not context.submit(event, context.user_id):
                context.trace_dropped += 1
        elif len(context.trace_buffer) < 256:
            context.trace_buffer.append(event)
        else:
            context.trace_dropped += 1
    except Exception:
        context.trace_dropped += 1


@dataclass
class Span:
    name: str
    component: str
    span_id: str = field(default_factory=lambda: uuid4().hex[:16])
    parent_span_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started: float = field(default_factory=time.perf_counter)
    ended: bool = False
    finished_at: datetime | None = None
    finished_duration_ms: int | None = None
    source_location: str | None = None
    http_status: int | None = None

    def observe(self, outcome: str, error: BaseException | None = None) -> None:
        try:
            self._observe(outcome, error)
        except Exception:
            context = current_context()
            if context is not None:
                context.trace_dropped += 1

    def _observe(self, outcome: str, error: BaseException | None = None) -> None:
        from .diagnostics_runtime import safe_exception_type, safe_source_location

        context = current_context()
        if context is None:
            return
        end = None if outcome == "started" else (self.finished_at or datetime.now(UTC))
        duration = (
            None
            if end is None
            else self.finished_duration_ms
            if self.finished_duration_ms is not None
            else min(86_400_000, max(0, round((time.perf_counter() - self.started) * 1000)))
        )
        deliver(
            EventInput(
                trace_id=context.trace_id,
                origin_platform=context.origin_platform,
                span_id=self.span_id,
                parent_span_id=self.parent_span_id,
                record_type="span",
                started_at=self.started_at,
                ended_at=end,
                offset_ms=max(0, round((self.started - context.trace_started) * 1000)),
                clock_domain=context.clock_domain,
                request_id=context.request_id,
                operation_id=context.operation_id,
                component=self.component,
                operation=context.operation,
                stage=self.name,
                platform=context.telemetry_platform,
                version=context.version,
                app_version=context.app_version,
                category="database_failure"
                if error and self.component == "database"
                else "application_bug"
                if error
                else "unknown",
                severity="error"
                if outcome == "failure"
                else "warning"
                if outcome in {"cancelled", "blocked"}
                else "info",
                error_code="SPAN_FAILED"
                if error or outcome in {"failure", "blocked", "timeout", "cancelled"}
                else "SPAN_STARTED"
                if end is None
                else "SPAN_COMPLETED",
                outcome=outcome,
                http_status=self.http_status,
                duration_ms=duration,
                retry_count=context.retry_count,
                resource_id=context.resource_id,
                exception_type=safe_exception_type(error),
                source_location=safe_source_location(error) or self.source_location,
                expected_span_count=context.span_count + 1,
                dropped_count=context.trace_dropped,
            )
        )

    def finish(self, outcome: str = "success", error: BaseException | None = None) -> None:
        if isinstance(error, TimeoutError):
            outcome = "timeout"
        if not self.ended:
            self.ended = True
            self.finished_at = datetime.now(UTC)
            self.finished_duration_ms = min(
                86_400_000, max(0, round((time.perf_counter() - self.started) * 1000))
            )
            self.observe(outcome, error)


def start_span(
    name: str, component: str, *, parent: str | None = None, critical: bool = False
) -> Span | None:
    context = current_context()
    if context is None or _SUPPRESSED.get() or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", name):
        return None
    dependency = component in {"database", "redis"}
    if context.span_count >= (96 if critical else 64) or (
        dependency and not critical and context.dependency_span_count >= 32
    ):
        context.trace_dropped += 1
        return None
    context.span_count += 1
    if dependency:
        context.dependency_span_count += 1
    current_parent = _PARENT.get()
    if (
        context.validation_span
        and context.validation_span.ended
        and current_parent == context.validation_span.span_id
    ):
        current_parent = context.root_span_id
    active = (
        context.active_stage if context.active_stage and not context.active_stage.ended else None
    )
    observed_parent = (
        active.span_id if active and current_parent == active.parent_span_id else current_parent
    )
    span = Span(name, component, parent_span_id=parent or observed_parent or context.root_span_id)
    span.observe("started")
    return span


@contextmanager
def timed_stage(name: str, *, component: str | None = None) -> Iterator[Span | None]:
    context = current_context()
    span = start_span(name, component or (context.component if context else "api"))
    if span is None:
        yield None
        return
    token = _PARENT.set(span.span_id)
    try:
        yield span
    except BaseException as error:
        if context is not None and (
            context.exception_stage is None or context.exception_stage[0] is not error
        ):
            context.exception_stage = (error, span.name)
        span.finish("failure" if isinstance(error, Exception) else "cancelled", error)
        raise
    else:
        span.finish()
    finally:
        _PARENT.reset(token)


def _endpoint_entered(name: str) -> None:
    context = current_context()
    if name == "business_logic" and context and context.validation_span:
        context.validation_span.finish()


def _endpoint_returned(name: str) -> None:
    context = current_context()
    if name == "business_logic" and context:
        context.response_span = start_span(
            "response_preparation", "api", parent=context.root_span_id, critical=True
        )


def traced(name: str, *, component: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Preserve signatures and results; never inspect arguments or payloads."""
    import inspect
    from functools import wraps

    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        code = getattr(function, "__code__", None)
        location = f"{code.co_filename.rsplit('/', 1)[-1]}:{code.co_firstlineno}" if code else None
        if inspect.iscoroutinefunction(function):

            @wraps(function)
            async def async_call(*args: P.args, **kwargs: P.kwargs) -> Any:
                _endpoint_entered(name)
                with timed_stage(name, component=component) as span:
                    if span is not None:
                        span.source_location = location
                    result = await function(*args, **kwargs)
                _endpoint_returned(name)
                return result

            return cast(Callable[P, R], async_call)

        @wraps(function)
        def sync_call(*args: P.args, **kwargs: P.kwargs) -> R:
            _endpoint_entered(name)
            with timed_stage(name, component=component) as span:
                if span is not None:
                    span.source_location = location
                result = function(*args, **kwargs)
            _endpoint_returned(name)
            return result

        return sync_call

    return decorate


def instrument_routes(routes: Any) -> None:
    """Apply the supported route-handler hook, including lazily included routers."""
    from fastapi.routing import APIRoute
    from starlette.routing import request_response

    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            instrument_routes(included.routes)
        if not isinstance(route, APIRoute) or getattr(route, "_diagnostics_instrumented", False):
            continue
        if not route.path.startswith("/api/") or "/diagnostics" in route.path:
            continue
        endpoint = traced("business_logic", component="api")(route.endpoint)
        route.endpoint = endpoint
        route.dependant.call = endpoint
        original = route.get_route_handler

        def handler_factory(original: Any = original) -> Any:
            handler = original()

            async def observed(request: Any) -> Any:
                context = current_context()
                if context is None:
                    return await handler(request)
                validation = start_span(
                    "validation_and_dependencies", "api", parent=context.root_span_id, critical=True
                )
                context.validation_span = validation
                token = _PARENT.set(validation.span_id if validation else context.root_span_id)
                try:
                    response = await handler(request)
                    if context.response_span:
                        context.response_span.http_status = response.status_code
                        context.response_span.finish()
                    return response
                except BaseException as error:
                    if context.exception_stage is None or context.exception_stage[0] is not error:
                        failing = (
                            context.response_span
                            if context.response_span and not context.response_span.ended
                            else validation
                        )
                        if failing:
                            context.exception_stage = (error, failing.name)
                    if validation:
                        validation.finish(
                            "failure" if isinstance(error, Exception) else "cancelled", error
                        )
                    if context.response_span:
                        context.response_span.finish(
                            "failure" if isinstance(error, Exception) else "cancelled", error
                        )
                    raise
                finally:
                    _PARENT.reset(token)

            return observed

        route.get_route_handler = handler_factory  # type: ignore[method-assign]
        route.app = request_response(handler_factory())
        route.__dict__["_diagnostics_instrumented"] = True


class DiagnosticsCompletionMiddleware:
    """Observe actual ASGI response completion, including streaming interruptions."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        scope["diagnostics_asgi"] = True
        completed = False
        status: int | None = None

        async def observe_send(message: Message) -> None:
            nonlocal completed, status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                completed = True

        error: BaseException | None = None
        try:
            await self.app(scope, receive, observe_send)
        except BaseException as caught:
            error = caught
            raise
        finally:
            state = scope.get("state", {})
            context = state.get("diagnostics_trace_context")
            root = state.get("diagnostics_root_span")
            if context is not None and root is not None:
                from .diagnostics_runtime import bind_request_context

                with bind_request_context(context):
                    root.name = (
                        "backend_response_completed"
                        if completed
                        else "backend_response_interrupted"
                    )
                    root.http_status = status
                    observed = (
                        "failure"
                        if error
                        else "success"
                        if completed and status and status < 400
                        else "failure"
                        if completed
                        else "cancelled"
                    )
                    if root.ended:
                        root.observe(observed, error)
                    else:
                        root.finish(observed, error)
