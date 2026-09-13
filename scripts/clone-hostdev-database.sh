#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$project_root/compose.host-backend.yaml"
destination_project="fitician-hostdev"
destination_service="hostdev-db"

cd "$project_root"

if ! docker compose ps --status running --services | grep -Fxq "db"; then
  echo "The current Fitician database service is not running." >&2
  exit 1
fi

docker compose -p "$destination_project" -f "$compose_file" up -d "$destination_service"

destination_container="$(
  docker compose -p "$destination_project" -f "$compose_file" ps -q "$destination_service"
)"
if [[ -z "$destination_container" ]]; then
  echo "The dedicated hostdev database container was not created." >&2
  exit 1
fi

actual_project="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$destination_container")"
actual_service="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.service" }}' "$destination_container")"
if [[ "$actual_project" != "$destination_project" || "$actual_service" != "$destination_service" ]]; then
  echo "Refusing to replace a database outside the dedicated hostdev project." >&2
  exit 1
fi

for _attempt in $(seq 1 60); do
  health="$(docker inspect -f '{{ .State.Health.Status }}' "$destination_container")"
  [[ "$health" == "healthy" ]] && break
  sleep 1
done
if [[ "${health:-}" != "healthy" ]]; then
  echo "The dedicated hostdev database did not become healthy." >&2
  exit 1
fi

docker compose -p "$destination_project" -f "$compose_file" exec -T "$destination_service" \
  psql -v ON_ERROR_STOP=1 -U fitician -d postgres \
  -c 'DROP DATABASE IF EXISTS fitician WITH (FORCE)' \
  -c 'CREATE DATABASE fitician OWNER fitician'

docker compose exec -T db pg_dump -U fitician -d fitician --no-owner --no-privileges \
  | docker compose -p "$destination_project" -f "$compose_file" exec -T \
    "$destination_service" psql -v ON_ERROR_STOP=1 -U fitician -d fitician

echo "Hostdev database clone completed on port 5433."
