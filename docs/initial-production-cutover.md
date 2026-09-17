# Initial Fitician production cutover

The first deployment is operator-run. Keep `PRODUCTION_DEPLOY_ENABLED` unset until
the restored application has passed its public and authenticated checks.

1. Provision a VPS, DNS A/AAAA records for `FITICIAN_DOMAIN`, Docker Compose,
   `curl`, `age`, and AWS CLI. Put `compose.prod.yaml`, `Caddyfile`,
   `backup-production.sh`, operator `.env`, and mode-`0600` `backup.env` in
   `/opt/fitician`. Configure the GitHub Docker Hub and VPS secrets and the
   `VITE_MEDIA_PUBLIC_BASE_URL` variable. Do not put credentials in Git.
2. Re-run the public and private media verification commands in
   [public-media-s3-migration.md](public-media-s3-migration.md) against the
   current source database and buckets. Require zero missing active targets,
   SHA-256 failures, and public-read failures. The 2026-09-17 snapshot is
   historical evidence, not a cutover check.
3. Announce a short maintenance window and stop source writes. Record counts
   for `users`, `exercises`, `exercise_media_assets`, and the two nutrition
   catalogues plus `alembic_version`. Create a custom PostgreSQL dump, encrypt
   it with the offline age recipient, and keep the encrypted file inside the
   project workspace. Confirm that `pg_dump`, `age`, and the pipeline all exit
   successfully before restoring.
4. Start only the VPS `db` service. Decrypt the dump on the source machine and
   stream it through SSH to `pg_restore --single-transaction --exit-on-error`
   in the fresh VPS database. Keep the age identity off the VPS. Compare the
   recorded source counts and Alembic revision with the restored database.
5. Dispatch `Deploy Fitician production` for the SHA of a green CI run with
   `initial_deploy=true`. The helper rejects an empty restored user table.
   Check HTTPS, login and secure cookie, API requests, public S3 images and
   videos, authorized private media, both workers, and a fresh encrypted
   backup. Enable the daily backup timer and perform a restore drill into a
   disposable database.
6. Set repository variable `PRODUCTION_DEPLOY_ENABLED=true`. Later successful
   `main` pushes deploy automatically. For a pending Alembic revision, inspect
   the migration and dispatch the successful SHA with
   `allow_schema_migrations=true` after the backup is verified.

Use `/opt/fitician/.deployed-image-tag` as the last verified deployed SHA.
Keep the old source deployment and encrypted cutover dump until the new site
has passed the acceptance checks.
