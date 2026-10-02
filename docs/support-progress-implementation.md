# Support and Progress implementation ledger

Approved specification: `docs/support-progress-phase0.md`, option 1.
Execution: main agent, autonomous through phases 2–11; preserve unrelated WIP.

- [x] Phase 1: Support domain/API/security; commit `ebf53598`, 66 backend tests.
- [x] Phase 2: Shared Help registry/search/API; public Web Help and member Web/Mobile ticket list/create/thread; More entry points; focused Core/Web/native rendering tests.
- [x] Phase 3: Web admin queue/search/status/reply, authorization rendering tests.
- [x] Phase 4: Canonical public contact config, placeholder removal, Web/native notification and app-link routing; release metadata validation.
- [x] Phase 5: Owner-scoped Progress overview context/ranges/product modes; bounded aggregate services and generated contract.
- [x] Phase 6: Exact shoulder width and explicit measurement provenance; observation series with truthful legacy coverage; Web/native profile inputs.
- [x] Phase 7: Durable nutrition activation history and date-correct target/actual series; null intake and shared authoritative adherence.
- [x] Phase 8: Web Progress hero/cards, selectable body chart, calorie chart, training/recovery/analysis/insights; rendering tests.
- [ ] Phase 9: Mobile equivalent; replace tab while retaining Body Analysis routes; native rendering and navigation tests.
- [ ] Phase 10: Durable reschedule events, deep links, accessibility, RTL/LTR, responsive/browser review, bounded queries and empty states.
- [ ] Phase 11: Combined regression review, affected backend suites/Core/Web/native tests, lint/typecheck/build, migration/OpenAPI contracts, final CI.

Each phase uses focused red/green tests, named staging, Conventional Commit and push.
Full affected verification occurs when the feature is coherent. No production deploy/store publication.
Approved public support email: `fitician.fit@gmail.com` (user confirmed).
Phase 2 verification: Core shared search/API 3 tests; Web Help/tickets 5 tests; Mobile Help/tickets/retry 3 native tests; Web and Mobile typechecks; focused Web lint.

Phase 3: admin-only routes, filtered/paginated queue, safe ticket thread and status controls. No profile/health API calls.

Phase 4: single public contact registry consumed by Core and release checks; approved email and Instagram; placeholder social accounts removed; validated UUID ticket destinations for Web/native inbox, push and app links. Core 4 tests, native routing 14 tests, store source 6 tests, Web communication/support 14 tests, both typechecks.

Phase 5: authenticated Progress overview, bounded date presets, product-mode visibility, scheduled/due training denominator, actual weekly check-ins and metadata-only latest Body Analysis. Six backend tests, strict module mypy and Ruff, generated contract checks. Nutrition/body sections are populated in phases 6–7.

Phase 6: canonical `shoulder_width_cm`, per-snapshot explicit observation fields and retry identity; profile measurement API; legacy changed-value series excludes carries and never substitutes shoulder circumference. Shared-profile weight changes preserve other measurement snapshots. UI registration is integrated into Progress in phases 8–9. Backend profile+Progress 176 tests, then 10 focused Progress/migration tests after retry hardening; strict mypy/Ruff and Core build.

Phase 7: transactional SQLAlchemy lifecycle observations for all existing ORM plan transitions; safe legacy baseline from migration time; date-only pinned legacy evidence; recurring day index from historical start; confirmed/high-confidence 80–120% band centralized with existing review logic. Invalid/missing intake remains null. Today is in progress and excluded from completed-day metrics. Fourteen Progress/migration tests, strict mypy and Ruff. After transaction-ordering and timezone fixes: all 14 Progress tests and 24 nutrition review/editing regression tests passed. Full affected nutrition suites remain required for phase 11.

Phase 8: Web `/progress` and navigation; shared pure chart geometry preserves null gaps and observed timestamps; body selector and explicit measurement form; calorie target/actual tooltip and day control; due-training/recovery summaries; lazy existing Body Analysis page embedded with its full comparison/capture/delete behavior. Core geometry/API tests and 57 Web route/navigation/analysis/Progress tests passed; focused typecheck/lint.
