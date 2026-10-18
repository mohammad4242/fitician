# Request tracing implementation plan

Goal: Extend unified diagnostics into an evidence-based web-only trace explorer.
Architecture: Add bounded span metadata to diagnostic_events, retaining the writer, privacy, identity, retention and issue pipeline. Use W3C traceparent plus correlation IDs; distinguish business and transport results.

1. Runtime/storage (main): additive span columns/indexes, nested timing, common request spans, bounded capture, sampling/drop evidence. Exclude spans from legacy metrics. Test success, errors, cancellation, nesting and privacy.
2. Nutrition (Luna): map persisted outcomes; time candidate construction, commit and serialization without changing generation semantics. Test HTTP 201 business failure.
3. Admin APIs (main): bounded explorer, latest span observations, deterministic Persian summaries, aggregate percentiles and explicit unknown/truncated outcomes. Test authorization, pagination and deduplication.
4. Web UI (Luna): primary traces tab, filters, nested waterfall, evidence, analytics, controlled polling, Persian/English, both themes. Focused rendering tests.
5. Correlation (main): client W3C propagation, database/dependency spans, Agent correlation, supported worker boundaries. Document coverage gaps.
6. Integration: focused checks, isolated migration verification, visual verification and combined review; allowlisted commits, push, established PR workflow. Merge approved changes only; no production mutation.

Review focus: HTTP 201 domain failures; client timeout with unknown backend outcome; missing parents/drops; async context isolation; SQL/body/credential privacy.

Status: Implementation and focused verification completed. Combined Luna technical review approved; no blockers. Migration upgrade/downgrade exercised only on the isolated local test database. Production rollout remains separate.
