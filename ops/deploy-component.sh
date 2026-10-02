#!/usr/bin/env bash
# Only API replicas or frontend. Never run migrations or recreate dependencies.
set -Eeuo pipefail
app_dir=${VPS_APP_DIR:?VPS_APP_DIR required}
component=${COMPONENT:?COMPONENT required}
image_tag=${IMAGE_TAG:?IMAGE_TAG required}
expected_current=${EXPECTED_CURRENT_TAG:-}
registry=${DOCKERHUB_USERNAME:-}
cd "$app_dir"
case "$component" in
  frontend) services=(frontend); tag_variable=FRONTEND_IMAGE_TAG ;;
  backend) services=(backend backend-2); tag_variable=BACKEND_API_IMAGE_TAG ;;
  *) echo 'Unsupported component' >&2; exit 1 ;;
esac
valid_tag() { [[ "$1" =~ ^[0-9a-f]{40}$ ]]; }
valid_tag "$image_tag"
test -s .env
test -f .scalability-foundation-accepted
python3 - .scalability-foundation-accepted <<'PY'
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
lines = Path(sys.argv[1]).read_text().splitlines()
values = dict(line.split("=", 1) for line in lines)
required = {"foundation_version", "image_tag", "evidence_run_id", "accepted_at"}
if len(values) != len(lines) or set(values) != required:
    raise SystemExit("Invalid scalability acceptance marker")
if (values["foundation_version"] != "1" or
        not re.fullmatch(r"[0-9a-f]{40}", values["image_tag"]) or
        not re.fullmatch(r"[0-9]+", values["evidence_run_id"])):
    raise SystemExit("Invalid scalability acceptance marker")
accepted = datetime.fromisoformat(values["accepted_at"].replace("Z", "+00:00"))
if accepted.tzinfo is None or accepted > datetime.now(UTC) + timedelta(minutes=5):
    raise SystemExit("Invalid scalability acceptance marker")
PY
compose() {
  local tag=$1
  shift
  env "$tag_variable=$tag" docker compose -f compose.prod.yaml "$@"
}
current_tag=''
for service in "${services[@]}"; do
  id=$(docker compose -f compose.prod.yaml ps -q "$service")
  test -n "$id"
  image=$(docker inspect --format '{{.Config.Image}}' "$id")
  tag=${image##*:}
  valid_tag "$tag"
  case "$image" in */fitician-"$component":"$tag") ;; *) echo 'Unexpected running image' >&2; exit 1 ;; esac
  if [ -n "$current_tag" ] && [ "$current_tag" != "$tag" ]; then
    echo 'API replicas have different versions; full release required' >&2
    exit 1
  fi
  current_tag=$tag
  if [ -z "$registry" ]; then registry=${image%/fitician-*}; fi
  test "$image" = "$registry/fitician-$component:$tag"
done
if [ "${INSPECT_ONLY:-false}" = true ]; then
  printf '%s\n' "$current_tag"
  exit 0
fi
test -n "$expected_current"
test "$current_tag" = "$expected_current"
if [ -n "${PREVIOUS_IMAGE_TAG:-}" ]; then test "$PREVIOUS_IMAGE_TAG" = "$current_tag"; fi
if [ "$image_tag" = "$current_tag" ]; then echo 'Component already at requested SHA'; exit 0; fi

unrelated_state() {
  local id service
  local ids
  ids=$(docker compose -f compose.prod.yaml ps -aq) || return
  for id in $ids; do
    service=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$id") || return
    if [[ " ${services[*]} " != *" $service "* ]]; then
      docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}:{{.Id}}:{{.RestartCount}}:{{.State.StartedAt}}' "$id" || return
    fi
  done | sort
}
before_state=$(unrelated_state)
compose "$image_tag" pull "${services[@]}"
if [ "$component" = backend ]; then
  current_revision=$(docker compose -f compose.prod.yaml exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"')
  target_revision=$(docker run --rm --network none --entrypoint alembic \
    "$registry/fitician-backend:$image_tag" heads | awk 'NR == 1 {print $1}')
  test -n "$current_revision"
  if [ "$current_revision" != "$target_revision" ]; then
    echo 'Pending schema change; full release required' >&2
    exit 1
  fi
fi
rollback() {
  local status=$?
  if [ "$status" -eq 0 ]; then status=1; fi
  trap - ERR INT TERM
  set +e
  if [ -n "${next_env:-}" ]; then rm -f -- "$next_env"; fi
  echo "Restoring $component to $current_tag" >&2
  compose "$current_tag" pull "${services[@]}" && \
    compose "$current_tag" up -d --no-deps --wait --wait-timeout 180 "${services[@]}"
  local rollback_status=$?
  if [ "$rollback_status" -ne 0 ]; then echo 'Component rollback FAILED' >&2; fi
  exit "$status"
}
trap rollback ERR INT TERM
compose "$image_tag" up -d --no-deps --wait --wait-timeout 180 "${services[@]}"
for service in "${services[@]}"; do
  id=$(compose "$image_tag" ps -q "$service")
  test -n "$id"
  test "$(docker inspect --format '{{.State.Health.Status}}' "$id")" = healthy
  test "$(docker inspect --format '{{.Config.Image}}' "$id")" = "$registry/fitician-$component:$image_tag"
done
# Check the real HTTPS ingress after container readiness; bounded curl retries.
curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 2 \
  --connect-timeout 5 --max-time 15 https://fitician.fit/healthz >/dev/null
if [ "$component" = frontend ]; then
  html=$(curl --fail --silent --show-error --location --connect-timeout 5 --max-time 20 \
    -H 'Cache-Control: no-cache' https://fitician.fit/)
  count=$(printf '%s' "$html" | grep -F -o '<meta name="enamad" content="74257848" />' | wc -l | tr -d ' ')
  test "$count" = 1
else
  curl --fail --silent --show-error --connect-timeout 5 --max-time 15 \
    https://fitician.fit/api/v1/products >/dev/null
  for service in "${services[@]}"; do
    compose "$image_tag" exec -T "$service" python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=5).read()" >/dev/null
  done
fi
after_state=$(unrelated_state)
if [ "$before_state" != "$after_state" ]; then
  echo 'Unrelated container ID, restart count, or start time changed' >&2
  false
fi
# Atomic persistence happens only after all health and isolation checks succeed.
next_env=$(mktemp "$app_dir/.env.component.XXXXXXXX")
chmod --reference=.env "$next_env"
awk -v key="$tag_variable" -v tag="$image_tag" '
  index($0, key "=") == 1 { print key "=" tag; found=1; next }
  { print }
  END { if (!found) print key "=" tag }
' .env > "$next_env"
mv "$next_env" .env
trap - ERR INT TERM
printf '%s released at %s; unrelated services unchanged\n' "$component" "$image_tag"
