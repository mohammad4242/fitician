#!/usr/bin/env bash
set -euo pipefail

host=${VPS_HOST:-}
user=${VPS_USER:-}
app_dir=${VPS_APP_DIR:-}
port=${VPS_SSH_PORT:-9011}
private_key=${VPS_SSH_PRIVATE_KEY:-}
known_hosts=${VPS_KNOWN_HOSTS:-}
workspace=${GITHUB_WORKSPACE:-$PWD}

blocked() {
  printf 'ssh=blocked class=%s\n' "$1"
  exit 1
}

[[ "$host" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]] || blocked settings
[[ "$user" =~ ^[A-Za-z0-9._-]+$ ]] || blocked settings
[[ "$app_dir" =~ ^/[A-Za-z0-9._/-]+$ && "$app_dir" != *'/../'* && "$app_dir" != */.. ]] || \
  blocked settings
[[ "$port" =~ ^[0-9]{1,5}$ ]] || blocked settings
port=$((10#$port))
((port >= 1 && port <= 65535)) || blocked settings
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

if ! agent_output=$(ssh-agent -s 2>/dev/null) || ! eval "$agent_output" >/dev/null; then
  blocked key
fi
agent_started=true
if ! SSH_ASKPASS_REQUIRE=never DISPLAY='' ssh-add -q "$key_file" >/dev/null 2>&1; then
  blocked key
fi

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
  -o LogLevel=ERROR \
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
  :
else
  case "$remote_output" in
    *'Host key verification failed'*|*'REMOTE HOST IDENTIFICATION HAS CHANGED'*|*'host key is known'*)
      blocked host_key
      ;;
    *'Permission denied'*|*'Too many authentication failures'*|*'No supported authentication methods available'*|*'sign_and_send_pubkey'*)
      blocked authentication
      ;;
    *'Connection timed out'*|*'Connection refused'*|*'Connection reset by peer'*|*'Connection closed by'*|*'No route to host'*|*'Network is unreachable'*|*'Could not resolve hostname'*|*'Operation timed out'*)
      blocked network
      ;;
    *) blocked ssh_client ;;
  esac
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
printf 'ssh=connected\nremote_uid=%s\napp_dir_readable=%s\napp_dir_writable=%s\ndocker_access=%s\n' \
  "$remote_uid" "$readable" "$writable" "$docker_access"
if [[ "$readable" != yes || "$writable" != yes || "$docker_access" != available ]]; then
  blocked remote_capabilities
fi
