#!/usr/bin/env bash
set -Eeuo pipefail

region=${REGION:?REGION is required}
kind=${DEPLOY_KIND:?DEPLOY_KIND is required}
image_tag=${IMAGE_TAG:?IMAGE_TAG is required}
app_dir=${APP_DIR:?APP_DIR is required}
release_dir=${RELEASE_DIR:?RELEASE_DIR is required}
compose_file=${COMPOSE_FILE:?COMPOSE_FILE is required}
project=${COMPOSE_PROJECT_NAME:?COMPOSE_PROJECT_NAME is required}
env_file=${FITICIAN_ENV_FILE:-"$app_dir/.env"}
owner_approved=${OWNER_APPROVED:-false}
allow_schema_migrations=${ALLOW_SCHEMA_MIGRATIONS:-false}
inspect_only=${INSPECT_ONLY:-false}
initial_deploy=${INITIAL_DEPLOY:-false}
image_source=${IMAGE_SOURCE:-registry}
first_scalability_approved=${FIRST_SCALABILITY_RELEASE_APPROVED:-false}
scalability_run_id=${SCALABILITY_EVIDENCE_RUN_ID:-}

fail() {
  echo "$1" >&2
  if [[ "${rollback_needed:-false}" == true ]] && declare -F rollback >/dev/null; then
    rollback
  fi
  exit 1
}
[[ "$image_tag" =~ ^[0-9a-f]{40}$ ]] || fail 'IMAGE_TAG must be a full Git SHA'
[[ "$project" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || fail 'Invalid Compose project name'
[[ "$owner_approved" == true ]] || fail 'Regional deployment requires owner approval'
[[ "$initial_deploy" == true || "$initial_deploy" == false ]] || fail 'INITIAL_DEPLOY must be true or false'
[[ "$image_source" == registry || "$image_source" == preloaded ]] || fail 'IMAGE_SOURCE must be registry or preloaded'
[[ -f "$env_file" && -s "$env_file" ]] || fail 'Regional application env file is missing'
[[ -d "$release_dir" && -f "$compose_file" ]] || fail 'Candidate release contract is missing'
[[ "$release_dir" == "$app_dir/releases/$image_tag" ]] || fail 'Release directory must be releases/<IMAGE_TAG>'
case "$compose_file" in "$release_dir"/compose.prod."$region".yaml) ;; *) fail 'Unexpected regional Compose contract path' ;; esac

case "$region:$kind" in
  iran:full|iran:frontend|iran:backend|germany:agent) ;;
  *) fail 'Unsupported regional deployment kind' ;;
esac
if [[ "$kind" == full || "$kind" == backend || "$kind" == frontend ]]; then
  [[ "$region" == iran ]] || fail 'Database and application releases are restricted to Iran'
fi

for command in docker python3; do command -v "$command" >/dev/null || fail "$command is required"; done
active_marker="$app_dir/.regional-$region-active-contract"
active_contract=''
if [[ -f "$active_marker" ]]; then
  [[ "$initial_deploy" != true ]] || fail 'INITIAL_DEPLOY cannot replace an existing regional deployment'
  active_contract=$(cat "$active_marker")
  case "$active_contract" in "$app_dir"/releases/*/compose.prod."$region".yaml) ;; *) fail 'Active contract marker is invalid' ;; esac
  [[ -f "$active_contract" ]] || fail 'Active regional contract is missing'
elif [[ "$initial_deploy" != true ]]; then
  fail 'Regional deployment has no active contract marker; use the approved initial deployment path'
fi
if [[ "$initial_deploy" == true && "$kind" == full && "$region" != iran ]]; then
  fail 'Only Iran full release supports initial database deployment'
fi
if [[ "$initial_deploy" == true && "$kind" == agent && "$region" != germany ]]; then
  fail 'Agent adoption is restricted to Germany'
fi
if [[ "$initial_deploy" == true && "$kind" != full && "$kind" != agent ]]; then
  fail 'Initial deployment only supports Iran full or Germany Agent Service'
fi
scalability_marker="$app_dir/.scalability-foundation-accepted"
first_scalability_release=false
if [[ "$region" == iran ]]; then
  if [[ -f "$scalability_marker" ]]; then
    python3 - "$scalability_marker" <<'PY'
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

values = {}
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    key, separator, value = line.partition("=")
    if not separator or not key or key in values:
        raise SystemExit("Invalid scalability acceptance marker")
    values[key] = value
required = {"foundation_version", "image_tag", "evidence_run_id", "accepted_at"}
if set(values) != required or values["foundation_version"] != "1":
    raise SystemExit("Invalid scalability acceptance marker")
if not re.fullmatch(r"[0-9a-f]{40}", values["image_tag"]) or not re.fullmatch(r"[0-9]+", values["evidence_run_id"]):
    raise SystemExit("Invalid scalability acceptance marker")
try:
    accepted = datetime.fromisoformat(values["accepted_at"].replace("Z", "+00:00"))
except ValueError as error:
    raise SystemExit("Invalid scalability acceptance marker") from error
if accepted.tzinfo is None or accepted > datetime.now(UTC) + timedelta(minutes=5):
    raise SystemExit("Invalid scalability acceptance marker")
PY
  elif [[ "$initial_deploy" == true && "$kind" == full && "$first_scalability_approved" == true && "$scalability_run_id" =~ ^[0-9]+$ ]]; then
    first_scalability_release=true
  else
    fail 'Iran deployment requires accepted scalability evidence; initial release needs approved evidence'
  fi
fi
if [[ "$image_source" == preloaded && "$region" == germany ]]; then
  fail 'Preloaded image installation is currently restricted to Iran'
fi

case "$kind" in
  full)
    services=(db redis backend backend-2 food-photo-worker body-analysis-worker notification-worker scheduler frontend caddy)
    image_services=(db redis caddy migrations backend backend-2 food-photo-worker body-analysis-worker notification-worker scheduler frontend)
    ;;
  frontend) services=(frontend); image_services=(frontend) ;;
  backend) services=(backend backend-2); image_services=(migrations backend backend-2) ;;
  agent) services=(agent-service); image_services=(agent-service) ;;
esac

compose() {
  local contract=$1 frontend=$2 api=$3 worker=$4 agent=$5
  shift 5
  COMPOSE_PROJECT_NAME="$project" FITICIAN_ENV_FILE="$env_file" \
    IMAGE_TAG="$image_tag" FRONTEND_IMAGE_TAG="$frontend" \
    BACKEND_API_IMAGE_TAG="$api" WORKER_IMAGE_TAG="$worker" AGENT_IMAGE_TAG="$agent" \
    docker compose -p "$project" --env-file "$env_file" -f "$contract" "$@"
}

volume_keys=(POSTGRES_VOLUME_NAME REDIS_VOLUME_NAME CADDY_DATA_VOLUME_NAME CADDY_CONFIG_VOLUME_NAME)
if [[ "$region" == germany ]]; then volume_keys=(AGENT_HOME_VOLUME_NAME); fi
volume_names=()
for key in "${volume_keys[@]}"; do
  value=$(awk -F= -v key="$key" '$1 == key {value=$2} END {print value}' "$env_file")
  [[ "$value" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || fail "Required persistent volume setting is invalid: $key"
  volume_names+=("$value")
done
expected_volumes=$(IFS=,; printf '%s' "${volume_names[*]}")
if ! compose "$compose_file" "$image_tag" "$image_tag" "$image_tag" "$image_tag" \
  config --format json 2>/dev/null | EXPECTED_REGION="$region" EXPECTED_VOLUMES="$expected_volumes" \
  EXPECTED_ENV_FILE="$env_file" python3 -c '
import json
import os
import sys
from urllib.parse import urlsplit

def reject(message):
    raise SystemExit(message)

values = {}
for line in open(os.environ["EXPECTED_ENV_FILE"], encoding="utf-8"):
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in raw:
        continue
    key, value = raw.split("=", 1)
    values[key] = value.strip().strip("\"\x27")

config = json.load(sys.stdin)
expected = set(os.environ["EXPECTED_VOLUMES"].split(","))
volumes = config.get("volumes", {})
observed = set()
for value in volumes.values():
    name = value.get("name")
    if value.get("external") is not True or name not in expected:
        reject("All regional persistent volumes must be explicitly external and named")
    observed.add(name)
if observed != expected:
    reject("Regional Compose contract is missing an expected external volume")

if os.environ["EXPECTED_REGION"] == "iran":
    services = config.get("services", {})
    database_name = services.get("db", {}).get("environment", {}).get("POSTGRES_DB")
    if not database_name:
        reject("Iran Compose contract must define the local database name")
    for name, service in services.items():
        raw_url = service.get("environment", {}).get("DATABASE_URL")
        if raw_url is None:
            continue
        parsed = urlsplit(raw_url)
        if parsed.hostname != "db" or parsed.port != 5432 or parsed.path.lstrip("/") != database_name:
            reject("Iran application DATABASE_URL must target its local db service")
    if "migrations" not in services or "backend" not in services:
        reject("Iran Compose contract must include migrations and backend services")
else:
    services = config.get("services", {})
    mounts = services.get("agent-service", {}).get("volumes", [])
    auth_mount = next((item for item in mounts if item.get("target") == "/home/agent"), None)
    if auth_mount is None or auth_mount.get("type") != "volume":
        reject("Agent authentication state must use an external named volume")
    auth_source = auth_mount.get("source")
    if volumes.get(auth_source, {}).get("name") != values.get("AGENT_HOME_VOLUME_NAME"):
        reject("Agent authentication state volume name does not match configuration")
'
then
  fail 'Regional Compose safety validation failed'
fi
for volume in "${volume_names[@]}"; do
  docker volume inspect "$volume" >/dev/null 2>&1 || fail 'A required persistent volume does not exist'
done

image_services_csv=$(IFS=,; printf '%s' "${image_services[*]}")
if ! image_refs=$(compose "$compose_file" "$image_tag" "$image_tag" "$image_tag" "$image_tag" \
  config --format json 2>/dev/null | IMAGE_SERVICES="$image_services_csv" python3 -c '
import json
import os
import sys

config = json.load(sys.stdin)
services = config.get("services", {})
images = []
for name in os.environ["IMAGE_SERVICES"].split(","):
    image = services.get(name, {}).get("image")
    tag = image.rsplit(":", 1)[-1] if isinstance(image, str) else ""
    if not isinstance(image, str) or not image:
        raise SystemExit("Candidate image reference is missing or invalid")
    if name not in {"db", "redis", "caddy"} and not __import__("re").fullmatch(r"[0-9a-f]{40}", tag):
        raise SystemExit("Candidate application image must use an immutable Git SHA")
    images.append(image)
print("\n".join(dict.fromkeys(images)))
'); then
  fail 'Candidate Compose images could not be verified'
fi
if [[ "$inspect_only" != true ]]; then
  if [[ "$image_source" == registry ]]; then
    compose "$compose_file" "$image_tag" "$image_tag" "$image_tag" "$image_tag" \
      pull "${image_services[@]}" || fail 'Unable to pull regional immutable images'
  else
    while IFS= read -r image; do
      [[ -n "$image" ]] || continue
      docker image inspect "$image" >/dev/null 2>&1 || fail 'A required preloaded immutable image is missing'
    done <<< "$image_refs"
  fi
fi

service_tag() {
  local service=$1 id image tag
  id=$(compose "$active_contract" "$image_tag" "$image_tag" "$image_tag" "$image_tag" ps -q "$service")
  [[ -n "$id" ]] || fail "Required running service is missing: $service"
  image=$(docker inspect --format '{{.Config.Image}}' "$id")
  tag=${image##*:}
  [[ "$tag" =~ ^[0-9a-f]{40}$ ]] || fail "Running $service image does not use an immutable SHA"
  printf '%s' "$tag"
}

configured_tag() {
  local value
  value=$(awk -F= -v key="$1" '$1 == key {value=$2} END {print value}' "$env_file")
  [[ "$value" =~ ^[0-9a-f]{40}$ ]] || value=$baseline_image_tag
  printf '%s' "$value"
}
baseline_image_tag=$(awk -F= '$1 == "IMAGE_TAG" {value=$2} END {print value}' "$env_file")
if [[ ! "$baseline_image_tag" =~ ^[0-9a-f]{40}$ ]]; then
  [[ "$initial_deploy" == true ]] || fail 'Current full-release IMAGE_TAG is missing or invalid'
  baseline_image_tag=$image_tag
fi
frontend_tag=$(configured_tag FRONTEND_IMAGE_TAG)
api_tag=$(configured_tag BACKEND_API_IMAGE_TAG)
worker_tag=$(configured_tag WORKER_IMAGE_TAG)
agent_tag=$(configured_tag AGENT_IMAGE_TAG)
previous_frontend_tag=$frontend_tag
previous_api_tag=$api_tag
previous_worker_tag=$worker_tag
previous_agent_tag=$agent_tag
legacy_agent_id=''
legacy_agent_restart=''
if [[ "$initial_deploy" == true && "$region" == germany && "$inspect_only" != true ]]; then
  auth_volume=$(awk -F= '$1 == "AGENT_HOME_VOLUME_NAME" {value=$2} END {print value}' "$env_file")
  legacy_ids=$(docker ps -q --filter "volume=$auth_volume")
  [[ -n "$legacy_ids" ]] || fail 'Initial Germany deployment requires an existing Agent using the auth volume'
  for id in $legacy_ids; do
    service=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$id")
    [[ "$service" == agent-service ]] || fail 'Unexpected running container uses the Agent authentication volume'
    [[ -z "$legacy_agent_id" ]] || fail 'Multiple running Agents use the authentication volume'
    legacy_agent_id=$id
    legacy_agent_restart=$(docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$id")
  done
  [[ -n "$legacy_agent_id" ]] || fail 'Existing Agent container was not found for auth-volume adoption'
fi

if [[ "$initial_deploy" == true && "$kind" == full ]]; then
  frontend_tag=$image_tag
  api_tag=$image_tag
  worker_tag=$image_tag
  if [[ "$inspect_only" == true ]]; then printf '%s\n' "$image_tag"; exit 0; fi
elif [[ "$initial_deploy" == true && "$kind" == agent ]]; then
  agent_tag=$image_tag
  if [[ "$inspect_only" == true ]]; then printf '%s\n' "$image_tag"; exit 0; fi
elif [[ "$region" == iran ]]; then
  frontend_tag=$(service_tag frontend)
  api_tag=$(service_tag backend)
  api_tag_2=$(service_tag backend-2)
  worker_tag=$(service_tag scheduler)
  for worker in food-photo-worker body-analysis-worker notification-worker; do
    [[ "$(service_tag "$worker")" == "$worker_tag" ]] || \
      fail "Running worker versions are mixed ($worker); deployment cannot capture a consistent baseline"
  done
  [[ "$api_tag" == "$api_tag_2" ]] || fail 'API replicas have mixed versions; deployment cannot capture a consistent backend'
  previous_frontend_tag=$frontend_tag
  previous_api_tag=$api_tag
  previous_worker_tag=$worker_tag
  case "$kind" in
    full) frontend_tag=$image_tag; api_tag=$image_tag; worker_tag=$image_tag ;;
    frontend) frontend_tag=$image_tag ;;
    backend) api_tag=$image_tag ;;
  esac
  if [[ "$inspect_only" == true ]]; then
    case "$kind" in
      frontend) printf '%s\n' "$previous_frontend_tag" ;;
      backend) printf '%s\n' "$previous_api_tag" ;;
      full) printf '%s\n' "$image_tag" ;;
    esac
    exit 0
  fi
else
  agent_tag=$(service_tag agent-service)
  previous_agent_tag=$agent_tag
  if [[ "$inspect_only" == true ]]; then printf '%s\n' "$agent_tag"; exit 0; fi
  agent_tag=$image_tag
fi
[[ "$inspect_only" == true ]] && exit 0

schema_changed=false
rollback_needed=false
old_env_copy=''
old_marker_copy=''
rollback() {
  local status=$?
  [[ $status -ne 0 ]] || status=1
  trap - ERR INT TERM
  if [[ "$rollback_needed" != true ]]; then exit "$status"; fi
  if [[ -n "$old_env_copy" && -f "$old_env_copy" ]]; then cp -p "$old_env_copy" "$env_file"; fi
  if [[ -n "$old_marker_copy" && -f "$old_marker_copy" ]]; then cp -p "$old_marker_copy" "$active_marker"; fi
  if [[ "$initial_deploy" == true ]]; then rm -f -- "$active_marker"; fi
  if [[ "$first_scalability_release" == true ]]; then rm -f -- "$scalability_marker"; fi
  if [[ "$schema_changed" == true ]]; then
    if ! compose "$compose_file" "$frontend_tag" "$api_tag" "$worker_tag" "$agent_tag" \
      stop caddy frontend backend backend-2 scheduler food-photo-worker body-analysis-worker notification-worker; then
      echo 'Application quiescence failed; block Iran ingress manually before recovery' >&2
    fi
    echo 'Schema changed; manual recovery from the encrypted backup is required' >&2
    exit "$status"
  fi
  echo "Restoring $region deployment with its previous immutable image versions" >&2
  local rollback_status=0
  if [[ "$initial_deploy" == true && "$region" == germany ]]; then
    if ! compose "$compose_file" "$image_tag" "$image_tag" "$image_tag" "$image_tag" \
      stop agent-service >/dev/null 2>&1; then
      echo 'Candidate Agent could not stop; legacy Agent remains stopped to protect authentication state' >&2
      exit "$status"
    fi
    docker update --restart="$legacy_agent_restart" "$legacy_agent_id" >/dev/null 2>&1 || true
    docker start "$legacy_agent_id" >/dev/null 2>&1 || rollback_status=$?
  elif [[ "$initial_deploy" == true ]]; then
    compose "$compose_file" "$image_tag" "$image_tag" "$image_tag" "$image_tag" stop backend backend-2 frontend scheduler food-photo-worker body-analysis-worker notification-worker caddy redis db >/dev/null 2>&1 || true
  elif [[ "$kind" == full ]]; then
    compose "$active_contract" "$previous_frontend_tag" "$previous_api_tag" \
      "$previous_worker_tag" "$previous_agent_tag" up -d --pull never --wait || rollback_status=$?
  else
    compose "$active_contract" "$previous_frontend_tag" "$previous_api_tag" \
      "$previous_worker_tag" "$previous_agent_tag" \
      up -d --pull never --no-deps --wait "${services[@]}" || rollback_status=$?
  fi
  if [[ "$rollback_status" -eq 0 && "$initial_deploy" != true ]]; then
    REGION="$region" DEPLOY_KIND="$kind" IMAGE_TAG="$image_tag" \
      COMPOSE_PROJECT_NAME="$project" FITICIAN_ENV_FILE="$env_file" \
      FRONTEND_IMAGE_TAG="$previous_frontend_tag" BACKEND_API_IMAGE_TAG="$previous_api_tag" \
      WORKER_IMAGE_TAG="$previous_worker_tag" AGENT_IMAGE_TAG="$previous_agent_tag" \
      COMPOSE_FILE="$active_contract" sh "$release_dir/ops/verify-regional.sh" || rollback_status=$?
  fi
  [[ "$rollback_status" -eq 0 ]] || echo 'Regional rollback failed' >&2
  exit "$status"
}
trap rollback ERR INT TERM

services=()
case "$kind" in
  full) services=(db redis backend backend-2 food-photo-worker body-analysis-worker notification-worker scheduler frontend caddy) ;;
  frontend) services=(frontend) ;;
  backend) services=(backend backend-2) ;;
  agent) services=(agent-service) ;;
esac

if [[ "$region" == iran && "$kind" == full ]]; then
  python3 "$release_dir/ops/check-db-connection-budget.py" --replicas 2
  python3 "$release_dir/ops/check-runtime-capacity.py" --region iran --replicas 2 \
    --compose-file "$compose_file" --env-file "$env_file"
  backup_contract=$active_contract
  if [[ "$initial_deploy" == true ]]; then
    rollback_needed=true
    compose "$compose_file" "$image_tag" "$image_tag" "$image_tag" "$image_tag" \
      up -d --pull never --wait db
    user_count=$(compose "$compose_file" "$image_tag" "$image_tag" "$image_tag" "$image_tag" \
      exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM users"')
    [[ "$user_count" =~ ^[1-9][0-9]*$ ]] || fail 'Initial Iran release requires a restored database with existing users'
    backup_contract=$compose_file
  fi
  COMPOSE_FILE="$backup_contract" COMPOSE_PROJECT_NAME="$project" \
    COMPOSE_ENV_FILES="$env_file" FITICIAN_ENV_FILE="$env_file" \
    BACKUP_ENV_FILE="$app_dir/backup.env" bash "$release_dir/backup-production.sh"
  if [[ "$initial_deploy" == true ]]; then active_contract=$compose_file; fi
  current_revision=$(compose "$active_contract" "$previous_frontend_tag" "$previous_api_tag" \
    "$previous_worker_tag" "$previous_agent_tag" exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"')
  target_revision=$(compose "$compose_file" "$image_tag" "$image_tag" "$image_tag" "$image_tag" \
    run --pull never --rm --no-deps migrations alembic heads | awk 'NR == 1 {print $1}')
  [[ -n "$current_revision" && -n "$target_revision" ]] || fail 'Could not verify Alembic revisions'
  if [[ "$current_revision" != "$target_revision" ]]; then
    if [[ "$allow_schema_migrations" != true ]]; then
      fail 'Pending schema migration requires explicit reviewed approval'
    fi
    schema_changed=true
  fi
elif [[ "$region" == iran && "$kind" == backend ]]; then
  current_revision=$(compose "$active_contract" "$previous_frontend_tag" "$previous_api_tag" \
    "$previous_worker_tag" "$previous_agent_tag" exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"')
  target_revision=$(compose "$compose_file" "$previous_frontend_tag" "$image_tag" \
    "$image_tag" "$previous_agent_tag" run --pull never --rm --no-deps migrations alembic heads | \
    awk 'NR == 1 {print $1}')
  [[ -n "$current_revision" && "$current_revision" == "$target_revision" ]] || \
    fail 'Backend component changes schema; use an approved full Iran release'
fi

if [[ "$region" == iran && "$kind" == full && "$schema_changed" == true ]]; then
  rollback_needed=true
  compose "$compose_file" "$image_tag" "$image_tag" "$image_tag" "$previous_agent_tag" \
    run --pull never --rm --no-deps migrations alembic upgrade head
fi

if [[ "$initial_deploy" == true && "$region" == germany ]]; then
  rollback_needed=true
  docker update --restart=no "$legacy_agent_id" >/dev/null
  docker stop "$legacy_agent_id" >/dev/null
fi
if [[ "$kind" == full ]]; then
  rollback_needed=true
  if ! compose "$compose_file" "$frontend_tag" "$api_tag" "$worker_tag" "$agent_tag" up -d --pull never --wait; then
    rollback || true
    exit 1
  fi
else
  rollback_needed=true
  if ! compose "$compose_file" "$frontend_tag" "$api_tag" "$worker_tag" "$agent_tag" \
    up -d --pull never --no-deps --wait "${services[@]}"; then
    rollback || true
    exit 1
  fi
fi

if ! REGION="$region" DEPLOY_KIND="$kind" IMAGE_TAG="$image_tag" \
  COMPOSE_PROJECT_NAME="$project" FITICIAN_ENV_FILE="$env_file" \
  FRONTEND_IMAGE_TAG="$frontend_tag" BACKEND_API_IMAGE_TAG="$api_tag" \
  WORKER_IMAGE_TAG="$worker_tag" AGENT_IMAGE_TAG="$agent_tag" \
  COMPOSE_FILE="$compose_file" sh "$release_dir/ops/verify-regional.sh"; then
  rollback || true
  exit 1
fi

umask 077
old_env_copy=$(mktemp "$app_dir/.env.regional-old.XXXXXXXX")
cp -p "$env_file" "$old_env_copy"
if [[ -f "$active_marker" ]]; then
  old_marker_copy=$(mktemp "$app_dir/.regional-$region-marker-old.XXXXXXXX")
  cp -p "$active_marker" "$old_marker_copy"
fi
next_env=$(mktemp "$app_dir/.env.regional.XXXXXXXX")
case "$kind" in full) next_baseline=$image_tag ;; *) next_baseline=$baseline_image_tag ;; esac
awk -v baseline="$next_baseline" -v frontend="$frontend_tag" -v api="$api_tag" \
  -v worker="$worker_tag" -v agent="$agent_tag" '
  /^(IMAGE_TAG|FRONTEND_IMAGE_TAG|BACKEND_API_IMAGE_TAG|WORKER_IMAGE_TAG|AGENT_IMAGE_TAG)=/ {next}
  {print}
  END {
    print "IMAGE_TAG=" baseline
    print "FRONTEND_IMAGE_TAG=" frontend
    print "BACKEND_API_IMAGE_TAG=" api
    print "WORKER_IMAGE_TAG=" worker
    print "AGENT_IMAGE_TAG=" agent
  }
' "$env_file" > "$next_env"
chmod 600 "$next_env"
next_marker=$(mktemp "$app_dir/.regional-$region-active-contract.XXXXXXXX")
printf '%s\n' "$compose_file" > "$next_marker"
chmod 600 "$next_marker"
if [[ "$first_scalability_release" == true ]]; then
  next_scalability_marker=$(mktemp "$app_dir/.scalability-foundation-accepted.XXXXXXXX")
  printf 'foundation_version=1\nimage_tag=%s\nevidence_run_id=%s\naccepted_at=%s\n' \
    "$image_tag" "$scalability_run_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$next_scalability_marker"
  chmod 600 "$next_scalability_marker"
fi
mv "$next_env" "$env_file"
mv "$next_marker" "$active_marker"
if [[ "$first_scalability_release" == true ]]; then mv "$next_scalability_marker" "$scalability_marker"; fi
trap - ERR INT TERM
rm -f -- "$old_env_copy" "$old_marker_copy"
echo "Verified $region $kind deployment for immutable image $image_tag"
