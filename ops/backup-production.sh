#!/usr/bin/env bash
set -euo pipefail

compose_file=${COMPOSE_FILE:-/opt/fitician/compose.prod.yaml}
app_dir=$(dirname "$compose_file")
compose_project=${COMPOSE_PROJECT_NAME:-fitician}
backup_env_file=${BACKUP_ENV_FILE:-"$app_dir/backup.env"}
if [ -z "${DB_BACKUP_BUCKET:-}" ] && [ -f "$backup_env_file" ]; then
  set -a
  # The operator owns this file; deployment never copies it from Git.
  # shellcheck source=/dev/null
  . "$backup_env_file"
  set +a
fi
: "${DB_BACKUP_BUCKET:?DB_BACKUP_BUCKET is required}"
: "${DB_BACKUP_AGE_RECIPIENT:?DB_BACKUP_AGE_RECIPIENT is required}"
: "${S3_ENDPOINT:?S3_ENDPOINT is required}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required}"
: "${AWS_DEFAULT_REGION:?AWS_DEFAULT_REGION is required}"

for command in docker age aws stat sha256sum cut python3; do
  command -v "$command" >/dev/null || { echo "$command is required" >&2; exit 1; }
done

umask 077
encrypted=$(mktemp "$app_dir/.db-backup.XXXXXXXX.age")
downloaded=$(mktemp "$app_dir/.db-backup-check.XXXXXXXX.age")
snapshot_metadata=$(mktemp "$app_dir/.db-snapshot.XXXXXXXX.json")
encrypted_metadata=$(mktemp "$app_dir/.db-snapshot.XXXXXXXX.json.age")
downloaded_metadata=$(mktemp "$app_dir/.db-snapshot-check.XXXXXXXX.json.age")
trap 'rm -f "$encrypted" "$downloaded" "$snapshot_metadata" "$encrypted_metadata" "$downloaded_metadata"' EXIT

if [ "${FINAL_SYNC:-0}" = "1" ]; then
  : "${FINAL_FREEZE_MANIFEST:?FINAL_FREEZE_MANIFEST is required for final sync}"
  python3 "$app_dir/ops/final-database-snapshot.py" \
    --execute \
    --confirm-source mohammad@141.11.0.99 \
    --freeze-manifest "$FINAL_FREEZE_MANIFEST" \
    --compose-file "$compose_file" \
    --project-name "$compose_project" \
    --encrypted-output "$encrypted" \
    --metadata-output "$snapshot_metadata"
  age -r "$DB_BACKUP_AGE_RECIPIENT" < "$snapshot_metadata" > "$encrypted_metadata"
else
  docker compose --project-name "$compose_project" --project-directory "$app_dir" \
    -f "$compose_file" exec -T db sh -c \
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl' \
    | age -r "$DB_BACKUP_AGE_RECIPIENT" > "$encrypted"
fi

local_bytes=$(stat -c %s "$encrypted")
if [ "$local_bytes" -eq 0 ]; then
  echo "Encrypted database backup is empty" >&2
  exit 1
fi

timestamp=$(date -u +%Y%m%dT%H%M%S%NZ)
date_path=${timestamp:0:4}/${timestamp:4:2}/${timestamp:6:2}
key="postgres/${date_path}/fitician-${timestamp}.dump.age"
aws --endpoint-url "$S3_ENDPOINT" s3 cp "$encrypted" "s3://$DB_BACKUP_BUCKET/$key" --only-show-errors
remote_bytes=$(aws --endpoint-url "$S3_ENDPOINT" s3api head-object \
  --bucket "$DB_BACKUP_BUCKET" --key "$key" --query ContentLength --output text)
if [ "$remote_bytes" != "$local_bytes" ]; then
  echo "Uploaded backup size does not match" >&2
  exit 1
fi

aws --endpoint-url "$S3_ENDPOINT" s3 cp "s3://$DB_BACKUP_BUCKET/$key" "$downloaded" --only-show-errors
local_sha256=$(sha256sum "$encrypted" | cut -d ' ' -f 1)
remote_sha256=$(sha256sum "$downloaded" | cut -d ' ' -f 1)
if [ "$remote_sha256" != "$local_sha256" ]; then
  echo "Downloaded backup SHA-256 does not match" >&2
  exit 1
fi

if [ "${FINAL_SYNC:-0}" = "1" ]; then
  metadata_key="postgres/${date_path}/fitician-${timestamp}.snapshot.json.age"
  aws --endpoint-url "$S3_ENDPOINT" s3 cp "$encrypted_metadata" \
    "s3://$DB_BACKUP_BUCKET/$metadata_key" --only-show-errors
  metadata_bytes=$(stat -c %s "$encrypted_metadata")
  remote_metadata_bytes=$(aws --endpoint-url "$S3_ENDPOINT" s3api head-object \
    --bucket "$DB_BACKUP_BUCKET" --key "$metadata_key" --query ContentLength --output text)
  if [ "$remote_metadata_bytes" != "$metadata_bytes" ]; then
    echo "Uploaded snapshot metadata size does not match" >&2
    exit 1
  fi
  aws --endpoint-url "$S3_ENDPOINT" s3 cp "s3://$DB_BACKUP_BUCKET/$metadata_key" \
    "$downloaded_metadata" --only-show-errors
  local_metadata_sha256=$(sha256sum "$encrypted_metadata" | cut -d ' ' -f 1)
  remote_metadata_sha256=$(sha256sum "$downloaded_metadata" | cut -d ' ' -f 1)
  if [ "$remote_metadata_sha256" != "$local_metadata_sha256" ]; then
    echo "Downloaded snapshot metadata SHA-256 does not match" >&2
    exit 1
  fi
  printf 'Encrypted snapshot metadata verified: s3://%s/%s (%s bytes, sha256 %s)\n' \
    "$DB_BACKUP_BUCKET" "$metadata_key" "$metadata_bytes" "$local_metadata_sha256"
fi

printf 'Encrypted database backup verified: s3://%s/%s (%s bytes, sha256 %s)\n' \
  "$DB_BACKUP_BUCKET" "$key" "$local_bytes" "$local_sha256"
