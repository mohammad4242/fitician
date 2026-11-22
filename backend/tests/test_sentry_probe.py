from app.observability.synthetic_probe import record_synthetic_failure


def test_synthetic_probe_is_business_independent_and_keeps_original_source(db, monkeypatch):
    from app.observability import synthetic_probe

    monkeypatch.setattr(synthetic_probe, "initialize_sentry", lambda service: False)
    result = record_synthetic_failure(db, "a" * 40)
    assert result["issue_id"]
    assert result["event_id"]
    assert result["sentry_event_id"] is None
    assert result["delivery"] == "not_configured"
    assert result["build"] == "a" * 40


def test_panel_probe_is_admin_origin_flag_and_release_gated(client, db, test_settings):
    from tests.admin.test_ai_task_settings_api import ORIGIN, _admin

    path = "/api/v1/admin/diagnostics/synthetic-probe"
    assert client.get(path).status_code == 401
    _admin(client, db)
    assert client.get(path).json()["enabled"] is False
    assert (
        client.post(path, headers={**ORIGIN, "Idempotency-Key": "probe-request-1"}).status_code
        == 404
    )
    test_settings.diagnostics_synthetic_probe_enabled = True
    assert client.get(path).json()["enabled"] is False  # Unknown release must remain unknown.
    test_settings.app_build_sha = "b" * 40
    assert client.get(path).json()["enabled"] is True
    assert client.post(path, headers={"Idempotency-Key": "probe-request-1"}).status_code == 403


def test_panel_probe_retry_does_not_capture_twice_or_increment_occurrences(
    client, db, test_settings, monkeypatch
):
    from sqlalchemy import select

    from app.observability import synthetic_probe
    from app.observability.diagnostics_models import DiagnosticIssue
    from tests.admin.test_ai_task_settings_api import ORIGIN, _admin

    _admin(client, db)
    test_settings.diagnostics_synthetic_probe_enabled = True
    test_settings.app_build_sha = "b" * 40
    captures = []
    monkeypatch.setattr(synthetic_probe, "initialize_sentry", lambda _: False)
    original = synthetic_probe.raise_synthetic_failure

    def capture():
        captures.append(True)
        original()

    monkeypatch.setattr(synthetic_probe, "raise_synthetic_failure", capture)
    path = "/api/v1/admin/diagnostics/synthetic-probe"
    headers = {
        **ORIGIN,
        "Idempotency-Key": "probe-request-2",
        "X-Correlation-ID": "0d5d1e19-8eb0-410b-930f-26037c06a217",
    }
    first = client.post(path, headers=headers)
    assert first.status_code == 201, first.json()
    repeated = client.post(path, headers=headers)
    assert repeated.status_code == 201
    assert repeated.json()["event_id"] == first.json()["event_id"]
    assert repeated.json()["issue_id"] == first.json()["issue_id"]
    assert len(captures) == 1
    issue = db.scalar(
        select(DiagnosticIssue).where(DiagnosticIssue.error_code == "DIAGNOSTIC_SYNTHETIC_FAILURE")
    )
    assert issue.count == 1
    from uuid import UUID

    from app.observability.diagnostics_models import DiagnosticEvent

    occurrence = db.get(DiagnosticEvent, UUID(first.json()["event_id"]))
    assert occurrence.request_id == headers["X-Correlation-ID"]
    assert first.json()["build"] == "b" * 40
    assert first.json()["delivery"] == "not_configured"
    test_settings.app_build_sha = "c" * 40
    assert client.post(path, headers=headers).status_code == 409
    assert len(captures) == 1


def test_panel_probe_is_bounded_and_concurrent_dispatch_fails_closed(
    client, db, test_settings, monkeypatch
):
    import hashlib

    from sqlalchemy import create_engine, text

    from app.observability import synthetic_probe
    from app.observability.environment import diagnostics_environment
    from tests.admin.test_ai_task_settings_api import ORIGIN, _admin

    _admin(client, db)
    test_settings.diagnostics_synthetic_probe_enabled = True
    test_settings.app_build_sha = "b" * 40
    captures = []
    original = synthetic_probe.raise_synthetic_failure

    def capture():
        captures.append(True)
        original()

    monkeypatch.setattr(synthetic_probe, "initialize_sentry", lambda _: False)
    monkeypatch.setattr(synthetic_probe, "raise_synthetic_failure", capture)
    identity = int.from_bytes(
        hashlib.sha256(("synthetic-probe:" + diagnostics_environment()).encode()).digest()[:8],
        signed=True,
    )
    engine = create_engine(test_settings.database_url)
    try:
        with engine.connect() as competing, competing.begin():
            competing.execute(
                text("SELECT pg_advisory_xact_lock(:identity)"), {"identity": identity}
            )
            result = client.post(
                "/api/v1/admin/diagnostics/synthetic-probe",
                headers={**ORIGIN, "Idempotency-Key": "busy-request-1"},
            )
            assert result.status_code == 409 and captures == []
    finally:
        engine.dispose()
    path = "/api/v1/admin/diagnostics/synthetic-probe"
    for i in range(6):
        assert (
            client.post(
                path, headers={**ORIGIN, "Idempotency-Key": f"rate-request-{i}"}
            ).status_code
            == 201
        )
    assert (
        client.post(path, headers={**ORIGIN, "Idempotency-Key": "rate-request-7"}).status_code
        == 429
    )
    assert (
        client.post(path, headers={**ORIGIN, "Idempotency-Key": "rate-request-0"}).status_code
        == 201
    )
    assert len(captures) == 6


def test_retried_probe_without_external_id_does_not_invent_missing_configuration(
    client, db, test_settings, monkeypatch
):
    from app.observability import synthetic_probe
    from tests.admin.test_ai_task_settings_api import ORIGIN, _admin

    _admin(client, db)
    test_settings.diagnostics_synthetic_probe_enabled = True
    test_settings.app_build_sha = "b" * 40
    monkeypatch.setattr(synthetic_probe, "initialize_sentry", lambda _: True)
    monkeypatch.setattr(synthetic_probe, "attach_exception", lambda event, error: event)
    monkeypatch.setattr(synthetic_probe, "flush_sentry", lambda: None)
    path = "/api/v1/admin/diagnostics/synthetic-probe"
    headers = {**ORIGIN, "Idempotency-Key": "unknown-capture-1"}
    assert client.post(path, headers=headers).json()["delivery"] == "unconfirmed"
    assert client.post(path, headers=headers).json()["delivery"] == "unknown"
