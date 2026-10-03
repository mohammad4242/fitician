#!/usr/bin/env sh
set -eu

compose_file=${COMPOSE_FILE:-compose.prod.yaml}
rollback_compose_file=${ROLLBACK_COMPOSE_FILE:-}
image_tag=${IMAGE_TAG:?IMAGE_TAG is required}
previous_image_tag=${PREVIOUS_IMAGE_TAG:-}
initial_deploy=${INITIAL_DEPLOY:-false}
allow_schema_migrations=${ALLOW_SCHEMA_MIGRATIONS:-false}
first_scalability_release_approved=${FIRST_SCALABILITY_RELEASE_APPROVED:-false}
scalability_evidence_run_id=${SCALABILITY_EVIDENCE_RUN_ID:-}
app_dir=$(dirname "$compose_file")
env_file="$app_dir/.env"
marker="$app_dir/.deployed-image-tag"
scalability_marker="$app_dir/.scalability-foundation-accepted"
schema_changed=false
first_scalability_release=false

ensure_redis_password() {
  if grep -Eq '^REDIS_PASSWORD=.+$' "$env_file"; then
    return
  fi
  generated_password=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
  next_env=$(mktemp "$app_dir/.env.XXXXXXXX")
  cp "$env_file" "$next_env"
  printf '\nREDIS_PASSWORD=%s\n' "$generated_password" >> "$next_env"
  mv "$next_env" "$env_file"
}

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

ensure_redis_password

validate_scalability_marker() {
  python3 - "$scalability_marker" <<'PY'
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

path = Path(sys.argv[1])
values: dict[str, str] = {}
for raw_line in path.read_text(encoding="utf-8").splitlines():
    key, separator, value = raw_line.partition("=")
    if not separator or not key or key in values:
        raise SystemExit("invalid scalability acceptance marker")
    values[key] = value
required = {"foundation_version", "image_tag", "evidence_run_id", "accepted_at"}
if set(values) != required or values["foundation_version"] != "1":
    raise SystemExit("invalid scalability acceptance marker")
if re.fullmatch(r"[0-9a-f]{40}", values["image_tag"]) is None:
    raise SystemExit("invalid scalability acceptance marker")
if re.fullmatch(r"[0-9]+", values["evidence_run_id"]) is None:
    raise SystemExit("invalid scalability acceptance marker")
try:
    accepted_at = datetime.fromisoformat(values["accepted_at"].replace("Z", "+00:00"))
except ValueError as error:
    raise SystemExit("invalid scalability acceptance marker") from error
if accepted_at.tzinfo is None or accepted_at > datetime.now(UTC) + timedelta(minutes=5):
    raise SystemExit("invalid scalability acceptance marker")
PY
}

if [ -f "$scalability_marker" ]; then
  validate_scalability_marker
else
  first_scalability_release=true
  if [ "$first_scalability_release_approved" != true ]; then
    echo "First scalability release requires explicit acceptance approval" >&2
    exit 1
  fi
  printf '%s' "$scalability_evidence_run_id" | grep -Eq '^[0-9]+$' || {
    echo "First scalability release requires a valid heavy evidence run ID" >&2
    exit 1
  }
  python3 "$app_dir/ops/check-db-connection-budget.py" --replicas 2
  python3 "$app_dir/ops/check-runtime-capacity.py" --replicas 2 \
    --compose-file "$compose_file" --env-file "$app_dir/.env"
fi

# Capture persistent component versions before selecting a full release. Component
# releases do not alter the full-release marker or worker/agent image versions.
read_previous_tag() {
  value=$(awk -F= -v key="$1" '$1 == key {print $2}' "$env_file" | tail -n 1)
  if [ -z "$value" ]; then value=$previous_image_tag; fi
  if [ -n "$value" ]; then printf '%s' "$value" | grep -Eq '^[0-9a-f]{40}$'; fi
  printf '%s' "$value"
}
previous_frontend_tag=$(read_previous_tag FRONTEND_IMAGE_TAG)
previous_api_tag=$(read_previous_tag BACKEND_API_IMAGE_TAG)
previous_worker_tag=$(read_previous_tag WORKER_IMAGE_TAG)
previous_agent_tag=$(read_previous_tag AGENT_IMAGE_TAG)
# Capture the running immutable versions too, including releases made by the old
# manual frontend workflow (which did not persist a component tag).
running_previous_tag() {
  service=$1
  fallback=$2
  if [ "$initial_deploy" = true ]; then printf '%s' "$fallback"; return; fi
  id=$(IMAGE_TAG="$previous_image_tag" docker compose -f "$compose_file" ps -q "$service")
  test -n "$id"
  actual=$(docker inspect --format '{{.Config.Image}}' "$id")
  tag=${actual##*:}
  printf '%s' "$tag" | grep -Eq '^[0-9a-f]{40}$' || {
    echo "Running $service does not use an immutable SHA" >&2; return 1;
  }
  printf '%s' "$tag"
}
previous_frontend_tag=$(running_previous_tag frontend "$previous_frontend_tag")
previous_api_tag=$(running_previous_tag backend "$previous_api_tag")
previous_worker_tag=$(running_previous_tag scheduler "$previous_worker_tag")
previous_agent_tag=$(running_previous_tag agent-service "$previous_agent_tag")
if [ "$initial_deploy" != true ]; then
  test "$(running_previous_tag backend-2 "$previous_api_tag")" = "$previous_api_tag"
  for worker in food-photo-worker body-analysis-worker notification-worker; do
    test "$(running_previous_tag "$worker" "$previous_worker_tag")" = "$previous_worker_tag"
  done
fi
frontend_tag=$image_tag
api_tag=$image_tag
worker_tag=$image_tag
agent_tag=$image_tag

compose() {
  FRONTEND_IMAGE_TAG="$frontend_tag" BACKEND_API_IMAGE_TAG="$api_tag" \
  WORKER_IMAGE_TAG="$worker_tag" AGENT_IMAGE_TAG="$agent_tag" IMAGE_TAG="$image_tag" docker compose -f "$compose_file" "$@"
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
  rollback_current_revision=$(compose exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"')
  image_tag="$previous_image_tag"
  frontend_tag=$previous_frontend_tag
  api_tag=$previous_api_tag
  worker_tag=$previous_worker_tag
  agent_tag=$previous_agent_tag
  if [ -n "$rollback_compose_file" ] && [ -f "$rollback_compose_file" ]; then
    cp "$rollback_compose_file" "$compose_file"
  fi
  compose pull
  rollback_target_revision=$(compose run --rm --no-deps migrations alembic heads | \
    awk 'NR == 1 {print $1}')
  if [ -z "$rollback_current_revision" ] || \
    [ "$rollback_current_revision" != "$rollback_target_revision" ]; then
    echo "Rollback image schema is incompatible with the current database" >&2
    return 1
  fi
  compose up -d --wait --remove-orphans
  verify_runtime
  # Preserve actual mixed versions, including legacy manual frontend releases.
  restored_env=$(mktemp "$app_dir/.env.rollback.XXXXXXXX")
  awk -v frontend="$frontend_tag" -v api="$api_tag" \
      -v worker="$worker_tag" -v agent="$agent_tag" '
    /^(FRONTEND_IMAGE_TAG|BACKEND_API_IMAGE_TAG|WORKER_IMAGE_TAG|AGENT_IMAGE_TAG)=/ {next}
    {print}
    END {
      print "FRONTEND_IMAGE_TAG=" frontend
      print "BACKEND_API_IMAGE_TAG=" api
      print "WORKER_IMAGE_TAG=" worker
      print "AGENT_IMAGE_TAG=" agent
    }
  ' "$env_file" > "$restored_env"
  mv "$restored_env" "$env_file"
}

capture_failure_diagnostics() {
  compose ps || true
  for service in \
    notification-worker food-photo-worker body-analysis-worker scheduler \
    backend backend-2 frontend agent-service migrations; do
    container_id=$(compose ps -q "$service" 2>/dev/null || true)
    if [ -n "$container_id" ]; then
      docker inspect --format \
        'service={{index .Config.Labels "com.docker.compose.service"}} status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} oom={{.State.OOMKilled}} restarts={{.RestartCount}} health_log={{json .State.Health.Log}}' \
        "$container_id" || true
    fi
  done
  compose logs --no-color --tail=200 \
    notification-worker food-photo-worker body-analysis-worker scheduler \
    backend backend-2 frontend agent-service migrations || true
}

verify_runtime() {
  FRONTEND_IMAGE_TAG="$frontend_tag" BACKEND_API_IMAGE_TAG="$api_tag" \
  WORKER_IMAGE_TAG="$worker_tag" AGENT_IMAGE_TAG="$agent_tag" \
  COMPOSE_FILE="$compose_file" IMAGE_TAG="$image_tag" sh "$app_dir/ops/verify-production.sh"
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
  capture_failure_diagnostics
  rollback || true
  exit 1
fi

if ! verify_runtime; then
  capture_failure_diagnostics
  rollback || true
  exit 1
fi

next_env=$(mktemp "$app_dir/.env.XXXXXXXX")
awk -v tag="$image_tag" '
  /^(FRONTEND_IMAGE_TAG|BACKEND_API_IMAGE_TAG|WORKER_IMAGE_TAG|AGENT_IMAGE_TAG)=/ {next}
  /^IMAGE_TAG=/ {print "IMAGE_TAG=" tag; found=1; next}
  {print}
  END {if (!found) print "IMAGE_TAG=" tag}
' "$env_file" > "$next_env"
mv "$next_env" "$env_file"
next_marker=$(mktemp "$app_dir/.deployed-image-tag.XXXXXXXX")
printf '%s\n' "$image_tag" > "$next_marker"
mv "$next_marker" "$marker"
if [ "$first_scalability_release" = true ]; then
  next_scalability_marker=$(mktemp "$app_dir/.scalability-foundation-accepted.XXXXXXXX")
  printf 'foundation_version=1\nimage_tag=%s\nevidence_run_id=%s\naccepted_at=%s\n' \
    "$image_tag" "$scalability_evidence_run_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "$next_scalability_marker"
  mv "$next_scalability_marker" "$scalability_marker"
fi
# Preserve the exact currently deployed and preceding component SHAs for cleanup.
next_retention=$(mktemp "$app_dir/.image-retention.XXXXXXXX")
printf '%s\n' "$image_tag" "$previous_frontend_tag" "$previous_api_tag" \
  "$previous_worker_tag" "$previous_agent_tag" | sort -u > "$next_retention"
if [ "$(wc -l < "$next_retention")" -ge 2 ]; then
  mv "$next_retention" "$app_dir/.image-cleanup-protected-shas"
else
  rm -f "$next_retention"
fi

if [ -n "$rollback_compose_file" ]; then
  rm -f "$rollback_compose_file"
fi

echo "Production deployment verified for immutable image tag ${image_tag}"
