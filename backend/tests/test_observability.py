from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


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


def test_instance_header_is_opt_in_for_local_replica_smoke(test_settings) -> None:
    test_settings.instance_header_enabled = True
    test_settings.instance_id = "backend-test"
    with TestClient(create_app(test_settings)) as client:
        response = client.get("/livez")

    assert response.headers["X-Fitician-Instance"] == "backend-test"


def test_readiness_and_health_stop_accepting_traffic_during_drain(client: TestClient) -> None:
    client.app.state.draining = True

    ready = client.get("/readyz")
    health = client.get("/healthz")

    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"
    assert health.status_code == 503
