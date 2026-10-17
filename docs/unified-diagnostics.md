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

No request bodies, raw error messages, prompts, medical forms, credentials, screenshots, private media or session recordings enter diagnostics. Stack evidence is a bounded source basename and line. Client free text and server-owned fields are rejected. Admin notes are internal and must contain no secrets.

Client event times are server receipt times; an offline report can arrive later than its original failure. Correlation IDs link it to earlier server evidence.

Client queues hold at most thirty safe events, deduplicate for sixty seconds and retry three times with backoff. They clear on account changes/logout. Web retries on reconnect. Queues live in memory and do not survive process termination. Identity comes from authentication at delivery, never from submitted user IDs.

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

Rollback application images with the additive tables retained. Do not downgrade/drop diagnostic tables or restore an older production database after new writes. A schema/data recovery needs a write freeze and reconciliation. Keep the backup and previous image IDs until production smoke checks pass.
