#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

project="fitician-split-test-${UID:-user}-$$"
run_dir="$repo_root/.codex-tmp/iran-germany/$project"
env_file="$run_dir/compose.env"
mkdir -p "$run_dir/pytest-tmp"
token="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
umask 077
printf 'SPLIT_TEST_TOKEN=%s\n' "$token" > "$env_file"
chmod 0600 "$env_file"
unset token

export SPLIT_TEST_PYTEST_DIR="$run_dir/pytest-tmp"
compose=(docker compose --progress quiet --project-name "$project" --env-file "$env_file" -f compose.split-test.yaml)

cleanup() {
  "${compose[@]}" down --remove-orphans >/dev/null 2>&1 || true
  rm -f "$env_file"
}
trap cleanup EXIT INT TERM

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required."
  exit 2
fi

uv sync --directory backend --extra dev --locked
echo "Starting isolated split-region project: $project"
"${compose[@]}" up --build --detach --wait iran-db iran-redis iran-backend iran-backend-2
echo "Backend replicas are ready before the Agent ingress exists."
"${compose[@]}" up --detach --wait split-agent split-gateway

echo "Running focused Backend provider and queue regressions against this project's Postgres."
test_database_url="postgresql+psycopg://fitician:fitician@iran-db:5432/fitician_test"
"${compose[@]}" exec --no-TTY \
  -e TEST_DATABASE_URL="$test_database_url" \
  -e DATABASE_URL="$test_database_url" \
  -e NUTRITION_AUDIT_DATABASE_URL="postgresql+psycopg://fitician:fitician@iran-db:5432/fitician_nutrition_audit" \
  -e APP_ENV=test \
  -e PYTHONPATH=/app:/testdeps \
  -w /app iran-backend python -m pytest \
  /app/tests/ai/test_remote_agent_topology.py \
  /app/tests/ai/test_agent_service_provider.py \
  /app/tests/ai/test_agent_service_admin_contract.py \
  /app/tests/admin/test_agent_service_auth_api.py \
  /app/tests/admin/test_agent_service_proxy_api.py \
  /app/tests/body_analysis/test_worker.py \
  /app/tests/nutrition/test_food_photo_queue.py -q \
  --basetemp=/split-pytest/run

echo "Probing real Agent HTTP with fake runner and no production authentication."
connected_output="$("${compose[@]}" exec --no-TTY iran-backend python /ops/split_test_probe.py connected)"
printf '%s\n' "$connected_output"
workspace_image="$(printf '%s\n' "$connected_output" | sed -n 's/^WORKSPACE_IMAGE=//p')"
if [[ "$workspace_image" != /tmp/fitician-agent/* ]]; then
  echo "Agent workspace image path was missing or outside the isolated workspace."
  exit 1
fi
"${compose[@]}" exec --no-TTY split-agent \
  python /opt/split-test/codex workspace-cleanup "$workspace_image"

echo "Stopping only this project's Agent container and checking both Backend replicas."
"${compose[@]}" stop split-agent
"${compose[@]}" exec --no-TTY iran-backend python /ops/split_test_probe.py disconnected
echo "Restarting the Agent and repeating the authenticated multipart request."
"${compose[@]}" up --detach --wait split-agent
recovered_output="$("${compose[@]}" exec --no-TTY iran-backend python /ops/split_test_probe.py connected)"
printf '%s\n' "$recovered_output"
recovered_workspace_image="$(printf '%s\n' "$recovered_output" | sed -n 's/^WORKSPACE_IMAGE=//p')"
if [[ "$recovered_workspace_image" != /tmp/fitician-agent/* ]]; then
  echo "Recovered Agent workspace image path was missing or outside the isolated workspace."
  exit 1
fi
"${compose[@]}" exec --no-TTY split-agent \
  python /opt/split-test/codex workspace-cleanup "$recovered_workspace_image"

echo "SIMULATION PASSED: $project"
echo "Project-named database and Agent-home volumes are retained; reruns use a new project name."
