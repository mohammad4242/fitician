#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

host=${VPS_HOST:-}
user=${VPS_USER:-}
app_dir=${VPS_APP_DIR:-}
port=${VPS_SSH_PORT:-9011}
private_key=${VPS_SSH_PRIVATE_KEY:-}
known_hosts=${VPS_KNOWN_HOSTS:-}
expected_host_sha256=${EXPECTED_HOST_SHA256:-}
workspace=${GITHUB_WORKSPACE:-$PWD}
client_key_loaded=no
client_key_fingerprint_sha256=not_available
target_host_matches_expected=not_provided
pinned_host_entry_present=no
host_key_verified=no
key_offered=no
authentication_accepted=no

report_proofs() {
  printf 'client_key_loaded=%s\nclient_key_fingerprint_sha256=%s\ntarget_host_matches_expected=%s\npinned_host_entry_present=%s\nhost_key_verified=%s\nkey_offered=%s\nauthentication_accepted=%s\n' \
    "$client_key_loaded" "$client_key_fingerprint_sha256" "$target_host_matches_expected" \
    "$pinned_host_entry_present" "$host_key_verified" "$key_offered" \
    "$authentication_accepted"
}

blocked() {
  report_proofs
  printf 'ssh=blocked class=%s\n' "$1"
  if [[ -n "${2:-}" ]]; then printf 'auth_detail=%s\n' "$2"; fi
  exit 1
}

[[ "$host" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]] || blocked settings
[[ "$user" =~ ^[A-Za-z0-9._-]+$ ]] || blocked settings
[[ "$app_dir" =~ ^/[A-Za-z0-9._/-]+$ && "$app_dir" != *'/../'* && "$app_dir" != */.. ]] || \
  blocked settings
[[ "$port" =~ ^[0-9]{1,5}$ ]] || blocked settings
port=$((10#$port))
((port >= 1 && port <= 65535)) || blocked settings
if [[ -n "$expected_host_sha256" ]]; then
  [[ "$expected_host_sha256" =~ ^[A-Fa-f0-9]{64}$ ]] || blocked settings
  expected_host_sha256=${expected_host_sha256,,}
  actual_host_sha256=$(printf '%s' "$host" | sha256sum | awk '{print $1}')
  if [[ "$actual_host_sha256" != "$expected_host_sha256" ]]; then
    target_host_matches_expected=no
    blocked target_mismatch
  fi
  target_host_matches_expected=yes
fi
[[ -n "$private_key" ]] || blocked key
[[ -n "$known_hosts" ]] || blocked host_key

temp_dir=$(mktemp -d "$workspace/.regional-ssh-diagnostic.XXXXXXXX")
chmod 700 "$temp_dir"
key_file="$temp_dir/identity"
known_hosts_file="$temp_dir/known_hosts"
agent_started=false
cleanup() {
  if [[ "$agent_started" == true && -n "${SSH_AGENT_PID:-}" ]]; then
    ssh-agent -k >/dev/null 2>&1 || true
  fi
  rm -rf -- "$temp_dir"
}
trap cleanup EXIT

umask 077
printf '%s\n' "$private_key" > "$key_file"
printf '%s\n' "$known_hosts" > "$known_hosts_file"
chmod 600 "$key_file" "$known_hosts_file"
unset VPS_SSH_PRIVATE_KEY VPS_KNOWN_HOSTS private_key known_hosts

if ! ssh-keygen -F "[$host]:$port" -f "$known_hosts_file" >/dev/null 2>&1; then
  blocked host_key
fi
pinned_host_entry_present=yes

if ! agent_output=$(ssh-agent -s 2>/dev/null) || ! eval "$agent_output" >/dev/null; then
  blocked key
fi
agent_started=true
if ! SSH_ASKPASS_REQUIRE=never DISPLAY='' ssh-add -q "$key_file" >/dev/null 2>&1; then
  blocked key
fi
client_key_loaded=yes
fingerprint_token=$(ssh-keygen -lf "$key_file" -E sha256 2>/dev/null | awk '{print $2}') || blocked key
[[ "$fingerprint_token" =~ ^SHA256:[A-Za-z0-9+/=]+$ ]] || blocked key
client_key_fingerprint_sha256=$(printf '%s' "$fingerprint_token" | sha256sum | awk '{print $1}')
unset fingerprint_token

printf -v remote_command 'sh -s -- %q' "$app_dir"
if remote_output=$(ssh \
  -p "$port" \
  -i "$key_file" \
  -o BatchMode=yes \
  -o IdentitiesOnly=yes \
  -o "IdentityAgent=$SSH_AUTH_SOCK" \
  -o StrictHostKeyChecking=yes \
  -o "UserKnownHostsFile=$known_hosts_file" \
  -o GlobalKnownHostsFile=/dev/null \
  -o ConnectTimeout=8 \
  -o ConnectionAttempts=1 \
  -o ServerAliveInterval=3 \
  -o ServerAliveCountMax=2 \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no \
  -o KbdInteractiveAuthentication=no \
  -o ClearAllForwardings=yes \
  -o RequestTTY=no \
  -o LogLevel=DEBUG1 \
  "$user@$host" "$remote_command" 2>&1 <<'REMOTE_CHECKS'
set -eu
app_dir=$1
remote_uid=$(id -u 2>/dev/null || printf unknown)
case "$remote_uid" in *[!0-9]*|'') remote_uid=unknown ;; esac
readable=no
writable=no
if [ -d "$app_dir" ] && [ -r "$app_dir" ] && [ -x "$app_dir" ]; then readable=yes; fi
if [ -d "$app_dir" ] && [ -w "$app_dir" ]; then writable=yes; fi
docker_access=missing
if command -v docker >/dev/null 2>&1; then
  docker_access=unavailable
  if command -v timeout >/dev/null 2>&1 && timeout 8 docker info --format '{{.ServerVersion}}' >/dev/null 2>&1; then
    docker_access=available
  fi
fi
printf 'remote_uid=%s\napp_dir_readable=%s\napp_dir_writable=%s\ndocker_access=%s\n' \
  "$remote_uid" "$readable" "$writable" "$docker_access"
REMOTE_CHECKS
); then
  remote_output=${remote_output//$'\r'/}
else
  remote_output=${remote_output//$'\r'/}
  if printf '%s\n' "$remote_output" | grep -E \
    "^debug1: Host '.*' is known and matches the [A-Za-z0-9_-]+ host key\\.$" >/dev/null; then
    host_key_verified=yes
  fi
  if printf '%s\n' "$remote_output" | grep -E \
    '^debug1: Offering public key: .+ SHA256:[A-Za-z0-9+/=]+.*$' >/dev/null; then
    key_offered=yes
  fi
  if printf '%s\n' "$remote_output" | grep -E \
    '^Authenticated to .+ using "publickey"\.$' >/dev/null; then
    authentication_accepted=yes
  fi
  failure_class=ssh_client
  auth_detail=none
  case "$remote_output" in
    *'Host key verification failed'*|*'REMOTE HOST IDENTIFICATION HAS CHANGED'*|*'host key is known'*)
      failure_class=host_key
      ;;
    *'Connection timed out'*|*'Connection refused'*|*'Connection reset by peer'*|*'Connection closed by'*|*'No route to host'*|*'Network is unreachable'*|*'Could not resolve hostname'*|*'Operation timed out'*)
      failure_class=network
      ;;
    *'Too many authentication failures'*)
      failure_class=authentication
      auth_detail=too_many_authentication_failures
      ;;
    *'sign_and_send_pubkey: signing failed'*|*'agent refused operation'*)
      failure_class=key
      auth_detail=agent_signing_failed
      ;;
    *'Permission denied'*|*'No supported authentication methods available'*)
      failure_class=authentication
      if [[ "$key_offered" == yes && "$authentication_accepted" == no ]]; then
        auth_detail=publickey_rejected
      fi
      ;;
  esac
  blocked "$failure_class" "$auth_detail"
fi

if printf '%s\n' "$remote_output" | grep -E \
  "^debug1: Host '.*' is known and matches the [A-Za-z0-9_-]+ host key\\.$" >/dev/null; then
  host_key_verified=yes
fi
if printf '%s\n' "$remote_output" | grep -E \
  '^debug1: Offering public key: .+ SHA256:[A-Za-z0-9+/=]+.*$' >/dev/null; then
  key_offered=yes
fi
if printf '%s\n' "$remote_output" | grep -E \
  '^Authenticated to .+ using "publickey"\.$' >/dev/null; then
  authentication_accepted=yes
fi

remote_uid=$(printf '%s\n' "$remote_output" | sed -n 's/^remote_uid=//p')
readable=$(printf '%s\n' "$remote_output" | sed -n 's/^app_dir_readable=//p')
writable=$(printf '%s\n' "$remote_output" | sed -n 's/^app_dir_writable=//p')
docker_access=$(printf '%s\n' "$remote_output" | sed -n 's/^docker_access=//p')
[[ "$remote_uid" =~ ^[0-9]+$|^unknown$ ]] || blocked remote_report
[[ "$readable" == yes || "$readable" == no ]] || blocked remote_report
[[ "$writable" == yes || "$writable" == no ]] || blocked remote_report
[[ "$docker_access" == available || "$docker_access" == unavailable || "$docker_access" == missing ]] || \
  blocked remote_report
printf 'ssh=connected\n'
report_proofs
printf 'remote_uid=%s\napp_dir_readable=%s\napp_dir_writable=%s\ndocker_access=%s\n' \
  "$remote_uid" "$readable" "$writable" "$docker_access"
if [[ "$readable" != yes || "$writable" != yes || "$docker_access" != available ]]; then
  blocked remote_capabilities
fi
