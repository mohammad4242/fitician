#!/usr/bin/env bash
set -euo pipefail

scenario=${1:-health}
base_url=${BASE_URL:-http://127.0.0.1:8080}
host=$(printf '%s' "$base_url" | sed -E 's#^[a-zA-Z]+://([^/:]+).*#\1#')
if [[ "$host" != "127.0.0.1" && "$host" != "localhost" && "$host" != "::1" ]]; then
  if [[ "${FITICIAN_ALLOW_PRODUCTION_LOAD:-false}" != "true" ]]; then
    echo "Refusing non-local load target: $host" >&2
    exit 2
  fi
fi

case "$scenario" in
  health)
    path=${LOAD_PATH:-/livez}
    requests=${LOAD_REQUESTS:-100}
    concurrency=${LOAD_CONCURRENCY:-10}
    p95=${LOAD_MAX_P95_MS:-750}
    ;;
  catalogue)
    path=${LOAD_CATALOGUE_PATH:-/api/v1/exercise-categories}
    requests=${LOAD_REQUESTS:-200}
    concurrency=${LOAD_CONCURRENCY:-20}
    p95=${LOAD_MAX_P95_MS:-300}
    ;;
  custom)
    : "${LOAD_PATH:?LOAD_PATH is required for custom scenario}"
    path=$LOAD_PATH
    requests=${LOAD_REQUESTS:-100}
    concurrency=${LOAD_CONCURRENCY:-10}
    p95=${LOAD_MAX_P95_MS:-750}
    ;;
  *)
    echo "Unknown scenario: $scenario (health, catalogue, custom)" >&2
    exit 2
    ;;
esac

exec python3 ops/load/http_smoke.py \
  --base-url "$base_url" \
  --path "$path" \
  --requests "$requests" \
  --concurrency "$concurrency" \
  --max-p95-ms "$p95"
