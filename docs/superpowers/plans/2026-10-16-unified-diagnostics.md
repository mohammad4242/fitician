# Unified Diagnostics Implementation Plan

**Goal:** Deliver the requested private diagnostics system, correct generation charging, and validated offline Iran deployment.
**Architecture:** Extend existing structured logging and correlation IDs. PostgreSQL stores bounded diagnostic issues/events/alerts/history. Authenticated clients submit a restrictive allowlisted contract; all diagnostic reads and mutations require admin authorization. Member screens remain unchanged.
**Execution:** User-authorized continuous SOL supervision with Luna handling client delivery and diagnostic CRUD; SOL owns transaction correctness, integration, dashboard, security review, release gates.

## Constraints
- No SaaS dependency, sensitive input capture, screenshots, arbitrary client messages, or public diagnostic reads.
- Independent 3 new workout and 3 new nutrition plans per rolling seven days.
- Persistence, usable lifecycle, and charging must share a transaction; pending reviews reserve capacity without charging.
- Idempotent retries and eligible unchanged-plan reuse; never reuse invalid, expired, revoked, or medically unsafe plans.
- Diagnostic failures cannot fail business operations. DB failures use structured fallback logs.
- Preserve unrelated untracked workspace files. Explicit Git file allowlists. No CD enablement or store publication.

## Tasks
- [ ] Durable diagnostic models, strict taxonomy/contract, atomic issue grouping, regression handling, alerts and bounded retention; PostgreSQL tests.
- [ ] Quota limit tests, transaction and concurrency regression tests; review reservations and lifecycle charging; input-based reuse/idempotency.
- [ ] Request/exception and workflow-stage capture, jobs and infrastructure observations, abandoned-attempt detection; failure isolation tests.
- [ ] Web/PWA and native bounded telemetry queues, sanitization, authenticated delivery, transport/global runtime hooks; focused client tests.
- [ ] RTL/localized admin overview, issue filters/details/timelines, events, generation and infrastructure views, alerts/status/history; frontend/browser tests using persisted events.
- [ ] Alembic migration review and upgrade/downgrade, API contract generation, focused lint/typecheck/integration tests; final security and concurrency review.
- [ ] Focused commits/push, protected merge and exact SHA; build images, verified restorable production backup, offline image transfer and compatible migration/deployment; authenticated smoke tests.
- [ ] Signed versioned Android artifacts and validation; release limitations and concise Persian evidence report.

## Review focus
Test concurrent retries, commit ambiguity, obsolete medical context, rejected reviews, client-forged fields, telemetry recursion, unavailable DB, unbounded filters, issue recurrence, and deletion of diagnostic identities. Metrics without a valid denominator remain unknown. Reachability never implies successful business execution. Deployment and Android claims require fresh evidence.
