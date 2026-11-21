from contextlib import contextmanager
from uuid import uuid4

from sqlalchemy import event as sqlalchemy_event
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import Settings
from app.observability.diagnostics_models import DiagnosticEvent, DiagnosticIssue
from app.observability.diagnostics_runtime import DiagnosticsRuntime
from app.observability.diagnostics_schemas import EventInput


def observation(*, failure=False):
    return EventInput(
        component="writer_test",
        operation="capture",
        stage="persist",
        platform="backend",
        category="application_bug" if failure else "unknown",
        severity="error" if failure else "info",
        error_code="WRITER_TEST",
        record_type="event" if failure else "span",
        outcome="failure" if failure else "success",
    )


def writer(factory):
    runtime = DiagnosticsRuntime(Settings(app_env="local", _env_file=None), session_factory=factory)
    runtime._maintenance = lambda _: None
    return runtime


def drain(runtime):
    runtime._stop.set()
    runtime._run()
    assert runtime._queue.unfinished_tasks == 0


def factory_for(db):
    return lambda: Session(bind=db.connection(), join_transaction_mode="create_savepoint")


def test_batch_spans_use_bounded_bulk_insert_and_preserve_grouping(db):
    runtime = writer(factory_for(db))
    statements = []
    connection = db.connection()

    def observe(_connection, _cursor, statement, *_args):
        if statement.startswith("INSERT INTO diagnostic_events"):
            statements.append(statement)

    sqlalchemy_event.listen(connection, "before_cursor_execute", observe)
    try:
        spans = [observation() for _ in range(64)]
        failures = [observation(failure=True) for _ in range(2)]
        for item in [*spans, *failures, failures[0]]:
            assert runtime.submit(item)
        drain(runtime)
        assert len([s for s in statements if "RETURNING" not in s]) == 2
        assert db.scalar(select(func.count()).select_from(DiagnosticEvent)) == 66
        assert db.scalar(select(DiagnosticIssue.count)) == 2
        assert all(item.event_id is not None for item in spans)
        assert runtime.health_snapshot()["persisted"] == 67
    finally:
        sqlalchemy_event.remove(connection, "before_cursor_execute", observe)


def test_unknown_commit_ack_retries_same_uuid_without_double_count(db):
    calls = 0

    @contextmanager
    def factory():
        nonlocal calls
        calls += 1
        with factory_for(db)() as session:
            commit = session.commit

            def acknowledge():
                commit()
                if calls == 1:
                    raise OperationalError("commit", {}, Exception("private credential"))

            session.commit = acknowledge
            yield session

    runtime = writer(factory)
    failure = observation(failure=True)
    runtime.submit(failure)
    drain(runtime)
    assert calls == 2
    assert db.scalar(select(DiagnosticIssue.count)) == 1
    assert runtime.health_snapshot()["retried"] == 1
    assert runtime.dropped_count == 0


def test_outage_has_bounded_retries_and_safe_failure_visibility():
    calls = 0

    @contextmanager
    def factory():
        nonlocal calls
        calls += 1
        raise OperationalError("private query", {}, Exception("private credential"))
        yield  # pragma: no cover

    runtime = writer(factory)
    for _ in range(40):
        runtime.submit(observation())
    drain(runtime)
    assert calls == 6
    snapshot = runtime.health_snapshot()
    assert snapshot["persistence_failed"] == 40
    assert snapshot["dropped"] == 40
    assert snapshot["retried"] == 80
    losses = runtime.recent_losses()
    assert len(losses) == 32
    assert set(losses[0]) == {"event_id", "reason", "observed_at"}
    assert "private" not in str(losses)
    assert snapshot["in_flight"] == 0


def test_overflow_exposes_evicted_observation_identity():
    runtime = writer(lambda: None)
    original = observation()
    runtime.submit(original)
    for _ in range(255):
        runtime.submit(observation())
    assert runtime.submit(observation(failure=True))
    assert runtime.health_snapshot()["evicted"] == 1
    assert runtime.recent_losses()[0]["event_id"] == str(original.event_id)
    assert runtime.recent_losses()[0]["reason"] == "queue_evicted"


def test_rejected_failure_is_visible_and_loss_ring_is_bounded():
    runtime = writer(lambda: None)
    for _ in range(256):
        runtime.submit(observation(failure=True))
    for _ in range(40):
        assert not runtime.submit(observation(failure=True))
    assert runtime.health_snapshot()["queue_rejected"] == 40
    assert len(runtime.recent_losses()) == 32


def test_poison_observation_does_not_discard_valid_neighbour(db):
    runtime = writer(factory_for(db))
    missing_user = uuid4()
    runtime.submit(observation(), user_id=missing_user)
    good = observation(failure=True)
    runtime.submit(good)
    drain(runtime)
    assert db.get(DiagnosticEvent, good.event_id) is not None
    assert runtime.health_snapshot()["persisted"] == 1
    assert runtime.health_snapshot()["persistence_failed"] == 1


def test_submit_after_shutdown_is_rejected_with_visible_reason():
    runtime = writer(lambda: None)
    runtime._stop.set()
    assert not runtime.submit(observation())
    assert runtime.health_snapshot()["shutdown_discarded"] == 1


def test_exhausted_shutdown_budget_accounts_for_remaining_queue():
    runtime = writer(lambda: None)
    for _ in range(40):
        runtime.submit(observation())
    runtime._stop.set()
    runtime._shutdown_deadline = 0
    runtime._run()
    assert runtime.health_snapshot()["shutdown_discarded"] == 40
    assert runtime.queued_count == 0
    assert runtime._queue.unfinished_tasks == 0


def test_successful_stage_events_are_batched_without_creating_issues(db):
    runtime = writer(factory_for(db))
    statements = []
    connection = db.connection()

    def observe(_connection, _cursor, statement, *_args):
        if statement.startswith("INSERT INTO diagnostic_events"):
            statements.append(statement)

    sqlalchemy_event.listen(connection, "before_cursor_execute", observe)
    try:
        for _ in range(64):
            runtime.submit(observation().model_copy(update={"record_type": "event"}))
        drain(runtime)
        assert len(statements) == 2
        assert db.scalar(select(func.count()).select_from(DiagnosticIssue)) == 0
    finally:
        sqlalchemy_event.remove(connection, "before_cursor_execute", observe)
