#!/usr/bin/env bash
set -euo pipefail

base_url=${BASE_URL:-http://127.0.0.1:8080}
deadline_seconds=${CI_SCALE_SMOKE_DEADLINE_SECONDS:-60}
compose=(docker compose -f compose.yaml -f compose.multi.yaml)
host=$(printf '%s' "$base_url" | sed -E 's#^[a-zA-Z]+://([^/:]+).*#\1#')

if [[ "$host" != "127.0.0.1" && "$host" != "localhost" && "$host" != "::1" ]]; then
  if [[ "${FITICIAN_ALLOW_PRODUCTION_FAILURE_DRILL:-false}" != "true" ]]; then
    echo "Refusing non-local CI replica smoke target: $host" >&2
    exit 2
  fi
fi

deadline=0
reset_deadline() { deadline=$((SECONDS + deadline_seconds)); }

instance_for_url() {
  curl --silent --show-error --dump-header - --output /dev/null --max-time 3 "$1/livez" |
    awk -F': ' 'tolower($1)=="x-fitician-instance" {gsub("\r", "", $2); print $2}'
}

collect_instances() {
  local count=${1:-24} instances="" instance
  for _ in $(seq 1 "$count"); do
    instance=$(instance_for_url "$base_url")
    [[ -n "$instance" ]] || return 1
    instances=$(printf '%s\n%s\n' "$instances" "$instance" | sed '/^$/d' | sort -u)
  done
  printf '%s\n' "$instances"
}

wait_for_status() {
  local url=$1 expected=$2 status
  reset_deadline
  while ((SECONDS < deadline)); do
    status=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 3 "$url" || true)
    [[ "$status" == "$expected" ]] && return 0
    sleep 1
  done
  echo "deadline exceeded waiting for $url status $expected" >&2
  return 1
}

wait_for_two_instances() {
  local instances count
  reset_deadline
  while ((SECONDS < deadline)); do
    instances=$(collect_instances || true)
    count=$(printf '%s\n' "$instances" | sed '/^$/d' | wc -l)
    if ((count >= 2)); then
      printf '%s\n' "$instances"
      return 0
    fi
    sleep 1
  done
  echo "deadline exceeded waiting for both backend replicas" >&2
  return 1
}

cleanup() { "${compose[@]}" start backend-2 >/dev/null 2>&1 || true; }
trap cleanup EXIT

before=$(wait_for_two_instances | tr '\n' ',' | sed 's/,$//')
failed_instance=$(instance_for_url http://127.0.0.1:8002)
[[ -n "$failed_instance" ]]

"${compose[@]}" stop backend-2 >/dev/null
wait_for_status "$base_url/readyz" 200
survivors=$(collect_instances 24)
if printf '%s\n' "$survivors" | grep -Fxq "$failed_instance"; then
  echo "Caddy routed to unavailable backend-2" >&2
  exit 1
fi
[[ $(printf '%s\n' "$survivors" | sed '/^$/d' | wc -l) -eq 1 ]]

"${compose[@]}" start backend-2 >/dev/null
wait_for_status http://127.0.0.1:8002/readyz 200
after=$(wait_for_two_instances | tr '\n' ',' | sed 's/,$//')

printf '{"smoke":"multi-replica","before":"%s","failed_instance":"%s","survivor":"%s","after":"%s"}\n' \
  "$before" "$failed_instance" "$survivors" "$after"
