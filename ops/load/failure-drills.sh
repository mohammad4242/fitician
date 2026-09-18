#!/usr/bin/env bash
set -euo pipefail

base_url=${BASE_URL:-http://127.0.0.1:8080}
direct_backend_url=${DIRECT_BACKEND_URL:-http://127.0.0.1:8001}
deadline_seconds=${FAILURE_DRILL_DEADLINE_SECONDS:-120}
backlog_size=${FAILURE_DRILL_BACKLOG_SIZE:-50}
backlog_max_drain_seconds=${FAILURE_DRILL_BACKLOG_MAX_DRAIN_SECONDS:-90}
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

deadline=0
reset_deadline() { deadline=$((SECONDS + deadline_seconds)); }

wait_for_status() {
  local url=$1 expected=$2
  reset_deadline
  while (( SECONDS < deadline )); do
    status=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 3 "$url" || true)
    [[ "$status" == "$expected" ]] && return 0
    sleep 1
  done
  echo "deadline exceeded waiting for $url status $expected" >&2
  return 1
}

wait_for_ready_check() {
  local name=$1 expected=$2
  reset_deadline
  while (( SECONDS < deadline )); do
    payload=$(curl --silent --max-time 3 "$direct_backend_url/readyz" || true)
    if PAYLOAD="$payload" CHECK_NAME="$name" EXPECTED="$expected" python3 -c \
      'import json,os,sys; d=json.loads(os.environ["PAYLOAD"]); sys.exit(d.get("checks",{}).get(os.environ["CHECK_NAME"]) != os.environ["EXPECTED"])' 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  echo "deadline exceeded waiting for readiness check $name=$expected" >&2
  return 1
}

wait_for_service_health() {
  local service=$1
  reset_deadline
  while (( SECONDS < deadline )); do
    container_id=$("${compose[@]}" ps -q "$service")
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$container_id" 2>/dev/null || true)
    [[ "$health" == "healthy" ]] && return 0
    sleep 1
  done
  echo "deadline exceeded waiting for healthy service $service" >&2
  return 1
}

json_value() {
  local key=$1
  python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$key"
}

redis_has_key() {
  local pattern=$1
  "${compose[@]}" exec -T redis sh -c \
    'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli --scan --pattern "$1" | head -n 1 | grep -q .' \
    sh "$pattern"
}

collect_instances() {
  local count=${1:-30} instances=""
  for _ in $(seq 1 "$count"); do
    headers=$(curl --silent --show-error --dump-header - --output /dev/null --max-time 3 "$base_url/livez")
    instance=$(printf '%s' "$headers" | awk -F': ' 'tolower($1)=="x-fitician-instance" {gsub("\r", "", $2); print $2}')
    [[ -n "$instance" ]] || return 1
    instances=$(printf '%s\n%s\n' "$instances" "$instance" | sed '/^$/d' | sort -u)
  done
  printf '%s\n' "$instances"
}

wait_for_two_instances() {
  reset_deadline
  while (( SECONDS < deadline )); do
    instances=$(collect_instances 20 || true)
    count=$(printf '%s\n' "$instances" | sed '/^$/d' | wc -l)
    if (( count >= 2 )); then
      printf '%s\n' "$instances"
      return 0
    fi
    sleep 1
  done
  echo "deadline exceeded waiting for traffic on two backend replicas" >&2
  return 1
}

fixture() { "${compose[@]}" exec -T backend python -m app.jobs.local_acceptance "$@"; }

wait_for_body_claim() {
  local analysis_id=$1
  reset_deadline
  while (( SECONDS < deadline )); do
    payload=$(fixture inspect-body --analysis-id "$analysis_id")
    if PAYLOAD="$payload" python3 -c \
      'import json,os,sys; d=json.loads(os.environ["PAYLOAD"]); sys.exit(not d.get("locked_by") or d.get("status") != "analyzing" or d.get("attempt_count") != 1)'; then
      printf '%s\n' "$payload"
      return 0
    fi
    sleep 1
  done
  echo "deadline exceeded waiting for Body Analysis claim" >&2
  return 1
}

wait_for_body_terminal() {
  local analysis_id=$1
  reset_deadline
  while (( SECONDS < deadline )); do
    payload=$(fixture inspect-body --analysis-id "$analysis_id")
    if PAYLOAD="$payload" python3 -c \
      'import json,os,sys; d=json.loads(os.environ["PAYLOAD"]); sys.exit(d.get("status") != "review_pending" or d.get("result_version_count") != 1)'; then
      printf '%s\n' "$payload"
      return 0
    fi
    sleep 1
  done
  echo "deadline exceeded waiting for exactly-once Body Analysis terminal result" >&2
  return 1
}

wait_for_body_reclaim() {
  local analysis_id=$1 old_worker_id=$2
  reset_deadline
  while (( SECONDS < deadline )); do
    payload=$(fixture inspect-body --analysis-id "$analysis_id")
    if PAYLOAD="$payload" OLD_WORKER_ID="$old_worker_id" python3 -c \
      'import json,os,sys; d=json.loads(os.environ["PAYLOAD"]); sys.exit(not d.get("locked_by") or d.get("locked_by") == os.environ["OLD_WORKER_ID"] or d.get("status") != "analyzing" or d.get("attempt_count") != 2)'; then
      printf '%s\n' "$payload"
      return 0
    fi
    sleep 1
  done
  echo "deadline exceeded waiting for replacement worker reclaim" >&2
  return 1
}

wait_for_batch_drain() {
  local batch_id=$1 expected=$2 drain_deadline=$((SECONDS + backlog_max_drain_seconds))
  while (( SECONDS < drain_deadline )); do
    payload=$(fixture inspect-batch --batch-id "$batch_id")
    if PAYLOAD="$payload" EXPECTED="$expected" python3 -c \
      'import json,os,sys; d=json.loads(os.environ["PAYLOAD"]); n=int(os.environ["EXPECTED"]); sys.exit(d.get("terminal") != n or d.get("max_result_versions") != 1)'; then
      printf '%s\n' "$payload"
      return 0
    fi
    sleep 1
  done
  echo "queue did not drain within ${backlog_max_drain_seconds}s" >&2
  return 1
}

cleanup_member_id=""
cleanup_batch_id=""
worker_container_id=""
cleanup() {
  if [[ -n "$worker_container_id" ]]; then
    docker update --restart=unless-stopped "$worker_container_id" >/dev/null 2>&1 || true
  fi
  "${compose[@]}" start db redis backend backend-2 body-analysis-worker >/dev/null 2>&1 || true
  [[ -z "$cleanup_member_id" ]] || fixture cleanup-member --user-id "$cleanup_member_id" >/dev/null 2>&1 || true
  [[ -z "$cleanup_batch_id" ]] || fixture cleanup-batch --batch-id "$cleanup_batch_id" >/dev/null 2>&1 || true
}
trap cleanup EXIT

drill_redis() {
  local actor="redis-drill-$PPID-$SECONDS@example.com"
  member=$(fixture seed-catalogue-member)
  member_id=$(printf '%s' "$member" | json_value user_id)
  cleanup_member_id=$member_id
  cookie_name=$(printf '%s' "$member" | json_value session_cookie_name)
  session_token=$(printf '%s' "$member" | json_value session_token)
  "${compose[@]}" stop redis >/dev/null
  status=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 5 \
    --cookie "$cookie_name=$session_token" "$base_url/api/v1/nutrition/foods" || true)
  [[ "$status" == 200 ]] || { echo "cached catalogue PostgreSQL fallback failed" >&2; return 1; }
  wait_for_status "$direct_backend_url/livez" 200
  wait_for_status "$direct_backend_url/readyz" 200
  wait_for_ready_check redis degraded

  limited=0
  for _ in $(seq 1 7); do
    status=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 5 \
      -H 'Content-Type: application/json' -H 'Origin: http://localhost:5173' \
      --data "{\"email\":\"$actor\",\"password\":\"wrong password\"}" \
      "$base_url/api/v1/auth/login" || true)
    if [[ "$status" == "429" ]]; then limited=1; break; fi
  done
  [[ "$limited" == "1" ]] || { echo "PostgreSQL rate-limit fallback did not enforce 429" >&2; return 1; }

  "${compose[@]}" start redis >/dev/null
  wait_for_ready_check redis ok
  curl --fail --silent --show-error --max-time 5 --cookie "$cookie_name=$session_token" \
    "$base_url/api/v1/nutrition/foods" >/dev/null
  redis_has_key 'fitician:cache:v1:*'
  recovery_actor="redis-recovery-$PPID-$SECONDS@example.com"
  curl --silent --output /dev/null --max-time 5 \
    -H 'Content-Type: application/json' -H 'Origin: http://localhost:5173' \
    --data "{\"email\":\"$recovery_actor\",\"password\":\"wrong password\"}" \
    "$base_url/api/v1/auth/login"
  redis_has_key 'fitician:rate:v1:auth:*'
  fixture cleanup-member --user-id "$member_id" >/dev/null
  cleanup_member_id=""
  printf '%s\n' '{"drill":"redis-unavailable","cache_fallback":true,"readiness_degraded":true,"postgres_rate_limit":true,"redis_recovered":true}'
}

drill_worker() {
  wait_for_service_health body-analysis-worker
  seed=$(fixture seed-body --count 1 --delay-seconds 20)
  analysis_id=$(SEED="$seed" python3 -c 'import json,os; print(json.loads(os.environ["SEED"])["analysis_ids"][0])')
  batch_id=$(printf '%s' "$seed" | json_value batch_id)
  cleanup_batch_id=$batch_id
  worker_container_id=$("${compose[@]}" ps -q body-analysis-worker)
  claimed=$(wait_for_body_claim "$analysis_id")
  old_worker_id=$(printf '%s' "$claimed" | json_value locked_by)
  docker update --restart=no "$worker_container_id" >/dev/null
  "${compose[@]}" kill -s SIGKILL body-analysis-worker >/dev/null
  reset_deadline
  while (( SECONDS < deadline )); do
    worker_state=$(docker inspect --format '{{.State.Status}}' "$worker_container_id" 2>/dev/null || true)
    [[ "$worker_state" == exited ]] && break
    sleep 1
  done
  [[ "${worker_state:-}" == exited ]] || { echo "worker did not remain stopped after SIGKILL" >&2; return 1; }
  durable=$(fixture inspect-body --analysis-id "$analysis_id")
  PAYLOAD="$durable" python3 -c \
    'import json,os,sys; d=json.loads(os.environ["PAYLOAD"]); sys.exit(not d.get("locked_by") or d.get("result_version_count") != 0)'
  fixture expire-body-lease --analysis-id "$analysis_id" >/dev/null
  docker update --restart=unless-stopped "$worker_container_id" >/dev/null
  "${compose[@]}" start body-analysis-worker >/dev/null
  wait_for_service_health body-analysis-worker
  reclaimed=$(wait_for_body_reclaim "$analysis_id" "$old_worker_id")
  terminal=$(wait_for_body_terminal "$analysis_id")
  fixture cleanup-batch --batch-id "$batch_id" >/dev/null
  cleanup_batch_id=""
  printf '%s\n' "$terminal" | RECLAIMED="$reclaimed" OLD_WORKER_ID="$old_worker_id" python3 -c \
    'import json,os,sys; d=json.load(sys.stdin); reclaimed=json.loads(os.environ["RECLAIMED"]); assert reclaimed["locked_by"] != os.environ["OLD_WORKER_ID"]; assert d["attempt_count"] == 2; print(json.dumps({"drill":"worker-killed-mid-job","durable":True,"reclaimed":True,"old_worker_id":os.environ["OLD_WORKER_ID"],"replacement_worker_id":reclaimed["locked_by"],"attempt_count":d["attempt_count"],"terminal":d["status"],"result_version_count":d["result_version_count"]}, separators=(",",":")))'
  worker_container_id=""
}

drill_backend_replica() {
  before=$(wait_for_two_instances | tr '\n' ',' | sed 's/,$//')
  failed_instance=$(curl --silent --dump-header - --output /dev/null --max-time 3 http://127.0.0.1:8002/livez | awk -F': ' 'tolower($1)=="x-fitician-instance" {gsub("\r", "", $2); print $2}')
  "${compose[@]}" stop backend-2 >/dev/null
  wait_for_status "$base_url/livez" 200
  surviving=$(collect_instances 25)
  if printf '%s\n' "$surviving" | grep -Fxq "$failed_instance"; then echo "Caddy routed to stopped backend-2" >&2; return 1; fi
  "${compose[@]}" start backend-2 >/dev/null
  wait_for_status http://127.0.0.1:8002/readyz 200
  after=$(wait_for_two_instances | tr '\n' ',' | sed 's/,$//')
  printf '{"drill":"backend-replica-killed","before":"%s","survivor":"%s","after":"%s"}\n' "$before" "$surviving" "$after"
}

drill_database() {
  "${compose[@]}" stop db >/dev/null
  wait_for_status "$direct_backend_url/readyz" 503
  wait_for_status "$direct_backend_url/livez" 200
  "${compose[@]}" start db >/dev/null
  wait_for_status "$direct_backend_url/readyz" 200
  wait_for_status "$base_url/api/v1/exercise-categories" 200
  printf '%s\n' '{"drill":"database-unavailable","readiness_failed":true,"liveness_ok":true,"recovered":true}'
}

drill_queue() {
  "${compose[@]}" stop body-analysis-worker >/dev/null
  seed=$(fixture seed-body --count "$backlog_size" --delay-seconds 0)
  batch_id=$(printf '%s' "$seed" | json_value batch_id)
  cleanup_batch_id=$batch_id
  metrics=$(curl --fail --silent --show-error --max-time 10 "$base_url/metrics")
  depth=$(printf '%s\n' "$metrics" | awk '/fitician_queue_queued_jobs\{queue="body_analysis"\}/ {print int($2)}')
  [[ -n "$depth" && "$depth" -ge "$backlog_size" ]] || { echo "queue depth did not increase" >&2; return 1; }
  printf '%s\n' "$metrics" | grep -q 'fitician_queue_oldest_job_age_seconds{queue="body_analysis"}'
  started=$SECONDS
  "${compose[@]}" start body-analysis-worker >/dev/null
  wait_for_service_health body-analysis-worker
  wait_for_batch_drain "$batch_id" "$backlog_size" >/dev/null
  duration=$((SECONDS - started))
  fixture cleanup-batch --batch-id "$batch_id" >/dev/null
  cleanup_batch_id=""
  printf '{"drill":"queue-backlog","seeded":%d,"observed_depth":%d,"drain_seconds":%d,"terminal":%d}\n' "$backlog_size" "$depth" "$duration" "$backlog_size"
}

drill_caddy() {
  failed_instance=$(curl --silent --dump-header - --output /dev/null --max-time 3 http://127.0.0.1:8002/livez | awk -F': ' 'tolower($1)=="x-fitician-instance" {gsub("\r", "", $2); print $2}')
  "${compose[@]}" stop backend-2 >/dev/null
  routed=$(collect_instances 40)
  if printf '%s\n' "$routed" | grep -Fxq "$failed_instance"; then echo "unavailable Caddy upstream still received traffic" >&2; return 1; fi
  "${compose[@]}" start backend-2 >/dev/null
  wait_for_status http://127.0.0.1:8002/readyz 200
  wait_for_two_instances >/dev/null
  printf '%s\n' '{"drill":"caddy-upstream-failure","failed_upstream_removed":true,"survivor_served":true,"rejoined":true}'
}

requested=${1:-all}
case "$requested" in
  all) drill_redis; drill_worker; drill_backend_replica; drill_queue; drill_database; drill_caddy ;;
  redis) drill_redis ;;
  worker) drill_worker ;;
  backend) drill_backend_replica ;;
  queue) drill_queue ;;
  database) drill_database ;;
  caddy) drill_caddy ;;
  *) echo "Unknown drill: $requested" >&2; exit 2 ;;
esac
