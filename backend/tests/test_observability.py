from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import create_app
from app.observability.metrics import MetricsRegistry, route_label_from_scope


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
    assert "# TYPE fitician_http_requests_total counter" in response.text


def test_http_metrics_use_the_matched_route_template(client: TestClient) -> None:
    plan_id = "550e8400-e29b-41d4-a716-446655440000"

    response = client.get(f"/api/v1/nutrition/plans/{plan_id}")
    metrics = client.get("/metrics")

    assert response.status_code == 401
    assert 'route=\"/api/v1/nutrition/plans/{plan_id}\"' in metrics.text
    assert plan_id not in metrics.text


def test_unmatched_http_paths_share_one_registry_series() -> None:
    metrics = MetricsRegistry()

    for index in range(1000):
        route = route_label_from_scope({"path": f"/unknown/{index}/arbitrary"})
        metrics.observe_http(
            method="GET",
            route=route,
            status_code=404,
            duration_seconds=0.01,
        )

    assert len(metrics._http_count) == 1
    assert next(iter(metrics._http_count)) == ("GET", "/__unmatched__", 404)
    assert 'route=\"/__unmatched__\"' in metrics.render()


def test_http_metrics_bound_arbitrary_method_labels() -> None:
    metrics = MetricsRegistry()
    route = route_label_from_scope({"route": SimpleNamespace(path="/livez")})

    for index in range(1000):
        metrics.observe_http(
            method=f"CUSTOM-{index}",
            route=route,
            status_code=405,
            duration_seconds=0.01,
        )

    assert len(metrics._http_count) == 1
    assert next(iter(metrics._http_count)) == ("OTHER", "/livez", 405)


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


def test_metrics_registry_exposes_bounded_cache_and_queue_labels() -> None:
    metrics = MetricsRegistry()
    metrics.record_cache(namespace="exercises", hit=True, redis_available=True)
    metrics.record_cache(namespace="exercises", hit=False, redis_available=False)
    metrics.record_rate_limit(namespace="auth", operation="login", allowed=False, available=True)
    metrics.set_labeled_gauge("fitician_queue_depth", {"queue": "body_analysis"}, 3)

    rendered = metrics.render()

    assert 'fitician_cache_hits_total{namespace="exercises"} 1' in rendered
    assert 'fitician_cache_misses_total{namespace="exercises"} 1' in rendered
    assert 'fitician_cache_redis_unavailable_total{namespace="exercises"} 1' in rendered
    assert 'fitician_rate_limit_blocked_total{namespace="auth",operation="login"} 1' in rendered
    assert 'fitician_queue_depth{queue="body_analysis"} 3' in rendered
