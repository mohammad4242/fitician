#!/bin/sh

set -eu

heartbeat_path=${JOB_HEARTBEAT_PATH:-/run/fitician/heartbeat.json}
expected_service=${JOB_HEARTBEAT_SERVICE:-}
max_age_seconds=${JOB_HEARTBEAT_MAX_AGE_SECONDS:-20}

case "$max_age_seconds" in
  ''|*[!0-9]*) exit 2 ;;
esac
[ -n "$expected_service" ] || exit 2
[ -f "$heartbeat_path" ] || exit 1

now=$(date +%s)
modified=$(stat -c %Y -- "$heartbeat_path")
age=$((now - modified))
[ "$age" -ge 0 ] && [ "$age" -le "$max_age_seconds" ] || exit 1

recorded_pid=$(sed -n 's/.*"pid"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$heartbeat_path")
recorded_service=$(sed -n 's/.*"service"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$heartbeat_path")
[ "$recorded_service" = "$expected_service" ] || exit 1
[ -n "$recorded_pid" ] || exit 1
kill -0 "$recorded_pid"
