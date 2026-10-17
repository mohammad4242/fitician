from __future__ import annotations

import logging
import queue
import re
import threading
import time
import traceback
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Request, Response
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from app.config import Settings
from app.observability.diagnostics_schemas import Category, EventInput, Severity
from app.observability.diagnostics_service import (
    cleanup_retention,
    detect_abandoned_attempts,
    record_event,
)
from app.observability.logging import log_event

logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
_ERROR_CODE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_ALLOWED_OUTCOMES = {
    "started",
    "stage",
    "success",
    "failure",
    "timeout",
    "cancelled",
    "reused",
    "pending_review",
    "blocked",
}


@dataclass
class RequestDiagnosticsContext:
    submit: Callable[[EventInput, UUID | None], bool]
    request_id: str
    operation_id: str
    operation: str
    user_id: UUID | None = None
    component: str = "api"
    stage_name: str = "request"
    outcome: str | None = None
    error_code: str | None = None
    category: Category | None = None
    severity: Severity | None = None
    resource_id: UUID | None = None
    input_fingerprint: str | None = None
    exception_type: str | None = None
    source_location: str | None = None
    duration_ms: int | None = None
    version: str | None = None


_REQUEST_CONTEXT: ContextVar[RequestDiagnosticsContext | None] = ContextVar(
    "fitician_diagnostics_context", default=None
)


@contextmanager
def bind_request_context(context: RequestDiagnosticsContext) -> Iterator[None]:
    token = _REQUEST_CONTEXT.set(context)
    try:
        yield
    finally:
        _REQUEST_CONTEXT.reset(token)


def set_request_user(user_id: UUID) -> None:
    context = _REQUEST_CONTEXT.get()
    if context is not None:
        context.user_id = user_id


@contextmanager
def stage(name: str, *, component: str | None = None) -> Iterator[None]:
    """Set the current bounded operation stage; a failing stage remains visible."""
    context = _REQUEST_CONTEXT.get()
    if context is None or not isinstance(name, str) or not _TOKEN_RE.fullmatch(name):
        yield
        return
    previous_stage, previous_component = context.stage_name, context.component
    context.stage_name = name
    if component is not None and _TOKEN_RE.fullmatch(component):
        context.component = component
    try:
        yield
    except BaseException:
        raise
    else:
        context.stage_name = previous_stage
        context.component = previous_component


def set_stage(name: str, *, component: str | None = None) -> bool:
    """Set the persistent stage for the current request, or no-op outside it."""
    context = _REQUEST_CONTEXT.get()
    if context is None or not isinstance(name, str) or not _TOKEN_RE.fullmatch(name):
        return False
    context.stage_name = name
    if component is not None and _TOKEN_RE.fullmatch(component):
        context.component = component
    try:
        context.submit(
            EventInput(
                request_id=context.request_id,
                operation_id=context.operation_id,
                component=context.component,
                operation=context.operation,
                stage=name,
                platform="backend",
                category="unknown",
                severity="info",
                error_code="WORKFLOW_STAGE_ENTERED",
                outcome="stage",
            ),
            context.user_id,
        )
    except Exception:
        return False
    return True


def emit(
    *,
    category: Category,
    severity: Severity,
    error_code: str,
    outcome: str,
    operation: str | None = None,
    component: str | None = None,
    stage_name: str | None = None,
    duration_ms: int | None = None,
    exception: BaseException | None = None,
    resource_id: UUID | None = None,
    input_fingerprint: str | None = None,
    version: str | None = None,
) -> bool:
    """Set the request's terminal workflow result for its single event."""
    context = _REQUEST_CONTEXT.get()
    if context is None:
        return False
    code = (
        error_code
        if isinstance(error_code, str) and _ERROR_CODE_RE.fullmatch(error_code)
        else "HTTP_ERROR"
    )
    if outcome not in _ALLOWED_OUTCOMES:
        return False
    context.outcome = outcome
    context.error_code = code
    context.category = category
    context.severity = severity
    if operation and _TOKEN_RE.fullmatch(operation):
        context.operation = operation
    if component and _TOKEN_RE.fullmatch(component):
        context.component = component
    if stage_name and _TOKEN_RE.fullmatch(stage_name):
        context.stage_name = stage_name
    context.resource_id = resource_id if isinstance(resource_id, UUID) else None
    context.input_fingerprint = (
        input_fingerprint
        if isinstance(input_fingerprint, str) and re.fullmatch(r"[a-f0-9]{64}", input_fingerprint)
        else None
    )
    context.exception_type = safe_exception_type(exception)
    context.source_location = safe_source_location(exception)
    context.duration_ms = duration_ms
    if version is not None and re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", version):
        context.version = version
    return True


def bind_version(version: str) -> None:
    context = _REQUEST_CONTEXT.get()
    if (
        context is not None
        and isinstance(version, str)
        and re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", version)
    ):
        context.version = version


def bind_resource(resource_id: UUID, *, fingerprint: str | None = None) -> None:
    context = _REQUEST_CONTEXT.get()
    if context is None or not isinstance(resource_id, UUID):
        return
    context.resource_id = resource_id
    if fingerprint is not None and re.fullmatch(r"[a-f0-9]{64}", fingerprint):
        context.input_fingerprint = fingerprint


def safe_exception_type(error: BaseException | None) -> str | None:
    if error is None:
        return None
    name = type(error).__name__
    return name[:100] if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]*", name) else None


def safe_source_location(error: BaseException | None) -> str | None:
    if error is None or error.__traceback__ is None:
        return None
    frames = traceback.extract_tb(error.__traceback__)
    for frame in reversed(frames):
        module = frame.filename.replace("\\", "/")
        if "/app/" not in module and not module.startswith("app/"):
            continue
        filename = Path(frame.filename).name
        if re.fullmatch(r"[A-Za-z0-9_.-]{1,120}\.py", filename):
            return f"{filename}:{frame.lineno}"
    return None


def route_operation(route_path: str | None, method: str) -> str:
    if route_path in {"/api/v1/workouts/generate", "/api/v1/workout-plans/generate"}:
        return "workout_generation"
    if route_path in {"/api/v1/nutrition/plans", "/api/v1/nutrition/plans/generate"}:
        return "nutrition_generation"
    template = re.sub(r"\{[^}]+\}", "id", route_path or "api/unmatched")
    safe = re.sub(r"[^A-Za-z0-9_.:-]+", "_", f"{method.lower()}_{template.strip('/')}")
    return safe[:80] or "api_unmatched"


def route_component(route_path: str | None) -> str:
    for prefix, component in (
        ("/api/v1/auth", "auth"),
        ("/api/v1/workout", "workout_engine"),
        ("/api/v1/nutrition", "nutrition"),
        ("/api/v1/body", "body_analysis"),
        ("/api/v1/notifications", "notifications"),
        ("/api/v1/billing", "billing"),
        ("/api/v1/entitlements", "entitlements"),
        ("/api/v1/profile", "onboarding"),
    ):
        if route_path and route_path.startswith(prefix):
            return component
    return "api"


def category_for_error(code: str, status_code: int) -> Category:
    code = code.upper()
    if code in {
        "AGENT_NETWORK_UNAVAILABLE",
        "CONNECTION_FAILURE",
        "DNS_FAILURE",
        "REDIS_UNAVAILABLE",
    }:
        return "infrastructure_failure"
    if code in {"DB_CONNECTION_FAILED", "DATABASE_UNAVAILABLE", "DB_POOL_EXHAUSTED"}:
        return "database_failure"
    if "TIMEOUT" in code or status_code in {408, 504}:
        return "interrupted"
    if code in {
        "INVALID_PROFILE_INPUT",
        "STRUCTURED_EXERCISE_REQUIRED",
        "NUTRITION_PROFILE_REQUIRED",
    }:
        return "invalid_input"
    if code in {"NUTRITION_GENERATION_INPUTS_CHANGED", "GENERATION_INPUTS_CHANGED"}:
        return "business_rejection"
    if code in {"COACH_REVIEW_QUOTA_EXCEEDED", "PHYSICIAN_REVIEW_QUOTA_EXCEEDED"}:
        return "quota_limit"
    if (
        status_code == 401
        or code.startswith("AUTH_")
        or code in {"AUTHENTICATION_REQUIRED", "ADMIN_ROLE_REQUIRED", "INVALID_CREDENTIALS"}
    ):
        return "auth_failure"
    if code in {
        "ENTITLEMENT_QUOTA_EXCEEDED",
        "RATE_LIMITED",
        "RATE_LIMIT_EXCEEDED",
        "RATE_LIMIT_UNAVAILABLE",
    }:
        return "quota_limit"
    if code in {"VALIDATION_ERROR", "AGE_NOT_SUPPORTED", "AGE_OUT_OF_RANGE"}:
        return "invalid_input"
    if code == "WORKOUT_GENERATION_UNSUPPORTED" or code.startswith("SAFETY_"):
        return "safety_restriction"
    if code in {
        "ENTITLEMENT_REQUIRED",
        "ACCESS_TERM_TOO_SHORT",
        "WORKOUT_GENERATION_COOLDOWN",
        "WORKOUT_GENERATION_IN_PROGRESS",
    }:
        return "business_rejection"
    if code.startswith(("AGENT_", "AI_")) or code == "WORKOUT_GENERATION_FAILED":
        return "provider_failure"
    if status_code < 500:
        return "unknown"
    return "unknown"


def safe_error_code(value: object) -> str:
    if isinstance(value, str) and _ERROR_CODE_RE.fullmatch(value):
        return value
    return "HTTP_ERROR"


def mark_http_error(request: object, *, code: object, error: BaseException | None = None) -> None:
    state = getattr(request, "state", None)
    if state is None:
        return
    state.diagnostics_error_code = safe_error_code(code)
    state.diagnostics_exception = error


def mark_database_failure(request: object) -> None:
    state = getattr(request, "state", None)
    if state is not None:
        state.diagnostics_skip_event = True


class DiagnosticsRuntime:
    """Bounded best-effort writer with a dedicated, short-timeout DB pool."""

    def __init__(
        self,
        settings: Settings,
        *,
        enabled: bool = True,
        session_factory: Callable[[], Session] | None = None,
        injected_sink: Callable[[EventInput, UUID | None], None] | None = None,
    ) -> None:
        self.settings = settings
        self.enabled = enabled and settings.diagnostics_enabled and settings.app_env != "test"
        self._session_factory = session_factory
        self._injected_sink = injected_sink
        self._queue: queue.Queue[tuple[EventInput, UUID | None]] = queue.Queue(maxsize=256)
        self.dropped_count = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._engine: Engine | None = None

    @property
    def writer_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def queued_count(self) -> int:
        return self._queue.qsize()

    def start(self) -> None:
        if not self.enabled or self._injected_sink is not None or self._thread is not None:
            return
        if self._session_factory is None:
            connect_args: dict[str, object] = {}
            if self.settings.database_url.startswith("postgresql"):
                connect_args = {
                    "connect_timeout": 2,
                    "options": "-c statement_timeout=2000",
                }
            self._engine = create_engine(
                self.settings.database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                poolclass=QueuePool,
                pool_size=1,
                max_overflow=0,
                pool_timeout=0.1,
                connect_args=connect_args,
            )
            engine = self._engine
            self._session_factory = lambda: Session(engine)
        self._thread = threading.Thread(
            target=self._run,
            name="fitician-diagnostics-writer",
            daemon=True,
        )
        self._thread.start()

    def submit(self, event: EventInput, user_id: UUID | None = None) -> bool:
        if self._injected_sink is not None:
            try:
                self._injected_sink(event, user_id)
            except Exception:
                return False
            return True
        if event.build is None and re.fullmatch(r"[a-f0-9]{7,40}", self.settings.app_build_sha):
            event = event.model_copy(update={"build": self.settings.app_build_sha})
        if not self.enabled:
            return False
        try:
            self._queue.put_nowait((event, user_id))
        except queue.Full:
            self.dropped_count += 1
            return False
        return True

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout=2.0)
        if self._engine is not None and not self._thread.is_alive():
            self._engine.dispose()
        self._thread = None

    def _maintenance(self, factory: Callable[[], Session]) -> None:
        try:
            from app.observability.diagnostics_jobs import reconcile_job_failures

            with factory() as db:
                reconcile_job_failures(db)
                detect_abandoned_attempts(db)
                cleanup_retention(db, limit=1000)
                db.commit()
        except Exception:
            log_event(
                logger,
                "diagnostics maintenance failed",
                error_code="DIAGNOSTICS_MAINTENANCE_FAILED",
            )

    def _run(self) -> None:
        factory = self._session_factory
        if factory is None:
            return
        next_cleanup = time.monotonic()
        written = 0
        while not self._stop.is_set() or not self._queue.empty():
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                if time.monotonic() >= next_cleanup:
                    self._maintenance(factory)
                    next_cleanup = time.monotonic() + 3600
                continue
            try:
                with factory() as db:
                    record_event(db, item[0], user_id=item[1])
                    db.commit()
                written += 1
                if time.monotonic() >= next_cleanup or written >= 100:
                    self._maintenance(factory)
                    next_cleanup = time.monotonic() + 3600
                    written = 0
            except Exception:
                log_event(
                    logger, "diagnostics persistence failed", error_code="DIAGNOSTICS_WRITE_FAILED"
                )
            finally:
                self._queue.task_done()


def should_record_request(request: Request) -> bool:
    path = request.url.path
    if not path.startswith("/api/"):
        return False
    if path.startswith("/api/v1/diagnostics/") or path.startswith("/api/v1/admin/diagnostics"):
        return False
    if path in {"/api/v1/healthz", "/api/v1/livez", "/api/v1/readyz", "/api/v1/metrics"}:
        return False
    if path.startswith("/api/v1/admin/") and request.method.upper() in {"GET", "HEAD"}:
        return False
    if "/admin/" in path and request.method.upper() in {"GET", "HEAD"}:
        return False
    return True


async def diagnostics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    runtime: DiagnosticsRuntime | None,
) -> Response:
    if runtime is None or not should_record_request(request):
        return await call_next(request)

    request_id = str(getattr(request.state, "request_id", "") or uuid4())
    context = RequestDiagnosticsContext(
        submit=runtime.submit,
        request_id=request_id,
        operation_id=str(uuid4()),
        operation=route_operation(
            request.url.path
            if request.url.path in {"/api/v1/workout-plans/generate", "/api/v1/nutrition/plans"}
            else None,
            request.method,
        ),
        user_id=getattr(request.state, "diagnostics_user_id", None),
    )
    token: Token[RequestDiagnosticsContext | None] = _REQUEST_CONTEXT.set(context)
    started = time.perf_counter()
    try:
        if context.operation in {"workout_generation", "nutrition_generation"}:
            try:
                runtime.submit(
                    EventInput(
                        request_id=context.request_id,
                        operation_id=context.operation_id,
                        component="api",
                        operation=context.operation,
                        stage="request_received",
                        platform="backend",
                        category="unknown",
                        severity="info",
                        error_code="WORKFLOW_STARTED",
                        outcome="started",
                    )
                )
            except Exception:
                pass
        response = await call_next(request)
        if not getattr(request.state, "diagnostics_skip_event", False):
            route = request.scope.get("route")
            template = getattr(route, "path", None)
            context.operation = route_operation(template, request.method)
            if context.component == "api":
                context.component = route_component(template)
            context.user_id = getattr(request.state, "diagnostics_user_id", None)
            status_code = response.status_code
            if status_code < 400:
                code = "HTTP_REQUEST_COMPLETED"
                severity: Severity = "info"
            elif status_code < 500:
                code = safe_error_code(getattr(request.state, "diagnostics_error_code", None))
                if code == "HTTP_ERROR":
                    code = "HTTP_CLIENT_ERROR"
                severity = "warning"
            else:
                code = safe_error_code(getattr(request.state, "diagnostics_error_code", None))
                if code == "HTTP_ERROR":
                    code = "HTTP_SERVER_ERROR"
                severity = "error"
            category = category_for_error(code, status_code)
            code = context.error_code or code
            severity = context.severity or severity
            category = context.category or category
            outcome = context.outcome or ("success" if status_code < 400 else "failure")
            exception = getattr(request.state, "diagnostics_exception", None)
            event = EventInput(
                event_id=uuid4(),
                request_id=context.request_id,
                operation_id=context.operation_id,
                component=context.component,
                operation=context.operation,
                stage=context.stage_name,
                platform="backend",
                version=context.version,
                category=category,
                severity=severity,
                error_code=code,
                exception_type=context.exception_type or safe_exception_type(exception),
                source_location=context.source_location or safe_source_location(exception),
                http_status=status_code,
                input_fingerprint=context.input_fingerprint,
                resource_id=context.resource_id,
                outcome=outcome,
                duration_ms=context.duration_ms
                if context.duration_ms is not None
                else min(max(0, round((time.perf_counter() - started) * 1000)), 86_400_000),
            )
            try:
                runtime.submit(event, context.user_id)
            except Exception:
                log_event(
                    logger, "diagnostics delivery failed", error_code="DIAGNOSTICS_WRITE_FAILED"
                )
        return response
    except BaseException as error:
        template = getattr(request.scope.get("route"), "path", None)
        context.operation = route_operation(template, request.method)
        if context.component == "api":
            context.component = route_component(template)
        # Preserve cancellations and the original exception. Never write nested DB transactions.
        if isinstance(error, SQLAlchemyError):
            log_event(
                logger,
                "database operation failed",
                request_id=context.request_id,
                error_code=type(error).__name__,
            )
        else:
            try:
                runtime.submit(
                    EventInput(
                        request_id=context.request_id,
                        operation_id=context.operation_id,
                        component=context.component,
                        operation=context.operation,
                        stage=context.stage_name,
                        platform="backend",
                        category="interrupted"
                        if not isinstance(error, Exception)
                        else "application_bug",
                        severity="warning" if not isinstance(error, Exception) else "critical",
                        error_code="OPERATION_INTERRUPTED"
                        if not isinstance(error, Exception)
                        else "UNHANDLED_EXCEPTION",
                        exception_type=safe_exception_type(error),
                        source_location=safe_source_location(error),
                        outcome="cancelled" if not isinstance(error, Exception) else "failure",
                        http_status=500 if isinstance(error, Exception) else None,
                        duration_ms=min(
                            86_400_000, max(0, round((time.perf_counter() - started) * 1000))
                        ),
                    ),
                    context.user_id,
                )
            except Exception:
                log_event(
                    logger, "diagnostics delivery failed", error_code="DIAGNOSTICS_WRITE_FAILED"
                )
        raise
    finally:
        _REQUEST_CONTEXT.reset(token)
