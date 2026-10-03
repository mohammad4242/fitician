# PostgreSQL backup memory and Docker retention

Production PostgreSQL stores some large compressed JSON validation diagnostics. On
2026-10-03, a TOAST value in `workout_plan_generations` had a 97,603,148-byte raw
header length, although its compressed storage was small. `pg_dump` uses COPY,
which expands and buffers a whole row. Running the client inside the database
container charges both server and client allocations to the same cgroup.

An isolated synthetic 97.6 MB JSON row reproduced the production failure:
320 MiB caused a cgroup OOM kill and COPY connection loss; 512 MiB completed,
with a sampled peak of 358.39 MiB. Production cgroup `oom_kill=1` and the
PostgreSQL SIGKILL at 10:54:27 UTC corroborated the failed deployment log.
The kernel journal was inaccessible to the operator; no elevated-access bypass
was used. COPY has no sort/hash operation here, so increasing work_mem is not a
fix. No production diagnostic records were deleted or rewritten.

## Resource budget

PostgreSQL and both API containers are bounded at 512 MiB each. All other limits
remain unchanged, including the agent which had approached its 448 MiB limit.
The total normal service budget is 3136 MiB. The actual 3915 MiB VPS leaves
779 MiB headroom, above the existing 750 MiB gate. The operator environment
records the actual capacity as `VPS_MEMORY_MIB=3915`.

The initial correction uses Docker's live resource update without restarting
any production container; matching Compose overrides persist across deploys.
Do not remove caps or lower the host headroom gate. Monitor future largest JSON
rows and cgroup events; any further growth requires another measured budget
review, not deletion of production data.

Backups use an exclusive `.db-backup.lock`; an overlapping scheduled/deploy
backup fails clearly rather than opening another large COPY stream.

## Image retention

`ops/cleanup-production-images.py` defaults to dry run. Supply an explicit file
of current/rollback immutable SHAs and explicit Fitician repositories. Apply
requires `--apply`. It protects all container references, the specified SHAs,
the two newest images in each repository, images younger than 24 hours, mixed
repository images, dangling images, and all non-Fitician images.

Only enumerated immutable Fitician image references are removed, without force.
References and protection files are rechecked before each removal. No container,
volume, upload, backup, or PostgreSQL data cleanup is implemented. Optional
`--cleanup-build-cache` prunes only unused build cache older than seven days.
The daily operator cron entry uses these restrictions. Successful full releases
update the rollback protection file; component releases are additionally protected
by container references and the two-newest-image retention rule.

## Restore validation

The production verification run adds a temporary age verification recipient to
the ordinary encrypted pg_dump pipeline. It retains the existing operator
recipient, uploads through the normal script, downloads that exact object, and
compares encrypted SHA-256 hashes. It decrypts directly into pg_restore in an
isolated PostgreSQL container: no network, no production volume mounts, no host
port, no persistent test volume. The temporary key and encrypted local test files
are removed after completion. Restoring uses `--exit-on-error`; table counts,
Alembic revision, cgroup OOM counters, production start times, memory headroom,
and service readiness are checked without printing personal records.
