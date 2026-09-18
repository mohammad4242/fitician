#!/usr/bin/env sh
set -eu

compose_file=${COMPOSE_FILE:-compose.prod.yaml}
image_tag=${IMAGE_TAG:?IMAGE_TAG is required}
app_dir=$(dirname "$compose_file")

printf '%s' "$image_tag" | grep -Eq '^[0-9a-f]{40}$' || {
  echo "IMAGE_TAG must be a full Git SHA" >&2
  exit 1
}

compose() {
  IMAGE_TAG="$image_tag" docker compose -f "$compose_file" "$@"
}

container_id() {
  compose ps -q "$1"
}

require_healthy() {
  service=$1
  id=$(container_id "$service")
  if [ -z "$id" ]; then
    echo "Required service is not running: $service" >&2
    return 1
  fi
  health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$id")
  if [ "$health" != healthy ]; then
    echo "Required service is unhealthy: $service ($health)" >&2
    return 1
  fi
}

require_image_tag() {
  service=$1
  id=$(container_id "$service")
  if [ -z "$id" ]; then
    echo "Required service is not running: $service" >&2
    return 1
  fi
  image=$(docker inspect --format '{{.Config.Image}}' "$id")
  case "$image" in
    *:"$image_tag") ;;
    *)
      echo "Immutable image mismatch: $service uses $image" >&2
      return 1
      ;;
  esac
}

for command in docker curl python3; do
  command -v "$command" >/dev/null || {
    echo "$command is required for production verification" >&2
    exit 1
  }
done

python3 "$app_dir/ops/check-db-connection-budget.py" --replicas 2 >/dev/null
python3 "$app_dir/ops/check-runtime-capacity.py" --replicas 2 --compose-file "$compose_file" >/dev/null

for service in agent-service backend backend-2 food-photo-worker body-analysis-worker notification-worker scheduler frontend; do
  require_image_tag "$service"
done

for service in body-analysis-worker food-photo-worker notification-worker scheduler; do
  require_healthy "$service"
done

compose exec -T db sh -c \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null && psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT 1" | grep -qx 1'

current_revision=$(compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"')
target_revision=$(compose run --rm --no-deps migrations alembic heads | awk 'NR == 1 {print $1}')
if [ -z "$current_revision" ] || [ "$current_revision" != "$target_revision" ]; then
  echo "Alembic revision mismatch: current=$current_revision target=$target_revision" >&2
  exit 1
fi

compose exec -T redis sh -c \
  'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli ping | grep -qx PONG'
require_healthy redis

for service in backend backend-2; do
  compose exec -T "$service" python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=5).read()" >/dev/null
done
compose exec -T frontend wget -qO- http://127.0.0.1/healthz >/dev/null

domain=$(compose exec -T caddy sh -c 'printf %s "$FITICIAN_DOMAIN"')
if [ -z "$domain" ]; then
  echo "HTTPS ingress domain is missing" >&2
  exit 1
fi
deadline=$(($(date +%s) + 60))
while [ "$(date +%s)" -lt "$deadline" ]; do
  if curl --fail --silent --show-error --max-time 5 \
    --resolve "$domain:443:127.0.0.1" "https://$domain/healthz" >/dev/null 2>&1; then
    echo "Production topology verified for immutable image tag $image_tag"
    exit 0
  fi
  sleep 2
done

echo "HTTPS ingress readiness check failed" >&2
exit 1
