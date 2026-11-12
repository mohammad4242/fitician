from app.observability.sentry import sanitize_event


def test_preserves_chain_and_frames_without_exporting_payload_or_locals():
    event = {
        "request": {"headers": {"Authorization": "secret"}, "data": "medical"},
        "user": {"email": "member@example.com"},
        "extra": {"prompt": "private"},
        "message": "private medical text",
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "secret",
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": "/srv/backend/app/auth/service.py",
                                "function": "login",
                                "lineno": 42,
                                "vars": {"token": "secret"},
                                "pre_context": ["secret"],
                                "context_line": "secret",
                            }
                        ]
                    },
                }
            ]
        },
        "breadcrumbs": {"values": [{"message": "secret", "data": {"body": "private"}}]},
    }
    clean = sanitize_event(event, {})
    assert clean["exception"]["values"][0]["type"] == "ValueError"
    assert clean["exception"]["values"][0]["stacktrace"]["frames"][0] == {
        "filename": "app/auth/service.py",
        "function": "login",
        "lineno": 42,
    }
    assert "secret" not in str(clean)
    assert "private" not in str(clean)
    assert "member@example.com" not in str(clean)


def test_span_and_unknown_fields_are_not_exported():
    clean = sanitize_event(
        {
            "spans": [{"description": "SELECT secret", "data": {"sql": "secret"}}],
            "contexts": {"ai": {"prompt": "secret"}},
            "unknown": "secret",
        },
        {},
    )
    assert "secret" not in str(clean)


def test_agent_privacy_policy_is_identical():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    assert (root / "backend/app/observability/sentry.py").read_bytes() == (
        root / "agent-service/app/sentry.py"
    ).read_bytes()


def test_real_sdk_serializes_original_chain_without_secrets():
    import sentry_sdk
    from sentry_sdk.integrations.dedupe import DedupeIntegration
    from sentry_sdk.transport import Transport

    from app.observability.sentry import _before_send

    envelopes = []

    class MemoryTransport(Transport):
        def capture_envelope(self, envelope):
            envelopes.append(envelope)

    client = sentry_sdk.Client(
        dsn='https://public@example.invalid/1', default_integrations=False,
        integrations=[DedupeIntegration()], transport=MemoryTransport(), before_send=_before_send,
        include_local_variables=False,
    )
    with sentry_sdk.isolation_scope() as scope:
        scope.set_client(client)
        try:
            try:
                raise ValueError('medical secret')
            except ValueError as cause:
                raise RuntimeError('Bearer secret') from cause
        except RuntimeError as error:
            sentry_sdk.capture_exception(error)
            sentry_sdk.capture_exception(error)
    assert len(envelopes) == 1
    payload = envelopes[0].items[0].payload.json
    assert [value['type'] for value in payload['exception']['values']] == [
        'ValueError', 'RuntimeError',
    ]
    assert all(value['stacktrace']['frames'] for value in payload['exception']['values'])
    assert 'medical secret' not in str(payload)
    assert 'Bearer secret' not in str(payload)
    client.close()
