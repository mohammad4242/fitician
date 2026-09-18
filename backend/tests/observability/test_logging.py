from __future__ import annotations

import json
import logging

from app.observability.logging import JsonLogFormatter, log_event, redact_fields


def test_redact_fields_removes_secret_values_recursively() -> None:
    value = redact_fields(
        {
            "request_id": "req-1",
            "token": "secret-token",
            "nested": {"password": "secret-password", "safe": "ok"},
        }
    )

    assert value == {
        "request_id": "req-1",
        "token": "[REDACTED]",
        "nested": {"password": "[REDACTED]", "safe": "ok"},
    }


def test_json_log_formatter_emits_bounded_safe_event() -> None:
    record = logging.LogRecord(
        name="fitician.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="job finished",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-1"
    record.job_id = "job-1"
    record.secret = "do-not-log"

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["event"] == "job finished"
    assert payload["request_id"] == "req-1"
    assert payload["job_id"] == "job-1"
    assert "do-not-log" not in json.dumps(payload)


def test_log_event_preserves_request_and_job_ids(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="fitician.test"):
        log_event(
            logging.getLogger("fitician.test"),
            "body analysis queued",
            request_id="req-1",
            job_id="job-1",
            attempt=1,
        )

    assert caplog.records[-1].request_id == "req-1"
    assert caplog.records[-1].job_id == "job-1"
