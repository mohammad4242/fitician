from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness_and_readiness_are_separate(client: TestClient) -> None:
    live = client.get("/livez")
    ready = client.get("/readyz")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json()["status"] == "ok"
    assert ready.json()["checks"]["database"] == "ok"
    assert ready.json()["checks"]["redis"] in {"ok", "degraded"}


def test_metrics_are_prometheus_compatible_and_do_not_include_request_content(
    client: TestClient,
) -> None:
    client.get("/livez")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "fitician_http_requests_total" in response.text
    assert 'route=\"/livez\"' in response.text
    assert "password" not in response.text.lower()
