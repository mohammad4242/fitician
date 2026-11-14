import asyncio
import json
import signal


def test_process_telemetry_accepts_only_its_private_sentry_configuration(tmp_path, monkeypatch):
    from app.debugging import process_lifecycle
    from app.observability import sentry

    observed = []
    monkeypatch.setattr(
        sentry,
        "initialize_sentry",
        lambda service, **options: observed.append((service, options)) or True,
    )
    monkeypatch.setenv("FITICIAN_RUNTIME_COMMIT", "a" * 40)
    for key in ("SENTRY_DSN", "DIAGNOSTICS_ENVIRONMENT", "APP_BUILD_SHA"):
        # Register restoration even when the key did not exist before this test.
        # initialize_telemetry writes directly to os.environ after validation.
        monkeypatch.setenv(key, "")
    path = tmp_path / "telemetry.json"
    assert process_lifecycle.initialize_telemetry(path, "debug-runtime") == "disabled"
    path.write_text(
        json.dumps(
            {"dsn": "https://public@o1.ingest.us.sentry.io/1", "environment": "production-germany"}
        )
    )
    path.chmod(0o600)
    assert process_lifecycle.initialize_telemetry(path, "debug-runtime") == "initialized"
    assert observed == [("debug-runtime", {"http_server": False})]
    import os

    assert os.environ["APP_BUILD_SHA"] == "a" * 40
    path.chmod(0o644)
    assert process_lifecycle.initialize_telemetry(path, "debug-runtime") == "configuration_rejected"


def test_termination_cancels_the_service_and_flushes_with_the_existing_bounded_budget(monkeypatch):
    from app.debugging import process_lifecycle
    from app.observability import sentry

    events = []

    async def service():
        try:
            await asyncio.Event().wait()
        finally:
            events.append("cancelled")

    async def run():
        loop = asyncio.get_running_loop()
        callbacks = {}
        monkeypatch.setattr(
            loop, "add_signal_handler", lambda sig, callback: callbacks.setdefault(sig, callback)
        )
        monkeypatch.setattr(loop, "remove_signal_handler", lambda sig: callbacks.pop(sig))
        monkeypatch.setattr(sentry, "flush_sentry", lambda: events.append("flushed"))
        task = asyncio.create_task(process_lifecycle.serve_until_stopped(service()))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        callbacks[signal.SIGTERM]()
        await asyncio.wait_for(task, 1)
        assert not callbacks

    asyncio.run(run())
    assert events == ["cancelled", "flushed"]


def test_private_telemetry_test_restores_previously_absent_environment(tmp_path):
    import os
    from unittest.mock import patch

    import pytest

    keys = ("SENTRY_DSN", "DIAGNOSTICS_ENVIRONMENT", "APP_BUILD_SHA")
    # Keep this regression itself isolated even when the nested test leaks environment.
    with patch.dict(os.environ):
        for key in keys:
            os.environ.pop(key, None)
        with pytest.MonkeyPatch.context() as scoped:
            test_process_telemetry_accepts_only_its_private_sentry_configuration(tmp_path, scoped)
        assert not any(key in os.environ for key in keys)
