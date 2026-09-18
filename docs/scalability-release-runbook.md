# Scalability release runbook

This runbook is for the first replicated Fitician release on the current VPS.
It keeps the existing immutable SHA deployment, encrypted backup, migration
gate, health verification, and schema-aware rollback behavior.

## Before push

Run from the repository root:

```bash
cd backend && uv run pytest
cd backend && uv run ruff check app/infrastructure app/cache app/rate_limits app/jobs app/observability app/resilience
cd backend && uv run python -m alembic heads
cd .. && python3 -m unittest discover -s ops/tests -p 'test_*.py' -v
docker compose -f compose.yaml -f compose.multi.yaml config --quiet
REDIS_PASSWORD=placeholder GRAFANA_ADMIN_PASSWORD=placeholder \
  docker compose -f compose.yaml -f compose.observability.yaml config --quiet
```

Run the local scale stack with deterministic/fake providers only. Record the
JSON output from `ops/load/run.sh` and `ops/load/failure-drills.sh all`.
Do not point load tools at production or paid AI, SMS, email, payment, or push
providers.

## Before CD

Require a successful GitHub Actions `Fitician CI` run for the exact commit.
The image publication job is downstream of backend, frontend, mobile, secret,
Compose/Caddy, Redis, rate-limit, queue, worker, scheduler, and monitoring
contract checks.

Confirm the release has:

- a full 40-character Git SHA image tag;
- a recent local load/failure artifact;
- a tested rollback SHA;
- a verified encrypted production backup plan;
- enough VPS memory for the configured replica/worker topology;
- no pending schema migration unless the reviewed migration flag is enabled.

## Deploy and observe

Use the existing `.github/workflows/deploy-production.yml` workflow. Never edit
the VPS `.env` through Git; production secrets stay in the operator-managed
environment. The deployment script backs up before rollout, waits for database
migrations and service health, probes both API replicas and Caddy HTTPS, and
updates `.deployed-image-tag` only after verification.

Observe for at least 30 minutes:

- Caddy routes only to ready backends;
- `/livez` stays live and `/readyz` stays ready;
- Redis availability and latency remain stable;
- queue oldest age and failed/dead-letter counts drain;
- DB pool checked-out/wait pressure stays below the connection budget;
- provider timeout/5xx rates and worker restarts stay within the release SLO.

The optional monitoring overlay is private and loopback-bound. Use an SSH
tunnel or an approved private admin network; never publish ports 9090/3000.

## Shutdown and leases

Body Analysis and Food Photo workers receive 450 seconds to finish an already
claimed provider call before Docker sends SIGKILL. Their provider timeout is
bounded at 420 seconds; their durable leases are 900 and 600 seconds,
respectively. Notification delivery receives 30 seconds for its 15-second
provider timeout and 60-second lease. The scheduler receives 60 seconds, and
API replicas receive 45 seconds to drain requests. A forced kill remains safe:
the replacement worker reclaims the durable row only after its lease becomes
stale, and owner-checked finalization prevents an old worker from finalizing a
reclaimed job.

## Rollback

If runtime verification or the observation gate fails, keep the previous SHA and
run the existing rollback path. App images may roll back only when the schema
is unchanged. If a schema migration ran, stop automatic rollback and restore
from the encrypted backup using the reviewed recovery procedure; never perform
an unsafe automatic database downgrade.
