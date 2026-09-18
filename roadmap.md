# Fitician Scalability Foundation Roadmap

Date: 2026-09-18
Target: single VPS, 2 vCPU / 4 GB RAM
Selected queue architecture: PostgreSQL durable queues. Redis is cache and distributed rate-limit infrastructure only.

## Current-state architecture discovered

Production request path:

Internet -> Caddy -> one backend:8000 for /api and /media; frontend:80 for the rest.
FastAPI -> PostgreSQL, Agent Service, OpenRouter/OpenCode Zen, SMTP/SMS, FCM/APNs, and S3-compatible media.

Existing durable work:

- Food Photo Analysis is already a PostgreSQL queue using FOR UPDATE SKIP LOCKED, leases, stale recovery, retries, durable status, and notification outbox.
- Notification delivery is already a PostgreSQL outbox/delivery queue with deduplication, leases, retries, and dead-letter state.
- Body Analysis persists durable analysis revisions but executes through FastAPI BackgroundTasks.

FastAPI lifespan starts food-price, retention, and account-deletion loops in every API process. /healthz currently checks PostgreSQL but mixes liveness and readiness. database/session.py uses SQLAlchemy defaults, effectively 15 possible connections per process. Caddy has one backend upstream.

Existing auth and nutrition limiters are PostgreSQL fixed-window counters. They are not one shared abstraction and several expensive/security-sensitive routes are uncovered. Forwarded client IP trust is not explicit.

Baseline evidence: 76 focused auth/rate-limit/queue/notification/body-analysis/health tests passed. Local worker containers are stale: food-photo lacks boto3 and notification cannot see migration 20260915_155. Rebuild them before feature work.

## Risks

1. Body Analysis can be lost after API restart.
2. API replicas would duplicate scheduler loops.
3. Default pools can exhaust PostgreSQL.
4. One backend is an availability and throughput bottleneck.
5. Redis/cache/distributed limiting is absent.
6. Forwarded IP spoofing can bypass limits.
7. Notification calls hold DB transactions too long.
8. Workers lack graceful shutdown, health, metrics, and jitter.
9. Provider timeout/retry behavior is inconsistent.
10. CI PostgreSQL 16 differs from local/production PostgreSQL 18.
11. No repeatable multi-replica/load/failure gate exists.

## Architecture decisions

Queue options:

1. PostgreSQL durable queues — Recommended and selected.
2. Redis + Celery.
3. PostgreSQL/Celery hybrid.

Extend the existing PostgreSQL queue pattern. Redis is not a broker and does not hold durable job results. Reconsider Celery/RabbitMQ/Kafka only after measured queue polling/throughput or multi-host requirements justify it.

Redis:

- Use redis:8.10.1-alpine pinned to an immutable digest.
- Private network only, no production host port.
- Password, AOF everysec, named volume, maxmemory 128mb, noeviction.
- Cache failure falls back to PostgreSQL.
- Redis limiter failure falls back to PostgreSQL.
- If both limiters fail, return 503 RATE_LIMITER_UNAVAILABLE.
- Redis loss does not fail liveness or basic readiness.

Cache only global catalogue reads:

- exercises list/detail, TTL 300/600 seconds;
- nutrition foods, TTL 300 seconds;
- published member meals, TTL 300 seconds.

Use namespace generation keys and JSON Pydantic payloads. Invalidate after successful mutations. Never cache auth, payments, entitlements, Body Analysis, private/user state, live plans, or drafts.

Rate limits use Redis Lua fixed windows with HMAC actor hashes. Generic PostgreSQL fallback uses an independent SQLAlchemy session. Preserve 429, Retry-After, and existing error codes. Protect login, registration, OAuth, refresh, OTP, forgot-password, email verification, Body Analysis, Food Photo, uploads, expensive AI, workout generation, and admin operations.

Only a trusted Caddy peer may supply one forwarded client IP. Caddy overwrites forwarded headers; application trusts only the configured edge CIDR.

Body Analysis gets BodyAnalysisJob with queued/processing/completed/failed state, transactional enqueue, leases, stale recovery, bounded retries, jitter, safe finalization, and correlation ID. Existing public status and polling contracts stay unchanged.

All schedules move to one scheduler service. Existing advisory locks/idempotency remain.

Use explicit per-service pools, a 40-connection budget, and Alembic NullPool. Add structured JSON logs, Prometheus metrics, Prometheus/Grafana/Redis Exporter, separate liveness/readiness, two default API replicas, optional third replica profile, and Caddy active/passive health checks.

## Dependency graph

baseline -> Redis -> cache/rate-limit -> Body worker -> scheduler -> pools -> provider policy -> logs/metrics -> health -> local replicas -> load/failure -> CI -> production Compose -> CD verification.

## Final topology

    Internet
       |
      Caddy (TLS, round-robin, active/passive health)
       |------------------------------|
       v                              v
 frontend nginx              backend-1 / backend-2
                                      |
             +------------------------+----------------------+
             v                        v                      v
        PostgreSQL                 Redis                 Agent/S3/providers
        domain + durable jobs      cache + limits
             |
     body-analysis-worker
     food-photo-worker
     notification-worker
     singleton scheduler

Prometheus scrapes API/workers/scheduler/Redis Exporter; Grafana reads Prometheus.

# Luna implementation tasks

Each task is one logical commit. Write tests first, observe the expected red failure, implement the smallest change, run focused and regression checks, and stage only listed files.

## Task 1 — Reconcile executable baseline

### Goal
Rebuild stale local images and establish a green baseline without source changes.

### Why now
Current worker containers are stale and restarting.

### Inspect first
compose.yaml; backend/Dockerfile; backend/pyproject.toml; backend/uv.lock; backend/alembic/versions; backend/tests/conftest.py.

### Files to create
None.

### Files to modify
None.

### Do not modify
Volumes, migrations, .env, media, or unrelated untracked files.

### Implementation
Run uv sync --frozen --extra dev, rebuild backend/food-photo-worker/notification-worker, start with docker compose up -d --wait, and confirm old boto3/missing-migration errors disappear.

### Tests first
No new tests; baseline only.

### Verification
cd backend && uv run python -m alembic heads && uv run python -m alembic current
cd backend && uv run pytest && uv run ruff check && uv run mypy app
npm run test --workspace frontend
npm run lint --workspace frontend
npm run build --workspace frontend
docker compose build backend food-photo-worker notification-worker
docker compose up -d --wait
docker compose ps

### Expected result
Source, migration head, images, and current tests agree.

### Failure/rollback concern
Never use docker compose down -v or downgrade migrations.

### Commit boundary
No commit.

### Definition of Done
Workers are not restarting; baseline results are recorded; no tracked source changes exist.

## Task 2 — Add private persistent Redis

### Goal
Add Redis locally and in production without application usage.

### Why now
Cache and distributed limiting need a verified service.

### Inspect first
compose.yaml; compose.prod.yaml; .env.example; .github/workflows/ci.yml; ops/deploy-production.sh.

### Files to create
ops/redis/redis.conf.

### Files to modify
compose.yaml; compose.prod.yaml; .env.example; deployment contract tests.

### Do not modify
Queues, PostgreSQL volumes, production public ports, or real secrets.

### Implementation
Use redis:8.10.1-alpine pinned by digest; AOF everysec; RDB preamble; noeviction; maxmemory 128mb; password; named volume; healthcheck; restart and memory limit. Bind local Redis only to localhost and no production host port.

### Tests first
Require persistence, auth, noeviction, healthcheck, and no production Redis port.

### Verification
docker compose config --quiet
docker compose up -d redis
docker compose exec redis sh -c 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli ping'
python3 -m unittest discover -s ops/tests -p 'test_*.py' -v

### Expected result
Redis is healthy and private.

### Failure/rollback concern
No application path depends on Redis yet.

### Commit boundary
feat(infra): add private persistent Redis foundation

### Definition of Done
Image digest, AOF/noeviction, private production networking, and ops tests pass.

## Task 3 — Add bounded Redis client

### Goal
Own one bounded Redis pool with safe lifecycle and degraded diagnostics.

### Why now
Cache and limiter code must not create ad-hoc connections.

### Inspect first
backend/app/main.py; backend/app/config.py; backend/app/database/session.py; backend/pyproject.toml; backend/tests/test_health.py.

### Files to create
backend/app/infrastructure/__init__.py; backend/app/infrastructure/redis.py; backend/tests/infrastructure/test_redis.py.

### Files to modify
backend/app/config.py; backend/app/main.py; backend/pyproject.toml; backend/uv.lock; .env.example.

### Do not modify
Auth sessions, queues, or public schemas.

### Implementation
Add redis>=6,<7; typed host/port/db/password/pool/timeouts; pool max 10; app.state ownership; shutdown close; diagnostic-only ping; redaction.

### Tests first
Pool bounds, redaction, lifecycle, successful/failed ping, startup with Redis unavailable.

### Verification
cd backend && uv run pytest tests/infrastructure/test_redis.py tests/test_health.py -q
cd backend && uv run ruff check app/infrastructure app/config.py app/main.py tests/infrastructure
cd backend && uv run mypy app

### Expected result
API remains usable when Redis is unavailable.

### Failure/rollback concern
Do not make health fail only because Redis is unavailable.

### Commit boundary
feat(backend): add resilient Redis client lifecycle

### Definition of Done
Bounded pool, redaction, lifecycle tests, and outage behavior are verified.

## Task 4 — Implement cache core

### Goal
Implement versioned JSON cache, namespace invalidation, and owner-safe locks.

### Why now
All cached endpoints need one policy.

### Inspect first
Redis client; backend/app/errors.py; backend/app/main.py; response models.

### Files to create
backend/app/cache/__init__.py; backend/app/cache/keys.py; backend/app/cache/service.py; backend/tests/cache/test_service.py.

### Files to modify
backend/app/config.py; .env.example.

### Do not modify
Auth/session, payments, entitlements, or domain routers.

### Implementation
Use fitician:cache:v1:{namespace}:g{generation}:{sha256(canonical-json)}; JSON serialization; get/set/get_or_load/generation bump; token-safe lock release; Redis errors call loader; contention <=50 ms.

### Tests first
Miss, hit, invalidation, corrupt value, lock ownership/contention, TTL, Redis fallback.

### Verification
cd backend && uv run pytest tests/cache/test_service.py -q
cd backend && uv run ruff check app/cache tests/cache && uv run mypy app/cache

### Expected result
Cache failures fall back safely.

### Failure/rollback concern
Invalidation failure may leave data stale only until TTL.

### Commit boundary
feat(cache): add versioned Redis cache service

### Definition of Done
Deterministic keys, owner-safe locks, no raw user values, green tests.

## Task 5 — Cache exercise catalogue

### Goal
Cache exercise list/detail without crossing media presentations.

### Why now
Exercise catalogue is high-read and low-write.

### Inspect first
backend/app/exercises/router.py; backend/app/exercises/service.py; backend/app/admin/router.py; backend/app/admin/service.py; exercise/admin tests.

### Files to create
backend/tests/exercises/test_exercise_cache.py.

### Files to modify
Exercise/admin routers; config; .env.example.

### Do not modify
Authorization, response shapes, media storage, imports, seed content.

### Implementation
Cache normalized list filters for 300 seconds and detail by slug/effective presentation for 600 seconds. Run guards before cache lookup. Bump exercises namespace after successful create/update/delete/media writes.

### Tests first
Miss/population, hit/no DB work, presentation isolation, mutation invalidation, Redis fallback.

### Verification
cd backend && uv run pytest tests/exercises/test_exercise_cache.py tests/exercises/test_exercise_api.py tests/admin/test_exercise_api.py -q
cd backend && uv run ruff check app/exercises/router.py app/admin/router.py tests/exercises/test_exercise_cache.py

### Expected result
Repeated reads avoid DB work without presentation leakage.

### Failure/rollback concern
Never move profile checks behind cache lookup.

### Commit boundary
feat(exercises): cache catalogue reads with invalidation

### Definition of Done
All query inputs are keyed and all admin mutations invalidate.

## Task 6 — Cache nutrition catalogues

### Goal
Cache foods and published member meals.

### Why now
They are shared read-heavy catalogues with explicit mutation paths.

### Inspect first
backend/app/nutrition/router.py; food/meal catalogue services; price update service; nutrition tests.

### Files to create
backend/tests/nutrition/test_catalogue_cache.py.

### Files to modify
Nutrition router/price service; config; .env.example.

### Do not modify
Member state, drafts, plans, pricing correctness, private URLs.

### Implementation
Use nutrition-foods and nutrition-meals namespaces with 300-second TTL. Key normalized filters/category/page. Invalidate food writes, images, retirements, overrides, scheduled price updates; invalidate meal writes/images. Never cache drafts/admin-all.

### Tests first
Miss/hit, filter separation, member/admin isolation, mutation invalidations, fallback.

### Verification
cd backend && uv run pytest tests/nutrition/test_catalogue_cache.py tests/nutrition/test_food_catalogue_api.py tests/nutrition/test_meal_catalogue.py -q
cd backend && uv run ruff check app/nutrition tests/nutrition/test_catalogue_cache.py

### Expected result
Only safe shared catalogues are cached.

### Failure/rollback concern
Never cache entitlements, plans, tracking, or drafts.

### Commit boundary
feat(nutrition): cache shared catalogues safely

### Definition of Done
Separate namespaces, no drafts in Redis, mutation tests pass.

## Task 7 — Enforce trusted proxy client IPs

### Goal
Prevent forwarded-IP spoofing from bypassing limits.

### Why now
Distributed IP limits require an explicit proxy boundary.

### Inspect first
Caddyfile; compose.prod.yaml; auth/nutrition routers; backend/app/main.py.

### Files to create
backend/app/http/__init__.py; backend/app/http/client_ip.py; backend/tests/http/test_client_ip.py.

### Files to modify
backend/app/config.py; .env.example; Caddyfile; compose.prod.yaml.

### Do not modify
OAuth/session validation or public routes.

### Implementation
Add TRUSTED_PROXY_CIDRS; trust one overwritten forwarded IP only when direct peer is in the edge CIDR; otherwise use direct peer. Define a private edge subnet and fixed Caddy IP.

### Tests first
Direct/trusted/untrusted/malformed/multi-hop/IPv4/IPv6 cases.

### Verification
cd backend && uv run pytest tests/http/test_client_ip.py tests/auth/test_rate_limits.py -q
cd backend && uv run ruff check app/http app/config.py tests/http
docker compose -f compose.prod.yaml config --quiet

### Expected result
Clients cannot choose their limiter IP.

### Failure/rollback concern
Incorrect CIDR must fail config tests before deployment.

### Commit boundary
fix(security): enforce trusted proxy client IP resolution

### Definition of Done
Spoof tests pass; Caddy overwrites headers; backend stays private.

## Task 8 — Add Redis-primary PostgreSQL-fallback limiter

### Goal
Create one atomic limiter independent of request transactions.

### Why now
All protected endpoints need one outage policy.

### Inspect first
Auth/nutrition limiter models/services; database base/session; rate-limit tests.

### Files to create
backend/app/rate_limits/__init__.py; backend/app/rate_limits/models.py; backend/app/rate_limits/service.py; backend/alembic/versions/20260918_156_add_operation_rate_limits.py; backend/tests/rate_limits/test_service.py.

### Files to modify
backend/app/database/base.py; backend/app/config.py; .env.example.

### Do not modify
Drop/rename legacy tables or store raw actors.

### Implementation
Add generic operation/window/actor-hash table. Hash actors with RATE_LIMIT_HMAC_SECRET. Implement Lua INCR/EXPIRE/TTL. On Redis failure use an independent short-lived PostgreSQL session. Fail closed only when both fail.

### Tests first
Atomic boundaries, concurrency, fallback, session isolation, Retry-After, hash privacy, migration.

### Verification
cd backend && uv run python -m alembic upgrade head
cd backend && uv run pytest tests/rate_limits tests/database -q
cd backend && uv run ruff check app/rate_limits tests/rate_limits

### Expected result
All replicas share exact counters and Redis outages remain secure.

### Failure/rollback concern
Migration is additive; old tables remain.

### Commit boundary
feat(security): add distributed rate limiter with database fallback

### Definition of Done
Atomic Lua, independent fallback, no raw actors, green tests.

## Task 9 — Migrate authentication limits

### Goal
Apply shared limits to every sensitive auth flow.

### Why now
Auth is the highest-risk abuse surface.

### Inspect first
Auth router/service/security and all auth rate-limit tests.

### Files to create
None expected.

### Files to modify
backend/app/auth/router.py; backend/app/auth/service.py; config; auth tests; .env.example.

### Do not modify
OAuth/password/session semantics or existing error contracts.

### Implementation
Cover registration, password login, Google/Apple, refresh, OTP send/resend/verify, forgot-password, email verification with IP and normalized identifier counters. Preserve 429, Retry-After, and enumeration protection.

### Tests first
Cross-replica, Redis outage, fail-closed, and missing-route coverage.

### Verification
cd backend && uv run pytest tests/auth -q
cd backend && uv run ruff check app/auth tests/auth

### Expected result
Sensitive auth flows share distributed counters.

### Failure/rollback concern
Do not leak account existence through limiter behavior.

### Commit boundary
feat(auth): enforce shared distributed abuse limits

### Definition of Done
All listed flows covered; contracts and outage tests pass.

## Task 10 — Protect expensive application/admin endpoints

### Goal
Protect Body Analysis, media, food-photo, lab, workout, and admin expensive operations.

### Why now
Replica count otherwise multiplies abuse capacity.

### Inspect first
Body Analysis, body-photo, nutrition, profile, workout, and admin routers.

### Files to create
backend/tests/rate_limits/test_expensive_routes.py.

### Files to modify
Target routers; config; .env.example.

### Do not modify
Entitlements, quotas, upload validation, admin authorization.

### Implementation
Apply stable operation names and IP/user policies before file reads/provider calls. Preserve existing nutrition user limits and add IP limits.

### Tests first
Boundary, IP/user independence, replica sharing, Retry-After, fallback.

### Verification
cd backend && uv run pytest tests/rate_limits/test_expensive_routes.py tests/body_analysis/test_analysis_api.py tests/nutrition/test_food_photo_queue.py tests/workouts/test_workout_plan_api.py -q
cd backend && uv run ruff check app tests/rate_limits/test_expensive_routes.py

### Expected result
Expensive operations cannot bypass limits by switching replicas.

### Failure/rollback concern
Avoid double-counting existing nutrition checks.

### Commit boundary
feat(security): limit expensive distributed operations

### Definition of Done
Every target category has coverage and existing quotas remain.

## Task 11 — Add Body Analysis durable jobs

### Goal
Persist one claimable job beside each analysis revision.

### Why now
The worker needs transactional enqueue state.

### Inspect first
Body Analysis models/service; food-photo job model/worker; queue design spec.

### Files to create
backend/alembic/versions/20260918_157_add_body_analysis_jobs.py; backend/tests/body_analysis/test_job_queue.py.

### Files to modify
backend/app/body_analysis/models.py; backend/app/database/base.py.

### Do not modify
Existing result/review tables or food-photo tables.

### Implementation
Add one-to-one BodyAnalysisJob with status, availability, lease owner/time, attempts/max, immutable non-secret execution config, correlation ID, safe errors, timestamps, indexes, and constraints.

### Tests first
Constraints, uniqueness, indexes, relationships, migration.

### Verification
cd backend && uv run python -m alembic upgrade head
cd backend && uv run pytest tests/body_analysis/test_job_queue.py tests/database -q

### Expected result
Every accepted analysis has one durable job.

### Failure/rollback concern
Do not rewrite existing analyses.

### Commit boundary
feat(body-analysis): add durable analysis job model

### Definition of Done
Additive migration and model tests pass.

## Task 12 — Enqueue Body Analysis transactionally

### Goal
Create analysis and job atomically with a non-secret execution snapshot.

### Why now
Returning queued without a committed job loses work.

### Inspect first
Body Analysis service/runtime; task provider; food-photo snapshot helpers; execution tests.

### Files to create
backend/app/body_analysis/job_config.py.

### Files to modify
backend/app/body_analysis/service.py; Body Analysis tests.

### Do not modify
Public status/schema, quota keys, manual retry semantics.

### Implementation
Extract snapshot/rebuild behavior; insert analysis/job in one transaction; include provider/model/prompt/schema/timeouts/routing/policy; propagate correlation; make active duplicates idempotent; automatic retries reuse the revision; manual retry creates the normal new revision.

### Tests first
Atomic rollback, duplicate enqueue, immutable snapshot, secret exclusion, quota once, retry revision.

### Verification
cd backend && uv run pytest tests/body_analysis/test_job_queue.py tests/body_analysis/test_execution_and_reviews.py -q
cd backend && uv run ruff check app/body_analysis tests/body_analysis

### Expected result
No analysis is returned queued without a committed job.

### Failure/rollback concern
Automatic retries never consume quota again.

### Commit boundary
feat(body-analysis): enqueue analysis jobs transactionally

### Definition of Done
Atomicity, idempotency, secret exclusion, quota tests pass.

## Task 13 — Implement Body Analysis worker

### Goal
Execute Body Analysis independently with leases, retries, stale recovery, jitter, and terminal failure.

### Why now
This is the primary restart/replica reliability target.

### Inspect first
Body Analysis router/service; food-photo worker; notification worker; provider tests.

### Files to create
backend/app/body_analysis/worker.py; backend/tests/body_analysis/test_worker.py.

### Files to modify
backend/app/body_analysis/router.py; config; compose.yaml; .env.example; API tests.

### Do not modify
Food-photo queue technology or public status values.

### Implementation
Claim queued/stale jobs with FOR UPDATE SKIP LOCKED; commit lease before provider work; rebuild current credentials from snapshot; retry only transient errors with full jitter; finalize only matching owner; mark poison jobs failed; remove BackgroundTasks; add worker; retain POST 202.

### Tests first
Claim exclusivity, stale reclaim, retry, poison failure, worker kill, ownership-safe finalization, duplicate prevention, credential refresh.

### Verification
cd backend && uv run pytest tests/body_analysis/test_worker.py tests/body_analysis -q
cd backend && uv run ruff check app/body_analysis tests/body_analysis
docker compose up -d --build body-analysis-worker

### Expected result
API/worker restarts cannot lose accepted analysis.

### Failure/rollback concern
Provider execution is at-least-once after crash; finalization is idempotent.

### Commit boundary
feat(body-analysis): execute analysis through durable worker

### Definition of Done
No Body Analysis BackgroundTasks; lease/recovery tests and independent worker pass.

## Task 14 — Preserve web/mobile resumable status contracts

### Goal
Prove current clients recover queued status after remount/restart.

### Why now
Server durability must be visible to users.

### Inspect first
Web body-photo result/wizard/API; mobile Body Analysis result/wizard/API.

### Files to create
None expected.

### Files to modify
Existing web/mobile Body Analysis tests only.

### Do not modify
Polling UX, status wording, or API types unless a real defect appears.

### Implementation
Add queued/analyzing/completed/failed remount tests, polling recovery, and GET reload tests. Run OpenAPI/shared contracts.

### Tests first
New client tests are the red phase.

### Verification
npm run test --workspace frontend -- --run src/features/bodyPhotos
npm run test --workspace @fitician/mobile -- bodyAnalysis
npm run test:native --workspace @fitician/mobile
npm run check:openapi
npm run test:contracts

### Expected result
Clients resume from durable server state.

### Failure/rollback concern
Do not add a second client state machine.

### Commit boundary
test(body-analysis): prove durable polling across restarts

### Definition of Done
Reload/remount/poll recovery and contract checks pass.

## Task 15 — Harden existing workers

### Goal
Preserve food-photo/outbox guarantees while adding jitter, shutdown, bounded concurrency, and safe transaction scope.

### Why now
All workers must be production-safe before scaling.

### Inspect first
Food-photo worker; notification worker/models; worker tests.

### Files to create
backend/app/jobs/__init__.py; backend/app/jobs/runtime.py; backend/tests/jobs/test_runtime.py.

### Files to modify
Food-photo/notification workers; config; .env.example; worker tests.

### Do not modify
Queue technology, deduplication keys, dead-letter semantics, provider payloads.

### Implementation
Add stop events, full jitter, bounded concurrency default one, graceful claim stopping. Refactor notifications to claim/commit, call provider without transaction, then lock/finalize. Preserve at-least-once and validate lease > timeout + shutdown margin.

### Tests first
Shutdown, no-new-claims, lease recovery, jitter, DB release, duplicate claim tests.

### Verification
cd backend && uv run pytest tests/jobs tests/nutrition/test_food_photo_queue.py tests/notifications -q
cd backend && uv run ruff check app/jobs app/nutrition/food_photo_worker.py app/notifications/worker.py tests/jobs

### Expected result
Workers stop safely and provider calls hold no long DB transaction.

### Failure/rollback concern
Do not claim exactly-once push delivery.

### Commit boundary
refactor(workers): harden leases retries and graceful shutdown

### Definition of Done
Existing queue tests and new shutdown/transaction tests pass.

## Task 16 — Separate scheduled work

### Goal
Run all schedules in one service, never in FastAPI replicas.

### Why now
Replica scaling is unsafe while lifespan owns schedules.

### Inspect first
main.py; price/retention/account schedulers; notification worker/reminders; scheduler tests.

### Files to create
backend/app/scheduler/__init__.py; backend/app/scheduler/main.py; backend/tests/scheduler/test_main.py.

### Files to modify
main.py; notification worker; compose.yaml; scheduler tests.

### Do not modify
Advisory locks, run idempotency, deletion locking, retention policy.

### Implementation
Create signal-aware scheduler for price, retention, deletion, reminder production. Remove lifespan tasks. Move reminder production out of delivery worker. Preserve locks/idempotency and continue after individual errors.

### Tests first
API starts zero schedulers; duplicate scheduler instances stay idempotent; reminders come from scheduler; shutdown cancels.

### Verification
cd backend && uv run pytest tests/scheduler tests/nutrition/test_food_pricing.py tests/notifications/test_notification_events.py tests/test_health.py -q
cd backend && uv run ruff check app/scheduler app/main.py app/notifications/worker.py tests/scheduler
docker compose up -d --build scheduler

### Expected result
Three APIs do not multiply schedules.

### Failure/rollback concern
Keep advisory locks as secondary protection.

### Commit boundary
refactor(scheduler): separate scheduled work from API replicas

### Definition of Done
FastAPI creates no scheduler; dedicated scheduler and duplicate tests pass.

## Task 17 — Harden database pools

### Goal
Bound per-service PostgreSQL pools and enforce a connection budget.

### Why now
Replicas/workers otherwise inherit unsafe defaults.

### Inspect first
database/session.py; alembic/env.py; config; Compose.

### Files to create
backend/tests/database/test_session_pool.py; ops/check-db-connection-budget.py; ops/tests/test_db_connection_budget.py.

### Files to modify
database/session.py; alembic/env.py; config; both Compose files; .env.example.

### Do not modify
PostgreSQL max_connections automatically or unrelated transactions.

### Implementation
Add pool size/overflow/timeout/recycle/pre-ping/LIFO, connect/statement timeouts, application name, cache keys including pool settings, Alembic NullPool, and a budget preflight.

### Tests first
Engine options, cache separation, checkout timeout/release, NullPool, budget.

### Verification
cd backend && uv run pytest tests/database/test_session_pool.py -q
cd backend && uv run ruff check app/database tests/database/test_session_pool.py
python3 ops/check-db-connection-budget.py --replicas 2

### Expected result
Default production remains below 40 configured connections.

### Failure/rollback concern
Do not increase pools to hide slow queries.

### Commit boundary
perf(database): bound per-service connection pools

### Definition of Done
Configurable pools, NullPool migrations, budget preflight pass.

## Task 18 — Standardize external timeout/retry policy

### Goal
Bound all external calls and retry only safe transient failures.

### Why now
Unbounded providers exhaust API and workers.

### Inspect first
AI/auth providers; FCM/APNs; nutrition providers; media/S3; billing; config.

### Files to create
backend/app/resilience/__init__.py; backend/app/resilience/policy.py; backend/tests/resilience/test_policy.py; docs/provider-resilience.md.

### Files to modify
Provider modules; config; .env.example.

### Do not modify
Unsafe payment retries, provider secrets/logging, or auth delivery queue semantics.

### Implementation
Define connect/read/write/pool/total timeout, full-jitter backoff, eligibility, max attempts, and terminal mapping per provider. Configure boto3 timeouts/attempts. Keep job-level retries authoritative.

### Tests first
Fake-clock eligibility, unsafe-write non-retry, caps, jitter, terminal mapping.

### Verification
cd backend && uv run pytest tests/resilience tests/ai tests/body_analysis/test_providers.py tests/auth/test_providers.py tests/notifications -q
cd backend && uv run ruff check app/resilience app tests/resilience

### Expected result
Every external operation has finite behavior.

### Failure/rollback concern
Observe metrics before further tightening defaults.

### Commit boundary
refactor(resilience): standardize provider timeouts and retries

### Definition of Done
Policy covers all providers; unsafe writes are not blindly retried.

## Task 19 — Add structured correlated logs

### Goal
Trace requests into durable jobs without sensitive content.

### Why now
Failure/load evidence needs cross-process correlation.

### Inspect first
main.py; errors.py; workers; Agent Service logging.

### Files to create
backend/app/observability/__init__.py; backend/app/observability/logging.py; backend/alembic/versions/20260918_158_add_job_correlation_ids.py; backend/tests/observability/test_logging.py.

### Files to modify
main.py; job/outbox models/workers; config; .env.example.

### Do not modify
X-Correlation-ID or log payloads/tokens/private media.

### Implementation
Emit timestamp/level/service/instance/event/request/job/attempt/duration/error fields. Add nullable correlation IDs to food-photo jobs and notification outbox events; propagate from enqueue; redact known secret fields.

### Tests first
Correlation propagation, JSON shape, redaction, migration.

### Verification
cd backend && uv run python -m alembic upgrade head
cd backend && uv run pytest tests/observability tests/errors tests/notifications tests/body_analysis/test_worker.py -q
cd backend && uv run ruff check app/observability app tests/observability

### Expected result
Request-to-job tracing works using safe IDs.

### Failure/rollback concern
Never emit prompts, image contents, provider bodies, or secrets.

### Commit boundary
feat(observability): add structured correlated runtime logs

### Definition of Done
JSON/redaction/migration/correlation tests pass.

## Task 20 — Instrument metrics and diagnostics

### Goal
Expose bounded Prometheus metrics for HTTP, DB, Redis, queues, workers, and providers.

### Why now
Capacity and release gates need measurements.

### Inspect first
main.py; database/session.py; workers/scheduler; resilience policy; queue models.

### Files to create
backend/app/observability/metrics.py; backend/app/observability/runtime_server.py; backend/app/system/router.py; backend/app/system/schemas.py; metrics/diagnostics tests.

### Files to modify
backend/pyproject.toml; backend/uv.lock; main/session/workers/providers/config; .env.example.

### Do not modify
High-cardinality or sensitive metric labels; public /metrics.

### Implementation
Add prometheus-client; instrument HTTP count/latency/status/inflight, pool checkout/wait, Redis/cache/limiter, queue depth/oldest/retries/duration, worker readiness/busy, provider latency/error. Add redacted admin diagnostics.

### Tests first
Metric increments, label allowlists, sensitive-value absence, gauges, diagnostics auth.

### Verification
cd backend && uv run pytest tests/observability/test_metrics.py tests/system/test_diagnostics.py -q
cd backend && uv run ruff check app/observability app/system tests/observability

### Expected result
Required signals are measurable safely.

### Failure/rollback concern
Metrics never fail requests.

### Commit boundary
feat(observability): expose bounded application metrics

### Definition of Done
Metrics and diagnostics tests pass; metrics remain private.

## Task 21 — Add Prometheus/Grafana monitoring

### Goal
Collect and visualize metrics within 4 GB.

### Why now
Metrics need retention, dashboards, and alert rules.

### Inspect first
Compose files, ops docs, metrics endpoints.

### Files to create
compose.observability.yaml; ops/monitoring/prometheus.yml; ops/monitoring/alerts.yml; Grafana provisioning/dashboard files; docs/observability.md.

### Files to modify
.env.example; CI config.

### Do not modify
Public monitoring exposure or add Loki/Tempo/cAdvisor/Alertmanager.

### Implementation
Use digest-pinned Prometheus 3.13.3, Grafana 12.4.10, Redis Exporter 1.91.1; bind to localhost; retain seven days/1 GB; provision dashboards/rules; apply memory/CPU limits.

### Tests first
Validate provisioning and config in CI.

### Verification
docker compose -f compose.yaml -f compose.observability.yaml config --quiet
docker compose -f compose.yaml -f compose.observability.yaml up -d
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://127.0.0.1:3000/api/health

### Expected result
Dashboards load; monitoring failure does not stop application services.

### Failure/rollback concern
Keep monitoring as an optional overlay during rollout.

### Commit boundary
feat(ops): add lightweight production observability stack

### Definition of Done
Images pinned, ports private, dashboards/rules load.

## Task 22 — Separate liveness/readiness and graceful drain

### Goal
Provide correct API/worker/scheduler health semantics.

### Why now
Caddy needs readiness before replicas.

### Inspect first
main.py; health tests; worker entrypoints; Compose.

### Files to create
backend/tests/observability/test_runtime_server.py.

### Files to modify
main/runtime server/workers/scheduler; Compose; health tests; .env.example.

### Do not modify
Make liveness dependency-sensitive or Redis mandatory for readiness.

### Implementation
Add /livez, /readyz, keep /healthz as readiness alias, mark unready before shutdown, set graceful timeout, expose private worker/scheduler probes, require DB claim self-check, add stop grace periods and non-production instance header.

### Tests first
Liveness/readiness outage behavior, Redis degraded readiness, drain, worker readiness, interrupted lease.

### Verification
cd backend && uv run pytest tests/test_health.py tests/observability/test_runtime_server.py tests/jobs -q
cd backend && uv run ruff check app tests/test_health.py tests/observability
docker compose up -d --build --wait

### Expected result
Unready replicas stop receiving traffic; Redis loss stays non-fatal.

### Failure/rollback concern
Update deployment health tests with any compatibility change.

### Commit boundary
feat(runtime): separate health readiness and graceful drain

### Definition of Done
Liveness/readiness/drain/worker checks pass.

## Task 23 — Add local multi-replica Caddy stack

### Goal
Prove three APIs distribute requests and share state.

### Why now
All shared correctness foundations are complete.

### Inspect first
Compose files; Caddyfile; main; stateless-media doc.

### Files to create
compose.scale.yaml; ops/tests/test_local_scale_contract.py; docs/local-scalability-testing.md.

### Files to modify
Caddyfile; compose.yaml.

### Do not modify
Another reverse proxy, sticky sessions, or process-local correctness state.

### Implementation
Parameterize Caddy upstreams; configure round-robin, active /readyz, passive failure, safe-method retry; add backend-2/backend-3 and Caddy on 8080; verify sessions/cache/limits/job status across replicas.

### Tests first
Scale contract and shared-state integration tests.

### Verification
docker compose -f compose.yaml -f compose.scale.yaml config --quiet
docker compose -f compose.yaml -f compose.scale.yaml up -d --build --wait
python3 -m unittest ops.tests.test_local_scale_contract -v

### Expected result
At least three instance IDs are observed through Caddy.

### Failure/rollback concern
Local-only until CI gates pass.

### Commit boundary
feat(infra): add local multi-replica Caddy test stack

### Definition of Done
Three APIs healthy; distribution/shared state proven.

## Task 24 — Add deterministic k6 load scenarios

### Goal
Measure catalogue, limiter, queue, and replica behavior without paid providers.

### Why now
Production requires repeatable local evidence.

### Inspect first
Fake providers; scale Compose; Body/food-photo APIs; auth helpers.

### Files to create
tests/load fake Agent Service/seed/k6 scripts; ops/load/run.sh; docs/load-testing.md.

### Files to modify
compose.scale.yaml.

### Do not modify
Production provider settings or paid-provider paths.

### Implementation
Add deterministic fake Agent Service and isolated seed data. Test catalogue bursts, distributed login limits, Body Analysis submissions/polling, queue depth, and collect percentiles/throughput/errors/DB/cache/worker metrics. Gate cached p95<300ms, p99<750ms, errors<1%, hit ratio>90%, body enqueue p95<500ms, fake completion<120s.

### Tests first
Fake-provider determinism and seed idempotency.

### Verification
docker compose -f compose.yaml -f compose.scale.yaml up -d --build --wait
bash ops/load/run.sh catalogue
bash ops/load/run.sh rate-limits
bash ops/load/run.sh body-analysis

### Expected result
Thresholds pass with no paid calls.

### Failure/rollback concern
Fake mode is rejected in production.

### Commit boundary
test(load): add deterministic scalability scenarios

### Definition of Done
Repeatable machine-readable scenarios and no paid calls.

## Task 25 — Automate failure drills

### Goal
Verify component failure and recovery.

### Why now
Load success alone does not prove resilience.

### Inspect first
Scale Compose, load scripts, leases, readiness, Caddy policy.

### Files to create
ops/load/failure-drills.sh; ops/tests/test_failure_drill_contract.py.

### Files to modify
docs/load-testing.md.

### Do not modify
Volumes, production resources, or arbitrary sleeps.

### Implementation
Use deadline-based polling for Redis stop/restart; worker kill mid-job; backend kill; 100-job backlog; test-only pool exhaustion; PostgreSQL outage/recovery; one Caddy upstream failure. Store ignored JSON results.

### Tests first
Static safety checks for target project, deadlines, and no volume deletion.

### Verification
python3 -m unittest ops.tests.test_failure_drill_contract -v
bash ops/load/failure-drills.sh all

### Expected result
All six failure classes recover within documented deadlines.

### Failure/rollback concern
Scripts refuse production context.

### Commit boundary
test(resilience): automate local failure drills

### Definition of Done
Every drill has a deadline and no destructive volume action.

## Task 26 — Add fast CI scalability gates

### Goal
Make Redis, queue, scheduler, lint, and configuration correctness merge gates.

### Why now
Local foundations are complete.

### Inspect first
.github/workflows/ci.yml; image dependencies; ops tests.

### Files to create
None expected.

### Files to modify
.github/workflows/ci.yml; workflow/ops tests.

### Do not modify
Existing jobs, SHA tags, frontend/mobile checks, or secret scans.

### Implementation
Align CI PostgreSQL to 18; add Redis service; run Ruff/mypy; run Redis-backed tests; validate Compose/Redis/Prometheus/Grafana/Caddy; worker/scheduler smoke; keep image publication downstream of every gate.

### Tests first
Workflow contract tests for each gate.

### Verification
python3 -m unittest discover -s ops/tests -p 'test_*.py' -v
cd backend && uv run pytest && uv run ruff check && uv run mypy app
docker compose -f compose.prod.yaml -f compose.observability.yaml config --quiet

### Expected result
Normal CI catches distributed correctness and configuration defects.

### Failure/rollback concern
Do not add full benchmarks to every PR.

### Commit boundary
ci(scalability): gate Redis workers schedulers and static checks

### Definition of Done
PostgreSQL 18, Redis, Ruff, mypy, and config gates are required.

## Task 27 — Add replica smoke and heavy-load workflow

### Goal
Run short replica checks on PRs and heavy load/failure tests separately.

### Why now
Runtime profiles differ.

### Inspect first
CI/deployment workflows and load scripts.

### Files to create
.github/workflows/load-test.yml.

### Files to modify
.github/workflows/ci.yml; workflow tests.

### Do not modify
Production secrets, auto-deploy triggers, fake-provider restrictions.

### Implementation
Add PR two-replica smoke and manual/nightly full load/failure workflow. Upload JSON/log artifacts. Require a recent heavy success in release checklist.

### Tests first
Workflow trigger, artifact, fake-provider, no-production-secret tests.

### Verification
python3 -m unittest ops.tests.test_deploy_workflow -v

### Expected result
PRs receive quick distribution coverage; heavy evidence is retained separately.

### Failure/rollback concern
Heavy failure blocks release approval, not source merging by itself.

### Commit boundary
ci(load): separate replica smoke from heavy resilience tests

### Definition of Done
PR smoke uses two APIs; heavy artifacts exist; paid providers stay disabled.

## Task 28 — Add production replicas and private infrastructure

### Goal
Apply local topology to production Compose/Caddy.

### Why now
All local and CI gates pass.

### Inspect first
compose.prod.yaml; observability overlay; Caddyfile; stateless media doc; load evidence.

### Files to create
None expected.

### Files to modify
Production Compose/Caddy; env example; media/deployment contract tests.

### Do not modify
Immutable tags, S3 boundaries, private DB/Redis, or add another proxy.

### Implementation
Add backend-1/backend-2 and optional backend-3 profile; Caddy round-robin/active/passive health; Body worker; singleton scheduler; Redis volume; worker/scheduler healthchecks; resource limits; one migration service; no migrations in ordinary service commands; private monitoring; no DB/Redis host ports.

### Tests first
Production contract tests for replicas, counts, healthchecks, limits, privacy, and S3 media.

### Verification
DOCKERHUB_USERNAME=example IMAGE_TAG=0000000000000000000000000000000000000000 POSTGRES_PASSWORD=placeholder AGENT_SERVICE_TOKEN=placeholder REDIS_PASSWORD=placeholder GRAFANA_ADMIN_PASSWORD=placeholder FITICIAN_DOMAIN=example.com docker compose -f compose.prod.yaml -f compose.observability.yaml config --quiet
docker run --rm -e FITICIAN_DOMAIN=example.com -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.10.2-alpine caddy validate --config /etc/caddy/Caddyfile
python3 -m unittest discover -s ops/tests -p 'test_*.py' -v

### Expected result
Production describes a private two-replica topology within budget.

### Failure/rollback concern
All schema changes remain additive.

### Commit boundary
feat(production): add replicated API and worker topology

### Definition of Done
Two APIs default; one scheduler; DB/Redis private; Caddy/resource checks pass.

## Task 29 — Extend CD verification and rollback

### Goal
Make current CD verify every required component safely.

### Why now
One API health response is insufficient.

### Inspect first
.github/workflows/deploy-production.yml; ops/deploy-production.sh; backup script; deploy tests.

### Files to create
ops/verify-production.sh; ops/tests/test_verify_production.py.

### Files to modify
ops/deploy-production.sh; deploy workflow; deploy tests.

### Do not modify
Backup-before-deploy, full SHA, migration gate, .deployed-image-tag, schema-aware rollback, automatic DB downgrade prohibition.

### Implementation
Preserve encrypted backup; run capacity/connection preflight; start Redis/Agent; run migration service; wait for all healthchecks; verify both APIs directly and via Caddy, Redis, frontend, workers, scheduler, image SHA, revision, and safe queue polling readiness. Update deployed tag only after success. Roll back app tags only schema-neutral.

### Tests first
Missing replica, unhealthy worker, Redis/scheduler failure, wrong SHA, budget failure, schema-change rollback tests.

### Verification
sh -n ops/deploy-production.sh
sh -n ops/verify-production.sh
bash -n ops/backup-production.sh
python3 -m unittest discover -s ops/tests -p 'test_*.py' -v

### Expected result
CD succeeds only when whole topology is healthy.

### Failure/rollback concern
Never downgrade database automatically.

### Commit boundary
feat(cd): verify replicated production topology safely

### Definition of Done
Every service is verified and rollback guarantees remain.

## Task 30 — Add and execute release runbook

### Goal
Make first replicated release evidence-backed and reversible.

### Why now
All implementation and CI gates are complete.

### Inspect first
All task commits; latest heavy artifacts; backup config; VPS resources; deployed SHA; migration head.

### Files to create
docs/scalability-release-runbook.md.

### Files to modify
README.md.

### Do not modify
Production data, failing gates, real-provider load settings, or old volumes/images during first release.

### Implementation
Document preflight/deploy/observe/rollback. Require recent heavy success, at least 1 GB free memory, verified backup, successful CI, immutable SHA, and 30-minute observation. Record capacity baseline and rollback SHA.

### Tests first
Review commands against ops tests.

### Verification
git diff --check
git status --short --branch
python3 -m unittest discover -s ops/tests -p 'test_*.py' -v
docker compose -f compose.prod.yaml -f compose.observability.yaml config --quiet

### Expected result
The release is observable and reversible.

### Failure/rollback concern
If any gate fails, retain previous immutable tag and do not improvise a DB downgrade.

### Commit boundary
docs(operations): add scalability release runbook

### Definition of Done
Runbook, heavy evidence, backup, and post-deploy evidence exist.

## Acceptance gates

Local:

- Backend pytest/Ruff/mypy, frontend/mobile/shared/OpenAPI gates pass.
- Compose/Caddy/monitoring validate.
- Redis persistence/auth/private-network checks pass.
- Three APIs distribute traffic.
- API starts no scheduler.
- Body Analysis survives API/worker restart.
- Existing food-photo/outbox remains green.
- Cache/limiter fallback, pool budget, load thresholds, and failure drills pass.
- No paid provider or secret appears.

CI:

- PostgreSQL 18 and Redis integration pass.
- Ruff/mypy are required.
- Cache/rate-limit/queue/scheduler/health tests pass.
- Multi-replica smoke passes.
- Compose/Caddy/monitoring contracts pass.
- Immutable SHA publication depends on every required gate.
- Heavy load/failure workflow has recent success.

Production:

- Backup, migration revision, image SHA, both APIs, Caddy, frontend, Redis, workers, scheduler, and DB are healthy.
- DB/Redis remain private.
- Connection budget, cache ratio, queue age, 5xx/provider timeout rates, and worker readiness meet thresholds.
- Unhealthy replica removal works.
- Dashboards/log correlation are available.
- Previous SHA and rollback procedure are recorded.

Failure drills:

- Redis unavailable: cache falls back; limiter uses PostgreSQL; double failure fails closed.
- Worker killed: lease expires/reclaims without duplicate finalization.
- Backend replica killed: Caddy uses remaining ready replica.
- Queue backlog: oldest age and drain time remain within SLO.
- DB exhaustion: checkout times out and metrics alert.
- Caddy upstream failure: health checks stop routing to failed upstream.

## Environment variables

New operator settings: Redis host/port/db/pool/timeouts/maxmemory; cache TTLs/lock TTL; limiter fallback/policies; trusted proxy CIDRs; Body Analysis worker batch/poll/lease/retry/concurrency; worker shutdown/runtime probe; DB pool/timeouts/budget/application name; provider timeout/retry settings; health/deploy verification; Prometheus retention; Grafana bind/user; service/instance/log/metrics; edge subnet/Caddy address.

New secrets: REDIS_PASSWORD, RATE_LIMIT_HMAC_SECRET, GRAFANA_ADMIN_PASSWORD. Existing DB, AI, OAuth, SMTP/SMS, push, S3, encryption, and deployment secrets remain secret. Never commit .env.

## Capacity and deferred scaling

Tune backend replica profile, worker concurrency, pool sizes, Redis memory, and queue poll/batch values through environment/Compose operator configuration while preserving the connection budget.

Defer managed PostgreSQL, off-box Redis, extra VPS nodes, pgBouncer, Kubernetes, Kafka, RabbitMQ, Celery, service mesh, distributed tracing, cAdvisor/Loki/Tempo, and CDN changes. Adopt them only after measured CPU/memory, queue, DB, Redis availability, or media-egress signals justify the added operational complexity.
