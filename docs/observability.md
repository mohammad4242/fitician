# Fitician observability

The API exposes a bounded Prometheus-compatible `/metrics` endpoint. It contains
HTTP latency/status counters, database pool gauges, Redis availability/latency,
cache and limiter counters, and durable queue depth. Request and job logs use
the correlation ID without recording prompts, tokens, private media, or provider
payloads.

Monitoring is an optional local/private Compose overlay. It does not participate
in API readiness and is not routed through Caddy:

```bash
GRAFANA_ADMIN_PASSWORD='local-change-me' \
REDIS_PASSWORD='fitician-redis-local-change-me' \
docker compose -f compose.yaml -f compose.observability.yaml up -d
```

Prometheus is available only on `127.0.0.1:9090`; Grafana is available only on
`127.0.0.1:3000`. Production operators should use an SSH tunnel or an existing
private admin network. Do not publish either port publicly.

The overlay uses seven-day/one-GB Prometheus retention, bounded memory/CPU, and
digest-pinned images. It can be stopped without stopping the application:

```bash
docker compose -f compose.yaml -f compose.observability.yaml stop prometheus grafana redis-exporter
```

