"""Resume durable trace links without changing job ownership, retries or charging."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID, uuid4

from .diagnostics_runtime import DiagnosticsRuntime, RequestDiagnosticsContext, bind_request_context
from .tracing import Span, current_context


@contextmanager
def job_trace(
    job: Any,
    *,
    component: str,
    user_id: UUID | None = None,
    runtime: DiagnosticsRuntime | None = None,
    status_source: Any = None,
) -> Iterator[None]:
    if current_context() is not None:
        yield
        return
    if runtime is None:
        import logging

        from .diagnostics_logs import DiagnosticLogHandler

        runtime = next(
            (
                h.runtime
                for h in logging.getLogger().handlers
                if isinstance(h, DiagnosticLogHandler)
            ),
            None,
        )
    if runtime is None or job is None or not getattr(job, "trace_id", None):
        # Legacy jobs have no trace context; existing job-failure reconciliation remains canonical.
        yield
        return
    context = RequestDiagnosticsContext(
        submit=runtime.submit,
        request_id=job.correlation_id or str(uuid4()),
        operation_id=job.trace_operation_id or str(uuid4()),
        operation=component,
        resource_id=getattr(status_source or job, "id", None),
        component=component,
        user_id=user_id,
        trace_id=job.trace_id,
        telemetry_platform="worker",
        retry_count=min(getattr(status_source or job, "attempt_count", 0), 100),
        clock_domain=f"worker:{component}",
    )
    with bind_request_context(context):
        root = Span(
            "worker_execution",
            component,
            span_id=context.root_span_id,
            parent_span_id=job.trace_parent_span_id,
        )
        root.observe("started")
        try:
            yield
        except BaseException as error:
            root.finish("failure" if isinstance(error, Exception) else "cancelled", error)
            raise
        else:
            status = str(getattr(status_source or job, "status", "unknown"))
            root.finish(
                "success"
                if status in {"completed", "processed", "sent"}
                else "failure"
                if status in {"failed", "dead_letter"}
                else "stage"
            )
