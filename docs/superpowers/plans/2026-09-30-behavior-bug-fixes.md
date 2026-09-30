# Confirmed behavior bug fixes

**Goal:** Fix the seven confirmed audit findings approved by the user.
**Architecture:** Reuse existing safety decisions and adaptation constraints. Current
exercise prescriptions define aggregates. UI asynchronous work respects identity,
selected dates and calendar rollover; chat detects gaps before merging pages.
**Tech Stack:** FastAPI/SQLAlchemy, React, React Native, shared TypeScript Core.

- [x] Backend: reproduce weekly pain, blocked direct/PDF reads, removed muscle metrics;
  apply minimal corrections and run athlete-state, review and nutrition read checks.
- [x] UI: reproduce delayed refresh after logout/account switch and wrong/stale dates;
  guard identity and use a calendar clock refreshed at midnight/foreground.
- [x] Chat: reproduce disjoint latest pages; retain a recoverable pagination cursor
  and contiguous history on Web/Mobile, with shared behavior regressions.
- [x] Verify focused suites, lint/types/contracts/builds; review owned diffs, commit
  and push current branch. Preserve existing WIP. No deployment.

## Verification results

- Backend: 146 focused tests passed (behavior regressions, athlete state,
  workout reviews, weekly nutrition plan API). Changed Python files pass Ruff.
- Web: 53 tests passed across auth, nutrition workflows, conversation and calendar
  clock. Production build passed.
- Native: 22 tracking/conversation tests passed. Mobile TypeScript check passed.
- Core: all 120 tests passed; Core build passed. OpenAPI contract check passed.
- Regression coverage: weekly pain reaches blocked generation exercises and clears
  when withdrawn; unsafe ID/PDF reads return 409; removed muscle metrics become zero;
  stale refresh cannot overwrite logout/new account; selected-date writes match reads;
  midnight/foreground refreshes tracking; missing chat ranges remain pageable.
- Existing progression test now checks the engine's per-muscle cap against known
  positive prior volume instead of comparing a chest-only fixture to full-body totals.

## Verification limits

- Strict backend mypy is blocked by an unchanged return-type error in
  `app/workout_cycles/body_progress_service.py:266`, reproduced by checking that
  module alone. The three changed service/metrics modules pass with silent imports.
  A separate silent-import router check reports existing response/dict return typing
  issues; the router is not claimed type-clean.
- Web lint completes with two existing warnings in `webTransport.test.ts:150`
  and `WeeklyNutritionPlan.tsx:96`.
- Verification used the current workspace. Eight unrelated modified files were
  preserved byte-for-byte and excluded from commits. Full monorepo suites were not run.
- No deployment performed.
