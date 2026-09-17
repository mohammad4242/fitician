# Stateless media production

Production uses immutable registry images and S3 for all runtime media. The
developer checkout and local media directories are not deployment inputs.

## Images

GitHub Actions publishes these Docker Hub images after CI succeeds:

- `${DOCKERHUB_USERNAME}/fitician-backend:<git-sha>`
- `${DOCKERHUB_USERNAME}/fitician-frontend:<git-sha>`
- `${DOCKERHUB_USERNAME}/fitician-agent:<git-sha>`

`IMAGE_TAG` in production is always the full Git SHA. `main` is only a
convenience tag and is never the deployment identifier.

## VPS contract

The application directory contains the production Compose file, `Caddyfile`, and an
operator-managed `.env` file. The Compose file creates named Docker volumes
for PostgreSQL, Caddy certificates, and the Agent Service home. There are no source, media, upload,
import, report, or build-artifact bind mounts.

The backend and frontend images contain no runtime public/private media
library. Backend startup uses S3 with `MEDIA_LOCAL_FALLBACK_ENABLED=false`.
Missing S3 objects produce real storage errors rather than reading local disk.

## Runtime services

`compose.prod.yaml` runs PostgreSQL, one-shot Alembic migrations, the backend,
food-photo and notification workers, the Agent Service, and the static frontend
container. Caddy owns public ports 80 and 443, obtains HTTPS certificates for
`FITICIAN_DOMAIN`, and routes `/api/` and `/media/` directly to the backend.
The frontend and backend containers have no published host ports.
The Agent Service receives bounded in-memory image bytes from the backend when
private media is S3-backed, so it has no private-media mount.

## Required environment

The operator `.env` must provide the existing production application settings
plus:

```text
DOCKERHUB_USERNAME=
IMAGE_TAG=
FITICIAN_DOMAIN=
POSTGRES_PASSWORD=
FRONTEND_ORIGIN=https://<FITICIAN_DOMAIN>
COOKIE_SECURE=true
SESSION_COOKIE_NAME=__Host-fitician_session
MEDIA_STORAGE_BACKEND=s3
MEDIA_LOCAL_FALLBACK_ENABLED=false
S3_ENDPOINT=
S3_REGION=ir-thr-at1
S3_PUBLIC_BUCKET=fitician-media
S3_PRIVATE_BUCKET=fitician-private-media
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
MEDIA_PUBLIC_BASE_URL=
AGENT_SERVICE_TOKEN=
```

Secrets are supplied only through the operator environment. They are not in
the image, frontend bundle, repository, or workflow logs.

The GitHub Actions deployment workflow requires these repository or production
environment secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `VPS_HOST`,
`VPS_USER`, `VPS_SSH_PRIVATE_KEY`, and `VPS_KNOWN_HOSTS`. Set the non-secret
repository variable `VPS_APP_DIR` only when `/opt/fitician` is not used. The
frontend build may use the non-secret `VITE_MEDIA_PUBLIC_BASE_URL` variable.

## Deployment and rollback

`ops/deploy-production.sh` is an operator or CI helper. It is not a VPS
source-checkout requirement. The VPS only needs `compose.prod.yaml`, `Caddyfile`, and `.env`
under the application directory. Run the helper from a deployment host with
`COMPOSE_FILE` pointing at that Compose file, or run the same Docker Compose
commands from `/opt/fitician`.

The helper pulls immutable images, starts the dependency graph, waits for the
database and Agent Service, runs `alembic upgrade head` through the one-shot
`migrations` service, waits for backend/frontend health checks, and rolls back
to `PREVIOUS_IMAGE_TAG` if a pull, migration, or readiness check fails.

## Database backups

Provision a private S3 bucket dedicated to database backups, with a 30-day
retention lifecycle. Install `age` and AWS CLI on the VPS. Keep the age identity
needed for decryption offline; only its public recipient belongs on the VPS.
Create `/opt/fitician/backup.env` with mode `0600` and these fields:

```text
DB_BACKUP_BUCKET=
DB_BACKUP_AGE_RECIPIENT=
S3_ENDPOINT=
AWS_DEFAULT_REGION=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

Copy `ops/backup-production.sh` to `/opt/fitician/backup-production.sh`.
Install the two `ops/systemd/fitician-db-backup.*` units, enable the timer,
and run the service once before relying on the schedule. The script streams
`pg_dump` through `age`; only encrypted bytes touch VPS disk or the backup bucket.
It verifies the uploaded object size and fails without uploading when dump or
encryption fails. Run a monthly restore drill into a disposable database using
the offline age identity, check the restored user count and Alembic revision,
then remove that disposable database. Never restore over the live database.

## S3 boundaries

- `fitician-media` contains only `public/` runtime objects.
- `fitician-private-media` contains authenticated user media under
  `private/body-photos/`, `private/food-photos/`, `private/profile-photos/`,
  and `private/nutrition-labs/`.
- The current-reference migration contains 30 objects totaling 17,439,787
  bytes: 22 body photos, 7 food photos, 1 profile photo, and no lab files.
- Private objects have no public base URL. Backend authorization is required
  before private reads.
- Landing source copies, local public media, unresolved private files, and
  historical/import media remain in the developer/archive environment and are
  not deployment dependencies.
