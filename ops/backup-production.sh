#!/usr/bin/env bash
set -euo pipefail

compose_file=${COMPOSE_FILE:-/opt/fitician/compose.prod.yaml}
app_dir=$(dirname "$compose_file")
backup_env_file=${BACKUP_ENV_FILE:-"$app_dir/backup.env"}
if [ -z "${DB_BACKUP_BUCKET:-}" ] && [ -f "$backup_env_file" ]; then
  set -a
  # The operator owns this file; deployment never copies it from Git.
  . "$backup_env_file"
  set +a
fi
: "${DB_BACKUP_BUCKET:?DB_BACKUP_BUCKET is required}"
: "${DB_BACKUP_AGE_RECIPIENT:?DB_BACKUP_AGE_RECIPIENT is required}"
: "${S3_ENDPOINT:?S3_ENDPOINT is required}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required}"
: "${AWS_DEFAULT_REGION:?AWS_DEFAULT_REGION is required}"

for command in docker age aws stat; do
  command -v "$command" >/dev/null || { echo "$command is required" >&2; exit 1; }
done

umask 077
encrypted=$(mktemp "$app_dir/.db-backup.XXXXXXXX.age")
trap 'rm -f "$encrypted"' EXIT

docker compose -f "$compose_file" exec -T db sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl' \
  | age -r "$DB_BACKUP_AGE_RECIPIENT" > "$encrypted"

local_bytes=$(stat -c %s "$encrypted")
if [ "$local_bytes" -eq 0 ]; then
  echo "Encrypted database backup is empty" >&2
  exit 1
fi

timestamp=$(date -u +%Y%m%dT%H%M%S%NZ)
key="postgres/$(date -u +%Y/%m/%d)/fitician-${timestamp}.dump.age"
aws --endpoint-url "$S3_ENDPOINT" s3 cp "$encrypted" "s3://$DB_BACKUP_BUCKET/$key" --only-show-errors
remote_bytes=$(aws --endpoint-url "$S3_ENDPOINT" s3api head-object \
  --bucket "$DB_BACKUP_BUCKET" --key "$key" --query ContentLength --output text)
if [ "$remote_bytes" != "$local_bytes" ]; then
  echo "Uploaded backup size does not match" >&2
  exit 1
fi

printf 'Encrypted database backup verified: s3://%s/%s (%s bytes)\n' \
  "$DB_BACKUP_BUCKET" "$key" "$local_bytes"
