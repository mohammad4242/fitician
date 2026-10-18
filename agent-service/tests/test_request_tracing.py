import json
import re

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app


def test_valid_correlation_and_traceparent_create_child_response_and_safe_log(caplog) -> None:
    app = create_app(Settings(agent_service_token=SecretStr("a" * 32)))
    trace_id = "1" * 32
    parent_span_id = "2" * 16
    correlation_id = "audit-correlation.42"

    with caplog.at_level("INFO", logger="fitician.agent_service"):
        response = TestClient(app).get(
            "/healthz",
            headers={
                "X-Correlation-ID": correlation_id,
                "traceparent": f"00-{trace_id}-{parent_span_id}-01",
            },
        )

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == correlation_id
    assert response.headers["X-Request-ID"] == correlation_id
    match = re.fullmatch(r"00-([a-f0-9]{32})-([a-f0-9]{16})-01", response.headers["traceparent"])
    assert match is not None
    assert match[1] == trace_id
    assert match[2] != parent_span_id
    record = json.loads(caplog.records[-1].message)
    assert record["request_id"] == correlation_id
    assert record["trace_id"] == trace_id
    assert record["span_id"] == match[2]
    assert record["parent_span_id"] == parent_span_id
    assert set(record) <= {
        "request_id",
        "trace_id",
        "span_id",
        "parent_span_id",
        "agent",
        "model",
        "endpoint",
        "task_kind",
        "duration_ms",
        "status",
        "error_code",
        "input_bytes",
        "image_count",
        "input_tokens",
        "output_tokens",
    }


def test_zero_trace_or_span_ids_are_replaced() -> None:
    app = create_app(Settings(agent_service_token=SecretStr("a" * 32)))
    response = TestClient(app).get(
        "/healthz",
        headers={
            "X-Correlation-ID": "safe-id",
            "traceparent": f"00-{'0' * 32}-{'0' * 16}-01",
        },
    )

    trace_id, span_id = response.headers["traceparent"].split("-")[1:3]
    assert trace_id != "0" * 32
    assert span_id != "0" * 16
