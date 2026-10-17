"""Bridge existing operational error logs without forwarding messages or arguments."""

from __future__ import annotations

import atexit
import logging
import re
from uuid import UUID

from app.config import Settings
from app.observability.diagnostics_runtime import (
    _REQUEST_CONTEXT,
    DiagnosticsRuntime,
    category_for_error,
    safe_source_location,
)
from app.observability.diagnostics_schemas import EventInput


class DiagnosticLogHandler(logging.Handler):
    def __init__(self, runtime: DiagnosticsRuntime) -> None:
        super().__init__(logging.ERROR)
        self.runtime = runtime

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith(("app.observability", "sqlalchemy")):
            return
        try:
            context = _REQUEST_CONTEXT.get()
            code = getattr(record, "error_code", None)
            if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", code):
                code = "OPERATIONAL_ERROR"
            component = re.sub(r"[^A-Za-z0-9_.:-]", "_", record.name)[:80]
            exception = record.exc_info[1] if record.exc_info else None
            request_id = getattr(record, "request_id", None) or (
                context.request_id if context else None
            )
            if request_id is not None and not re.fullmatch(
                r"[A-Za-z0-9_.:-]{1,128}", str(request_id)
            ):
                request_id = None
            job_id = getattr(record, "job_id", None)
            try:
                resource_id = UUID(str(job_id)) if job_id else None
            except ValueError:
                resource_id = None
            self.runtime.submit(
                EventInput(
                    component=component,
                    operation=context.operation if context else "background_operation",
                    stage=context.stage_name if context else "execution",
                    platform="backend" if context else "worker",
                    request_id=request_id,
                    operation_id=context.operation_id if context else None,
                    category=category_for_error(code.upper(), 500) if context else "job_failure",
                    severity="critical" if record.levelno >= logging.CRITICAL else "error",
                    error_code=code,
                    exception_type=type(exception).__name__ if exception else None,
                    source_location=safe_source_location(exception),
                    resource_id=resource_id,
                    outcome="failure",
                ),
                context.user_id if context else None,
            )
        except Exception:
            # Logging must never recurse or change a business outcome.
            return


def install_diagnostic_log_bridge(settings: Settings) -> DiagnosticsRuntime | None:
    if settings.app_env == "test":
        return None
    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler, DiagnosticLogHandler):
            return handler.runtime
    try:
        runtime = DiagnosticsRuntime(settings)
        runtime.start()
        root.addHandler(DiagnosticLogHandler(runtime))
        atexit.register(runtime.stop)
        return runtime
    except Exception:
        return None
