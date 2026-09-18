#!/usr/bin/env sh
set -eu

compose_file=${COMPOSE_FILE:-compose.prod.yaml}
image_tag=${IMAGE_TAG:?IMAGE_TAG is required}
previous_image_tag=${PREVIOUS_IMAGE_TAG:-}
initial_deploy=${INITIAL_DEPLOY:-false}
allow_schema_migrations=${ALLOW_SCHEMA_MIGRATIONS:-false}
app_dir=$(dirname "$compose_file")
marker="$app_dir/.deployed-image-tag"
schema_changed=false

printf '%s' "$image_tag" | grep -Eq '^[0-9a-f]{40}$' || {
  echo "IMAGE_TAG must be a full Git SHA" >&2
  exit 1
}
if [ -z "$previous_image_tag" ] && [ -f "$marker" ]; then
  previous_image_tag=$(cat "$marker")
fi
if [ "$initial_deploy" = true ]; then
  if [ -f "$marker" ]; then
    echo "INITIAL_DEPLOY cannot replace an existing deployment" >&2
    exit 1
  fi
elif [ -z "$previous_image_tag" ]; then
  echo "Initial database restore and manual deployment are required" >&2
  exit 1
fi

compose() {
  IMAGE_TAG="$image_tag" docker compose -f "$compose_file" "$@"
}

rollback() {
  if [ "$schema_changed" = true ]; then
    echo "Schema changed; manual recovery from the encrypted backup is required" >&2
    return 1
  fi
  if [ -z "$previous_image_tag" ]; then
    echo "Deployment failed and PREVIOUS_IMAGE_TAG is not set" >&2
    return 1
  fi
  echo "Rolling back to previous immutable image tag"
  image_tag="$previous_image_tag"
  compose pull
  compose up -d --wait --remove-orphans
  verify_runtime
}

verify_runtime() {
  running_services=$(compose ps --status running --services)
  for service in backend backend-2 redis food-photo-worker body-analysis-worker notification-worker scheduler frontend caddy; do
    if ! printf '%s\n' "$running_services" | grep -Fxq "$service"; then
      echo "Required service is not running: $service" >&2
      return 1
    fi
  done
  for backend_service in backend backend-2; do
    if ! compose exec -T "$backend_service" python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5).read()" >/dev/null; then
      echo "Backend readiness check failed: $backend_service" >&2
      return 1
    fi
  done
  if ! compose exec -T frontend wget -qO- http://127.0.0.1/healthz >/dev/null; then
    echo "Frontend readiness check failed" >&2
    return 1
  fi
  domain=$(compose exec -T caddy sh -c 'printf %s "$FITICIAN_DOMAIN"')
  if [ -z "$domain" ]; then
    echo "HTTPS ingress domain is missing" >&2
    return 1
  fi
  attempt=0
  while [ "$attempt" -lt 12 ]; do
    if curl --fail --silent --show-error --max-time 5 \
      --resolve "$domain:443:127.0.0.1" "https://$domain/healthz" >/dev/null 2>&1; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 5
  done
  echo "HTTPS ingress readiness check failed" >&2
  return 1
}

if [ "$initial_deploy" != true ]; then
  COMPOSE_FILE="$compose_file" bash "$app_dir/backup-production.sh"
else
  compose up -d --wait db
  restored_users=$(compose exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM users"')
  if [ "$restored_users" -le 0 ]; then
    echo "Initial deployment requires the restored member database" >&2
    exit 1
  fi
fi

if ! compose pull; then
  echo "Unable to pull immutable production images" >&2
  exit 1
fi

if [ "$initial_deploy" != true ]; then
  current_revision=$(compose exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"')
  target_revision=$(compose run --rm --no-deps migrations alembic heads | awk 'NR == 1 {print $1}')
  if [ -z "$current_revision" ] || [ -z "$target_revision" ]; then
    echo "Could not verify Alembic revisions" >&2
    exit 1
  fi
  if [ "$current_revision" != "$target_revision" ]; then
    schema_changed=true
    if [ "$allow_schema_migrations" != true ]; then
      echo "Pending schema migration requires a manual release" >&2
      exit 1
    fi
  fi
fi

if ! compose up -d --wait --remove-orphans; then
  rollback || true
  exit 1
fi

if ! verify_runtime; then
  rollback || true
  exit 1
fi

env_file="$app_dir/.env"
next_env=$(mktemp "$app_dir/.env.XXXXXXXX")
awk -v tag="$image_tag" '
  /^IMAGE_TAG=/ {print "IMAGE_TAG=" tag; found=1; next}
  {print}
  END {if (!found) print "IMAGE_TAG=" tag}
' "$env_file" > "$next_env"
mv "$next_env" "$env_file"
next_marker=$(mktemp "$app_dir/.deployed-image-tag.XXXXXXXX")
printf '%s\n' "$image_tag" > "$next_marker"
mv "$next_marker" "$marker"

echo "Production deployment verified for immutable image tag ${image_tag}"
