#!/usr/bin/env bash
set -euo pipefail

base_url=${BASE_URL:-http://127.0.0.1:8080}
deadline_seconds=${FAILURE_DRILL_DEADLINE_SECONDS:-60}
compose=(docker compose -f compose.yaml -f compose.multi.yaml)
host=$(printf '%s' "$base_url" | sed -E 's#^[a-zA-Z]+://([^/:]+).*#\1#')

if [[ "$host" != "127.0.0.1" && "$host" != "localhost" && "$host" != "::1" ]]; then
  if [[ "${FITICIAN_ALLOW_PRODUCTION_FAILURE_DRILL:-false}" != "true" ]]; then
    echo "Refusing non-local failure drill target: $host" >&2
    exit 2
  fi
fi
if [[ "${COMPOSE_FILE:-}" == *compose.prod.yaml* && "${FITICIAN_ALLOW_PRODUCTION_FAILURE_DRILL:-false}" != "true" ]]; then
  echo "Refusing production Compose failure drill" >&2
  exit 2
fi

deadline=$((SECONDS + deadline_seconds))
wait_for_url() {
  local path=$1
  local expected=${2:-200}
  while (( SECONDS < deadline )); do
    status=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 3 "$base_url$path" || true)
    if [[ "$status" == "$expected" ]]; then
      return 0
    fi
    sleep 1
  done
  echo "deadline exceeded waiting for $path status $expected" >&2
  return 1
}

restart_service() {
  local service=$1
  deadline=$((SECONDS + deadline_seconds))
  "${compose[@]}" stop "$service" >/dev/null
  "${compose[@]}" start "$service" >/dev/null
  wait_for_url /livez 200
}

drill_redis() {
  restart_service redis
  wait_for_url /readyz 200
  echo '{"drill":"redis-unavailable","result":"recovered"}'
}

drill_backend_replica() {
  restart_service backend-2
  echo '{"drill":"backend-replica-killed","result":"recovered"}'
}

drill_worker() {
  restart_service body-analysis-worker
  restart_service food-photo-worker
  restart_service notification-worker
  echo '{"drill":"worker-killed-mid-job","result":"recovered"}'
}

drill_database() {
  restart_service db
  wait_for_url /readyz 200
  echo '{"drill":"database-unavailable","result":"recovered"}'
}

drill_queue() {
  deadline=$((SECONDS + deadline_seconds))
  wait_for_url /metrics 200
  echo '{"drill":"queue-backlog","result":"metrics-observed"}'
}

drill_caddy() {
  restart_service backend-2
  wait_for_url /healthz 200
  echo '{"drill":"caddy-upstream-failure","result":"recovered"}'
}

requested=${1:-all}
case "$requested" in
  all)
    drill_redis
    drill_worker
    drill_backend_replica
    drill_queue
    drill_database
    drill_caddy
    ;;
  redis) drill_redis ;;
  worker) drill_worker ;;
  backend) drill_backend_replica ;;
  queue) drill_queue ;;
  database) drill_database ;;
  caddy) drill_caddy ;;
  *) echo "Unknown drill: $requested" >&2; exit 2 ;;
esac
