# Unified diagnostics

The internal dashboard is `/admin/diagnostics` (لاگینگ و دیباگینگ). It requires the existing admin role. Member screens and navigation are unchanged.

## Data flow and boundaries

- Existing `X-Correlation-ID`, structured logs, private metrics, entitlements, generation records, and outbox remain canonical.
- Web/PWA and Expo submit a closed authenticated telemetry batch. The server derives identity, severity and taxonomy. The body is limited to 16 KiB and ten events; ingestion allows 30 requests/minute/user. Component, workflow and stage labels are closed enums.
- API middleware records terminal outcomes; generation stage markers form a correlated timeline. Engine failures before a generation row exists are included. Existing generation diagnostics remain in their existing private domain records.
- A process-local queue holds at most 256 events. Maintenance uses a separate transaction so a cleanup failure does not roll back an already recorded event. One writer thread uses one dedicated database connection with a 100 ms pool wait, two-second connect timeout and two-second statement timeout. Saturation drops telemetry instead of blocking operations.
- SQLAlchemy failures in a request emit structured fallback logs rather than nested diagnostic writes. Observability errors cannot replace the original operation result.
- Worker error logs forward only fixed codes, component names, exception class and sanitized source locations. Bounded reconciliation also observes existing durable failed jobs and dead letters, including across restarts.
- Admin infrastructure probes distinguish reachability from successful business execution. API/DB/Redis/Agent/media probes and queue counts are actual observations; worker process/restart health remains unknown without an observed signal.

## Storage and diagnosis

The additive migration creates `diagnostic_events`, `diagnostic_issues`, `diagnostic_alerts`, `diagnostic_status_history`, and `entitlement_quota_reservations`. Indexed correlation, issue, time, operation and resource lookups support bounded pagination. A second additive migration adds nullable hashed request-key columns and partial unique indexes to existing generation/bundle tables; existing rows remain unchanged.

Event UUIDs deduplicate retries before issue counters change. Fingerprints exclude user/request/version IDs. Resolved recurrences reopen issues and increment regressions. Expected authentication, quota, business, input and safety rejections do not create actionable issues or alerts.

Confidence defaults to **unknown**. A trusted `ZeroDivisionError` with a sanitized code location confirms that specific technical failure only, not a wider business cause. Client reports cannot set confidence or exception evidence. Other causes require investigation; notes and status history preserve admin decisions.

One new critical issue or five repeated errors within ten minutes creates an internal alert, with a one-hour per-issue cooldown. Alerts remain usable without email, push or international access.

Overview/chart/platform aggregates use all retained terminal events in the selected window. They describe recorded observations; queue drops mean they are not an exhaustive traffic audit. Generation metrics separate reuse, failures, blocked attempts and pending review. Starts without a terminal observation after thirty minutes are labelled **outcome unconfirmed**, without changing plans or charging quota.

## Privacy and retention

No request bodies, raw error messages, prompts, medical forms, credentials, screenshots, private media or session recordings enter diagnostics. Stack evidence is a bounded source basename and line. Client free text and server-owned fields are rejected. JavaScript exception types come from a fixed allowlist; source evidence is only a hashed web bundle or native bundle basename with numeric line/column, never a URL, local path, message or raw stack. Client evidence remains unverified and cannot confirm root cause. Admin notes are internal and must contain no secrets.

Client event times are server receipt times; an offline report can arrive later than its original failure. Correlation IDs link it to earlier server evidence.

Client queues hold at most thirty safe events, deduplicate for sixty seconds and retry three times with backoff. They clear on account changes/logout. Web retries on reconnect; native delivery flushes through the existing connectivity monitor when connectivity returns. Queues live in memory and do not survive process termination. Identity comes from authentication at delivery, never from submitted user IDs.

Raw events expire after thirty days; issue summaries, status history and alerts after ninety days. Maintenance runs hourly and after every hundred writer events; ingestion also prunes. Soft volume caps are 100,000 events and 10,000 rows per aggregate/history table, pruned in bounded batches. A burst can exceed a cap until the next maintenance batch. User deletion anonymizes diagnostic user references with `ON DELETE SET NULL`; entitlement reservations cascade with the user.

## Generation charging

Workout and nutrition each allow three new successful plans per rolling seven days, independently. Existing admin exemptions and unrelated subscription/review products remain unchanged.

Persistence, usable lifecycle transition and final charge share a transaction. Quota accounting locks the user row and deduplicates resource keys. Workout persistence rechecks the semantic reuse signature under that same lock. Optional `Idempotency-Key` headers are SHA-256 hashed into unique per-member indexes on existing successful workout generations and nutrition bundles. Failed transactions do not retain a key or charge; changed or ineligible outcomes return 409 instead of generating again with that key. Web and native transports retain bounded in-memory keys across ambiguous network/5xx failures and clear them on definitive responses/authentication changes. Restarted clients still benefit from semantic input reuse. Nutrition now also hashes normalized inputs, safety policy, current catalogue, templates and engine policy for safe unchanged-plan reuse. Unconsumed generated meal history does not invalidate reuse. Rejected, invalidated, expired or medically incompatible outcomes are ineligible.

Pending professional review reserves capacity rather than charging successful usage. A successful approval finalizes that resource reservation atomically. Rejection/supersession releases it. Reservations count within the seven-day admission window; delayed approvals recheck current capacity. Existing professional-review submission limits remain in effect, preventing unlimited submissions. Legacy plans without a new reservation are not charged again at approval.

A valid direct nutrition bundle is immediately selectable and costs one generation for both candidates. Physician candidates remain reservations until approved. Failed construction, rollback, unsafe output, unchanged reuse and retry cost zero additional quota.

## Configuration and operational limits

- `DIAGNOSTICS_ENABLED=false` disables capture without removing admin history.
- Backend `APP_BUILD_SHA` and frontend `VITE_APP_BUILD_SHA` tag immutable builds; Android includes its native version/build number. Unknown versions stay unknown.
- Each enabled API/worker process adds at most one diagnostics connection; include these in the production connection budget.
- Native Java/Kotlin/Objective-C fatal crashes, signals and crashes before JavaScript startup are not reliably captured by this provider-neutral implementation. Expo's existing adapter exposes no configured native crash backend. React Native promise rejections are captured only where the runtime exposes a supported existing global handler. Preserve release source maps, R8 mappings and symbols; do not claim full native crash coverage.
- Anonymous pre-login failures are captured on the backend. Authenticated ingestion deliberately does not accept anonymous client telemetry.
- The system does not collect native tombstones, host kernel logs, or infer process crash counts from queue depth. A database outage leaves structured logs rather than durable DB diagnostic events until recovery.

## Release safeguards

Keep regional GitHub Actions CD disabled. Review the additive migration and test upgrade/downgrade on isolated PostgreSQL. Before production migration, take and restore-verify a fresh backup. Transfer exact-SHA images with `docker save`, SSH and `docker load`; use `--pull never` and preserve active Compose volumes, secrets and unrelated services.

Rollback the frontend independently with additive tables retained. Prefer disabling diagnostics capture and rolling forward for backend incidents. Before reverting backend images to older quota logic, freeze generation/review writes and reconcile any new pending-review reservations; older review code cannot finalize them correctly. Do not downgrade/drop diagnostic tables or restore an older production database after new writes. A schema/data recovery needs a write freeze and reconciliation. Keep the backup and previous image IDs until production smoke checks pass.

## Request traces (2026-10-18)

The primary **Request Traces / ردیابی درخواست‌ها** tab is available only at `/admin/diagnostics`. Android and installed PWA are sources; no native admin screen was added. The waterfall uses recorded spans, separate elapsed-clock lanes, expandable evidence and explicit incomplete/unknown states. Persian stage names retain technical identifiers. A yellow completed bar means an observed duration of at least 2 seconds, not a confirmed performance regression. Polling is opt-in every 15 seconds and pauses while hidden.

### Capture and schema

Migration `20261018_175` (parent `20261017_174`) adds columns to the existing `diagnostic_events` table:

- `trace_id` (32 lowercase hex), `span_id` / `parent_span_id` (16 hex), `record_type` (`event` or `span`). Existing rows remain events with null trace metadata.
- `started_at`, `ended_at` (nullable UTC), monotonic `duration_ms` and `offset_ms`, `clock_domain`.
- `origin_platform`, `app_version` (self-reported client metadata), `expected_span_count`, `dropped_count`. Existing `version` remains available for engine versions; immutable build tags remain unchanged.
- Existing request/operation/user references, HTTP status, retry count, sanitized exception type/source basename:line and issue linkage remain canonical. No bodies, SQL text/parameters, private media, auth values or raw exception messages are captured.

Each span has an entry and, when observed, an exit event with the same span ID. The detail reducer prefers a terminal observation over a delayed start replay. Existing event UUID deduplication prevents ingestion retries from changing issue counts. Legacy overview/generation metrics exclude `record_type=span` so child spans do not inflate request totals. New analytics use retained trace-level denominators and latest worker attempts per durable resource.

W3C `traceparent` version 00 is validated (zero IDs are invalid). Web/native requests create a span and preserve `X-Correlation-ID`. Backend responses expose `traceparent` and `X-Operation-ID`; backend sampling controls its sampled flag. Agent Service accepts/returns correlated context and logs bounded trace identifiers in its existing allowlist. Backend Agent adapter spans cover observed HTTP calls; Agent runner/provider internals remain available through correlated Agent logs, not fabricated central spans.

Backend and worker timing uses `perf_counter`; UTC timestamps are presentation metadata. Client dispatch/terminal durations use the device monotonic clock. Client timestamps in the dashboard are **server receipt times**, not inferred device wall-clock start/end. Separate clock domains must never be aligned as though device/server/worker clocks were synchronized. Cross-domain parents express structure only.

### Observed coverage

| Operation | Instrumented observations | Limits |
| --- | --- | --- |
| API requests | Backend receipt/completion or interruption; FastAPI validation/dependencies, endpoint business execution, response preparation; actual auth dependencies when entered | Diagnostics ingestion/admin reads and health/metrics probes excluded to avoid self-observation; skipped stages are not invented |
| Registration/login | Auth service boundaries, password authentication, session/token issuance, actual DB calls/commit | OAuth/OTP provider internals remain partial; a transport success alone does not prove a persisted business result |
| Profile/onboarding | Create/update/shared profile boundary, DB execution/commit | Per-field validation details intentionally excluded |
| Workout generation | Existing meaningful stage transitions now timed; engine/provider, persistence, activation/review, quota and commit | Engine sub-algorithms without explicit spans remain inside their observed enclosing stage |
| Nutrition generation | Entitlement, safety, profile, estimate, dietary/catalogue, budget/program selection, reuse/quota, construction, comparison, consistency, persistence, activation/review, quota, commit and serialization when entered | Branch-specific stages only; candidate `plan_week`, budget and ideal calls have bounded child spans; no production bottleneck is asserted from static code |
| Nutrition tracking | Check-in, catalogue/quick/free-meal persistence, entry edit/delete; DB observations | Fine-grained nutrient calculations remain inside the service span |
| Access/subscriptions | Entitlement/quota checks, consumption and package-grant boundaries | Payment-provider internals remain partial |
| Upload/media | Standardized upload, store/validation and concrete private-storage read/write/delete boundaries | Streaming body transfer has a request completion span; object-store internals are not separate spans |
| Body/food-photo workers | Durable scheduling parent, worker execution, attempts, provider calls and DB observations when new trace metadata exists | Existing pre-migration jobs have no invented trace link |
| Notifications | Durable outbox parent, delivery execution/attempts and existing failure reconciliation | FCM/APNs network/provider internals remain enclosing delivery work |
| Redis/PostgreSQL | Cache/rate-limit Redis calls; DB connection acquisition, SQL execute, commit and observed rollback | Connection acquisition combines pool wait/connect; it is not a claim of isolated pool wait. Rollback marker observes completion, not full rollback latency |

Job tables `body_analyses`, `nutrition_food_photo_analysis_jobs`, and `notification_outbox_events` receive nullable `trace_id`, `trace_parent_span_id`, and `trace_operation_id` columns. These propagate without changing claim, lease, retry, idempotency or entitlement semantics. Worker success/failure/pending state is shown separately from HTTP transport; the latest observed retry supersedes older attempt outcomes. Missing worker start or completion remains unconfirmed. Queueing a job does not verify its intended result.

### Business outcomes and diagnosis

Nutrition's HTTP 201 contract is preserved. Persisted `failed`, `safety_blocked`, `infeasible`, `target_infeasible`, and `live_price_unavailable` results produce non-success diagnostic outcomes after commit. The actual decision stage is retained; successful serialization is not relabeled as failed. Review, reuse and success remain distinct. A matching persisted workout/nutrition resource is queried before the summary marks persistence confirmed; other operations remain unknown unless explicitly verified.

Deterministic Persian summaries identify observed/successful/failed stages, technical evidence, persistence and a recommended investigation. Observed exception type/location confirms that observation, not a wider root cause. Insufficient evidence states **“The exact root cause has not yet been determined.”** A client transport timeout never independently changes the backend business result to failure.

### Admin APIs

All endpoints inherit existing `require_admin` authorization:

- `GET /api/v1/admin/diagnostics/traces`: `user_id`, `trace_id`, `request_id`, `operation_id`, `platform`, `component`, `operation`, `outcome`, `error_code`, timezone-aware `since` / `until`; `sort=newest|slowest|failed`; `limit=1..100`, `offset=0..10000`. Returns `{items, limit, offset, has_more}`. Default window: 24 hours.
- `GET /api/v1/admin/diagnostics/traces/{trace_id}`: `{trace, spans, summary, related_issue_ids, truncated}`. At most 2048 event observations are reduced; truncation is explicit.
- `GET /api/v1/admin/diagnostics/trace-analytics?hours=1|24|168|720`: retained request totals, business/worker-aware success/failure/incomplete counts, stage P50/P95, operation affected-user counts, platforms, trends and capture state. `capture` counters are **process-local**, not a fleet-wide loss total.
- Existing `POST /api/v1/diagnostics/client` additionally accepts closed `CLIENT_REQUEST_OBSERVED` events at `dispatch`, `response_received`, or `transport_failed`, with validated trace/span/parent/operation IDs and bounded monotonic timing. Identity, taxonomy, record kind and clock domain are server-derived. Existing batch/rate/privacy bounds still apply.

### Bounds and operations

`DIAGNOSTICS_SUCCESS_SAMPLE_RATE` defaults to 1.0 (0..1); successful high-volume backend traces may be sampled by trace ID. Failed/non-success and requests slower than `DIAGNOSTICS_SLOW_REQUEST_MS` (default 2000) retain bounded buffered evidence even when initially unsampled. Clients independently sample successful request telemetry at 10% by default and retain error observations. Anonymous pre-login client telemetry still requires authenticated delivery and may be absent.

Each execution retains at most 96 child spans, reserving 32 for explicit business/common stages and limiting repeated database/Redis observations to 32; skipped spans increase `dropped_count`. Unsampled buffers hold at most 256 observations; the existing writer queue remains capped at 256. Saturation prioritizes terminal non-success events by discarding a queued observation. Writer persistence failures increase a process-local drop counter. Missing expected spans, missing end records, queue loss and retention truncation are not success evidence. The existing 30/90-day retention and table caps apply to these same rows. Start/end span observations increase event volume; budget retention and one writer connection per enabled process accordingly. Capture still fails open and adds no infrastructure service.

Production is not changed by a commit. Before deploying: restore-verify a fresh regional backup, review additive schema/lock budget, apply `20261018_175` before backend/worker code, retain exact rollback images, and verify API/admin/worker samples. Keep regional CD disabled. Older images ignore the additive columns, so application rollback can retain them. Do not downgrade/drop tables or trace columns after new writes as a production rollback shortcut. Isolated-test downgrade/upgrade verification is required; production downgrade requires a write freeze and explicit recovery plan.

Transport failures additionally accept the closed `transport_kind` (`network`, `timeout`, `aborted`, `offline`, `unknown`). The server maps known timeouts/cancellations accurately; a missing kind remains a generic transport failure. Web terminal trace observations preserve canonical `API_REQUEST_FAILED` issue grouping through a deterministic deduplicated companion event. Native transport continues its existing canonical error event with trace metadata. Neither transport records diagnostics-page traffic.
