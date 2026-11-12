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
