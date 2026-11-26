# Iran schema release recovery

Use the protected regional workflow with `target=iran`, `deploy_kind=full`,
`allow_schema_migrations=true`, and the successful full CI run for the exact image
SHA. Confirm availability of the age recovery identity in the approved recovery
environment before approval. Keep the previous API, web, and worker images locally available.

For an existing Iran deployment with a schema change, the script stages and checks
the release first. It stops ingress, pauses diagnostics, and stops the API replicas,
scheduler, and queue workers using their Compose shutdown settings. It checks for
running writers, open PostgreSQL client and logical replication sessions, and
prepared transactions before taking the backup. It encrypts the backup and checks
the S3 readback against the original SHA-256. It checks quiescence again and verifies
the migrated revision before starting the candidate application.

## Respond to a failed deployment

Use trusted SSH and take the same `.regional-deploy.lock` before reconciliation. Inspect
`.regional-iran-schema-cutover/state`, `baseline`, and `backup.log` in the application root.
The baseline records the old contract path, previous web/API/worker/Agent tags, original
revision and candidate SHA, one value per line. The backup receipt records the exact object,
size, and SHA-256. Leave the marker in place until service recovery is verified.

- **`freezing`** — check the containers, the baseline revision and deployment process. The
  workflow can restart and verify the previous release on handled failures before migration.
  On interruption, manually verify the baseline and resume the previous release.
- **`migration`** — keep ingress and all writers stopped. Check that the deployment and its
  migration container have exited. Verify zero open client sessions and prepared transactions.
  Restore using the procedure below. The failed database remains available for inspection.
- **`candidate-start`** — the candidate may have accepted writes. Keep the services quiescent
  and preserve the database and Redis. Reconcile writes or roll forward under a reviewed
  recovery procedure before any snapshot restore.

### Restore after a migration failure

1. Download the exact ciphertext object from the receipt using the approved backup
   access. Verify its size and SHA-256 against the receipt. Decrypt with the approved age
   identity and stream directly into `pg_restore --exit-on-error --no-owner --no-acl` over
   trusted SSH. Use Bash `pipefail` and confirm the decrypt and restore both exit zero.
2. Restore into a newly created database on the same PostgreSQL instance with the original
   owner and a name reserved for this recovery. Use `template0` and preserve the original
   encoding and locale. Verify the original Alembic revision, key table counts and integrity,
   and zero unvalidated foreign keys before exposing the replacement.
3. With zero client sessions, connect to the maintenance database and rename the failed
   application database to a unique retained name. Rename the verified restored database
   to the original application database name in the same transaction. Confirm the transaction
   committed and verify both names before restarting services.
4. Use the saved active Compose contract and exact prior image tags. Bring up the API
   replicas, workers, scheduler and frontend with `--pull never --no-deps --wait`.
   Restore the prior diagnostics policy using the candidate's `diagnostics-release.py rollback`
   with the recorded candidate SHA. Keep PostgreSQL and Redis in place. Start Caddy after
   the previous services are ready. Run `ops/verify-regional.sh` using the old contract
   and tags, then check real request handling and worker health.
5. Archive the private marker directory under the candidate release directory with a
   recovery timestamp. Keep the encrypted backup, failed database, and previous images.

## Run the isolated drill

Run `ops/rehearse-iran-schema-cutover.py --work <new-short-workspace-path>
--alembic <backend-venv-alembic> --age-dir <directory-with-age-and-age-keygen>`.
The drill uses a unique internal Docker network, tmpfs PostgreSQL, synthetic writer
services, and an object-storage fixture. It uses the real backup script and real Alembic,
then injects a failing revision after a durable schema change. The result records drain,
backup, migration, restore, restart, and total outage time. Use a recent successful
production backup duration alongside these timings when estimating the maintenance window.
