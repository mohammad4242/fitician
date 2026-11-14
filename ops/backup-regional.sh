#!/usr/bin/env bash
# Resolve the currently running Iran database without changing its services or volumes.
set -euo pipefail
app_dir=${APP_DIR:-/opt/fitician-iran}
project=fitician-iran
id=$(docker ps --filter "label=com.docker.compose.project=$project" \
  --filter label=com.docker.compose.service=db --format '{{.ID}}')
[[ "$id" =~ ^[a-f0-9]{12,64}$ ]] || { echo 'One running Iran database is required' >&2; exit 1; }
contract=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}' "$id")
contract=$(python3 - "$contract" "$app_dir" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[2]).resolve(strict=True)
path = Path(sys.argv[1]).resolve(strict=True)
relative = path.relative_to(root)
if not path.is_file() or relative.parts[0] != 'releases' or path.name != 'compose.prod.iran.yaml':
    raise SystemExit('Database backup contract is outside the regional release root')
print(path)
PY
)
[[ -f "$app_dir/.env" && -f "$app_dir/ops/backup-production.sh" ]] || {
  echo 'Regional backup configuration or helper is missing' >&2; exit 1;
}
export COMPOSE_FILE="$contract" COMPOSE_PROJECT_NAME="$project" \
  FITICIAN_ENV_FILE="$app_dir/.env" BACKUP_ENV_FILE="$app_dir/backup.env" \
  DB_BACKUP_LOCK_FILE="$app_dir/.database-backup.lock"
exec bash "$app_dir/ops/backup-production.sh"
