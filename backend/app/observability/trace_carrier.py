"""Nullable durable propagation metadata for existing job records."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


def _value(name: str) -> str | None:
    from .tracing import current_context, propagation_headers

    context = current_context()
    if context is None:
        return None
    if name == "parent":
        return propagation_headers()["traceparent"].split("-")[2]
    return str(getattr(context, name))


class TraceCarrier:
    trace_id: Mapped[str | None] = mapped_column(String(32), default=lambda: _value("trace_id"))
    trace_parent_span_id: Mapped[str | None] = mapped_column(
        String(16), default=lambda: _value("parent")
    )
    trace_operation_id: Mapped[str | None] = mapped_column(
        String(128), default=lambda: _value("operation_id")
    )
