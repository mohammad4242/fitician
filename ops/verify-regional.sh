#!/usr/bin/env sh
set -eu

region=${REGION:?REGION is required}
kind=${DEPLOY_KIND:?DEPLOY_KIND is required}
image_tag=${IMAGE_TAG:?IMAGE_TAG is required}
compose_file=${COMPOSE_FILE:?COMPOSE_FILE is required}
project=${COMPOSE_PROJECT_NAME:?COMPOSE_PROJECT_NAME is required}
env_file=${FITICIAN_ENV_FILE:?FITICIAN_ENV_FILE is required}

compose() {
  COMPOSE_PROJECT_NAME="$project" FITICIAN_ENV_FILE="$env_file" \
    IMAGE_TAG="$image_tag" FRONTEND_IMAGE_TAG="${FRONTEND_IMAGE_TAG:-$image_tag}" \
    BACKEND_API_IMAGE_TAG="${BACKEND_API_IMAGE_TAG:-$image_tag}" \
    WORKER_IMAGE_TAG="${WORKER_IMAGE_TAG:-$image_tag}" \
    AGENT_IMAGE_TAG="${AGENT_IMAGE_TAG:-$image_tag}" \
    docker compose -p "$project" --env-file "$env_file" -f "$compose_file" "$@"
}

require_healthy() {
  service=$1
  expected_tag=$2
  expected_image=$3
  id=$(compose ps -q "$service")
  if [ -z "$id" ]; then echo "Required service is missing: $service" >&2; return 1; fi
  health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$id")
  if [ "$health" != healthy ]; then echo "Service is unhealthy: $service ($health)" >&2; return 1; fi
  if [ -n "$expected_image" ]; then
    image=$(docker inspect --format '{{.Config.Image}}' "$id")
    case "$image" in */"$expected_image":"$expected_tag") ;; *)
      echo "Immutable image mismatch: $service uses $image" >&2; return 1 ;;
    esac
  fi
}

require_image_tag() {
  service=$1
  expected_tag=$2
  expected_image=$3
  id=$(compose ps -q "$service")
  if [ -z "$id" ]; then echo "Required service is missing: $service" >&2; return 1; fi
  image=$(docker inspect --format '{{.Config.Image}}' "$id")
  case "$image" in */"$expected_image":"$expected_tag") ;; *)
    echo "Immutable image mismatch: $service uses $image" >&2; return 1 ;;
  esac
}

require_running() {
  service=$1
  id=$(compose ps -q "$service")
  if [ -z "$id" ]; then echo "Required service is missing: $service" >&2; return 1; fi
  state=$(docker inspect --format '{{.State.Status}}' "$id")
  if [ "$state" != running ]; then echo "Service is not running: $service" >&2; return 1; fi
}

for command in docker; do
  command -v "$command" >/dev/null || { echo "$command is required" >&2; exit 1; }
done
printf '%s' "$image_tag" | grep -Eq '^[0-9a-f]{40}$' || {
  echo 'IMAGE_TAG must be a full Git SHA' >&2; exit 1;
}

case "$region:$kind" in
  iran:full)
    require_healthy db '' ''
    require_healthy redis '' ''
    require_healthy backend "$BACKEND_API_IMAGE_TAG" fitician-backend
    require_healthy backend-2 "$BACKEND_API_IMAGE_TAG" fitician-backend
    require_healthy scheduler "$WORKER_IMAGE_TAG" fitician-backend
    require_healthy food-photo-worker "$WORKER_IMAGE_TAG" fitician-backend
    require_healthy body-analysis-worker "$WORKER_IMAGE_TAG" fitician-backend
    require_healthy notification-worker "$WORKER_IMAGE_TAG" fitician-backend
    require_healthy frontend "$FRONTEND_IMAGE_TAG" fitician-frontend
    require_running caddy
    compose exec -T db sh -c \
      'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null && psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT 1" | grep -qx 1'
    compose exec -T redis sh -c \
      'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli ping | grep -qx PONG'
    current_revision=$(compose exec -T db sh -c \
      'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"')
    target_revision=$(compose run --pull never --rm --no-deps migrations alembic heads | awk 'NR == 1 {print $1}')
    [ -n "$current_revision" ] && [ "$current_revision" = "$target_revision" ] || {
      echo 'Alembic revision mismatch' >&2; exit 1;
    }
    for service in backend backend-2; do
      compose exec -T "$service" python -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=5).read(); urllib.request.urlopen('http://127.0.0.1:8000/livez', timeout=5).read()" >/dev/null
    done
    # The Iran release does not gate on Agent Service readiness.
    domain=$(awk -F= '$1 == "FITICIAN_DOMAIN" {value=$2} END {print value}' "$env_file")
    [ -n "$domain" ] || domain=fitician.fit
    curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 2 \
      --resolve "$domain:443:127.0.0.1" \
      --connect-timeout 5 --max-time 15 "https://$domain/healthz" >/dev/null
    ;;
  iran:frontend)
    require_healthy frontend "$FRONTEND_IMAGE_TAG" fitician-frontend
    domain=$(awk -F= '$1 == "FITICIAN_DOMAIN" {value=$2} END {print value}' "$env_file")
    [ -n "$domain" ] || domain=fitician.fit
    curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 2 \
      --resolve "$domain:443:127.0.0.1" \
      --connect-timeout 5 --max-time 15 "https://$domain/healthz" >/dev/null
    ;;
  iran:backend)
    require_healthy backend "$BACKEND_API_IMAGE_TAG" fitician-backend
    require_healthy backend-2 "$BACKEND_API_IMAGE_TAG" fitician-backend
    current_revision=$(compose exec -T db sh -c \
      'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"')
    target_revision=$(compose exec -T backend alembic heads | awk 'NR == 1 {print $1}')
    [ -n "$current_revision" ] && [ "$current_revision" = "$target_revision" ] || {
      echo 'Alembic revision mismatch' >&2; exit 1;
    }
    domain=$(awk -F= '$1 == "FITICIAN_DOMAIN" {value=$2} END {print value}' "$env_file")
    [ -n "$domain" ] || domain=fitician.fit
    curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 2 \
      --resolve "$domain:443:127.0.0.1" \
      --connect-timeout 5 --max-time 15 "https://$domain/healthz" >/dev/null
    ;;
  germany:agent)
    require_healthy agent-service "$AGENT_IMAGE_TAG" fitician-agent
    compose exec -T agent-service python -c '
import json
import os
import urllib.request

token = os.environ["AGENT_SERVICE_TOKEN"]
request = urllib.request.Request(
    "http://127.0.0.1:9001/v1/capabilities",
    headers={"Authorization": "Bearer " + token},
)
with urllib.request.urlopen(request, timeout=10) as response:
    if response.status != 200:
        raise SystemExit("authenticated capabilities check failed")
    payload = json.loads(response.read())
if not isinstance(payload.get("runners"), list):
    raise SystemExit("authenticated capabilities response is invalid")
print("authenticated capabilities check passed")
'
    ;;
  *) echo 'Unsupported regional verification target' >&2; exit 1 ;;
esac

echo "Regional topology verified: $region $kind ($image_tag)"
