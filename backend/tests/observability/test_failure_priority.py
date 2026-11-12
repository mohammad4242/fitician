from app.config import Settings
from app.observability.diagnostics_runtime import DiagnosticsRuntime
from app.observability.diagnostics_schemas import EventInput


def event(failure=False):
    return EventInput(
        component="api",
        operation="test",
        stage="test",
        platform="backend",
        category="unknown",
        severity="error" if failure else "info",
        error_code="UNHANDLED_EXCEPTION" if failure else "HTTP_REQUEST_COMPLETED",
        outcome="failure" if failure else "success",
    )


def test_pressure_never_evicts_existing_failure_for_new_failure():
    runtime = DiagnosticsRuntime(Settings(app_env="local", _env_file=None))
    original = event(True)
    runtime.submit(original)
    for _ in range(255):
        runtime.submit(event())
    assert runtime.submit(event(True))
    assert runtime._queue.get_nowait()[0] is original
    assert runtime.queued_count == 255
    assert runtime.dropped_count == 1


def test_full_failure_queue_rejects_new_failure_honestly():
    runtime = DiagnosticsRuntime(Settings(app_env="local", _env_file=None))
    for _ in range(256):
        runtime.submit(event(True))
    assert runtime.submit(event(True)) is False
    assert runtime.dropped_count == 1
