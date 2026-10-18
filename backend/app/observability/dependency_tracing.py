"""Automatic database observations. SQL text and values are never inspected."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from .tracing import current_context, start_span


def _before_cursor(
    conn: Any,
    cursor: Any,
    statement: Any,
    parameters: Any,
    execution_context: Any,
    executemany: Any,
) -> None:
    # Execution context, not pooled connection, owns concurrent span state.
    execution_context._fitician_span = start_span("database_execute", "database")


def _after_cursor(
    conn: Any,
    cursor: Any,
    statement: Any,
    parameters: Any,
    execution_context: Any,
    executemany: Any,
) -> None:
    span = getattr(execution_context, "_fitician_span", None)
    if span is not None:
        span.finish()


def _database_error(exception_context: Any) -> None:
    execution = exception_context.execution_context
    span = getattr(execution, "_fitician_span", None)
    if span is not None:
        span.finish("failure", exception_context.original_exception)


def _before_commit(session: Session) -> None:
    if current_context() is not None:
        session.info["diagnostic_commit_span"] = start_span("database_commit", "database")


def _after_commit(session: Session) -> None:
    span = session.info.pop("diagnostic_commit_span", None)
    if span is not None:
        span.finish()


def _after_rollback(session: Session) -> None:
    span = session.info.pop("diagnostic_commit_span", None)
    if span is not None:
        span.finish("failure")
    rollback = start_span("database_rollback_observed", "database")
    if rollback is not None:
        rollback.finish()


def install_database_tracing() -> None:
    for target, name, callback in (
        (Engine, "before_cursor_execute", _before_cursor),
        (Engine, "after_cursor_execute", _after_cursor),
        (Engine, "handle_error", _database_error),
        (Session, "before_commit", _before_commit),
        (Session, "after_commit", _after_commit),
        (Session, "after_rollback", _after_rollback),
    ):
        if not event.contains(target, name, callback):
            event.listen(target, name, callback)


def traced_pool_class() -> type[QueuePool]:
    from sqlalchemy.pool import QueuePool

    from .tracing import timed_stage

    class ObservedQueuePool(QueuePool):
        def _do_get(self) -> Any:
            with timed_stage("database_connection_acquire", component="database"):
                return super()._do_get()

    return ObservedQueuePool
