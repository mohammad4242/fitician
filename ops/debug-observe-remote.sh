#!/usr/bin/env bash
# Trusted Actions control path; model inputs never become remote commands.
set -euo pipefail
: "${VPS_HOST:?}" "${VPS_USER:?}" "${VPS_SSH_PRIVATE_KEY:?}" "${VPS_KNOWN_HOSTS:?}" "${OBSERVATION_TARGET:?}"
port=${VPS_SSH_PORT:-9011}
trace=${OBSERVATION_TRACE_ID:-}
[[ "$OBSERVATION_TARGET" == iran || "$OBSERVATION_TARGET" == germany ]]
[[ -z "$trace" || "$trace" =~ ^[a-f0-9]{32}$ ]]
[[ "$VPS_HOST" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ && "$VPS_USER" =~ ^[A-Za-z0-9._-]+$ ]]
[[ "$port" =~ ^[0-9]{1,5}$ ]] && ((10#$port >= 1 && 10#$port <= 65535))
workspace=${GITHUB_WORKSPACE:-$PWD}
umask 077
private=$(mktemp -d "$workspace/.debug-observation.XXXXXXXX")
trap 'rm -rf -- "$private"' EXIT
printf '%s\n' "$VPS_SSH_PRIVATE_KEY" > "$private/identity"
printf '%s\n' "$VPS_KNOWN_HOSTS" > "$private/known_hosts"
unset VPS_SSH_PRIVATE_KEY VPS_KNOWN_HOSTS
ssh-keygen -F "[$VPS_HOST]:$port" -f "$private/known_hosts" >/dev/null
mkdir -p .ci-evidence/debug-observation
args=(--target "$OBSERVATION_TARGET")
if [[ -n "$trace" ]]; then args+=(--trace-id "$trace"); fi
timeout 220 ssh -T -i "$private/identity" -p "$port" \
  -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$private/known_hosts" -o ConnectTimeout=15 \
  -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -o ClearAllForwardings=yes \
  -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
  "$VPS_USER@$VPS_HOST" python3 - "${args[@]}" \
  < ops/debug-server-observation.py > .ci-evidence/debug-observation/observation.json
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path('.ci-evidence/debug-observation/observation.json')
assert 0<p.stat().st_size<=28000
v=json.loads(p.read_text());assert v['schema_version']==1 and v['target_environment']=='production-'+os.environ['OBSERVATION_TARGET'] and v['provenance']=='fixed_read_only_host_collector' and v['business_outcome_verified'] is False
print('Bounded sanitized host observations captured; business resolution remains unverified')
PY
