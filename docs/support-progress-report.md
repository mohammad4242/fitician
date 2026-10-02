# Support Center and My Progress implementation report

Branch: `feat/support-progress`. Approved architecture: canonical records plus
measurement provenance and lifecycle/reschedule events. This is a source and test
report; production deployment and physical-device acceptance are separate.

## Architecture and modules

- `backend/app/support/`: separate ticket/message/read/status-audit domain;
  authenticated member ownership, existing admin authorization, mutation guard,
  rate limits, cursor pagination, transactional inbox/outbox and UUID retries.
  Support admins receive support content and troubleshooting metadata only.
- `backend/app/progress/`: bounded owner-scoped read model, authoritative metric
  semantics, date presets, product-mode visibility and bulk queries. No copied
  workout/nutrition/analysis records and no private media URLs.
- `backend/app/profile/measurements.py`: canonical explicit body observations and
  idempotent recording. Existing profile/shared-profile snapshot behavior retained.
- `backend/app/nutrition/lifecycle_history.py`: transactional effective-date
  observations referencing existing plan revisions; centralized existing calorie
  band in `adherence_policy.py`.
- Core `support.ts`, `progress.ts`, `public-contacts.js`, generated API and FA/EN
  resources share content, contracts, pure chart geometry and presentation copy.
- Public contacts ship from one shared source consumed by clients and release
  checks: `fitician.fit@gmail.com`, `@fitician.fit`, `/support`. No contact-config
  API is needed for this static v1 registry. This replaces the Phase 0 proposal
  for a backend configuration endpoint.

## Progress sources and exact semantics

| Metric | Canonical source | Formula / interpretation |
| --- | --- | --- |
| Goal / mode | `UserProfile` | Existing fitness goal and product mode |
| Current program / week | Active owned `WorkoutCycle`; started visible nutrition plan when no training cycle | Cycle week bounded to its duration; current-period range uses cycle start first, otherwise nutrition start; ranges capped at 366 dates with explicit clipping |
| Training planned | `WorkoutCycleSession.scheduled_date` | Owned sessions scheduled within selected dates |
| Training due | Same session records | Scheduled before today, plus completed/skipped today; pending today and future sessions excluded |
| Training adherence | Same session status | `100 × completed_due / due`, rounded to 1 decimal; null for zero denominator |
| Skipped / overdue | Same session status | Due skipped / due still scheduled; upcoming sessions are not overdue |
| Rescheduled | `WorkoutSessionRescheduleEvent` | Distinct explicitly requested sessions with events in the period; cascaded shifts retained in history but not counted as requests; unknown legacy coverage returns null |
| Self-reported strength | End-cycle feedback `strength_progress` | Localized self-report only; no inferred strength curve |
| Recovery / difficulty | Weekly check-in enums and submission times | Actual observations; one observation is a current state, two or more permit an ordinal trend |
| Weight | `BodyMeasurement.weight_kg` | kg; explicit observations or legacy changed values only |
| Waist | `BodyMeasurement.waist_circumference_cm` | cm; same observation semantics |
| Hip | `BodyMeasurement.hip_circumference_cm` | cm; same observation semantics |
| Shoulder width | `BodyMeasurement.shoulder_width_cm` | cm; exact width, never circumference/chest substitution |
| Body delta | Each typed measurement series | Latest minus first recorded value in selected period; null with fewer than two observations |
| Target calories | Immutable plan-day nutrient totals + effective lifecycle history | Recurring historical day index and actual effective revision; legacy pinned day evidence only when history is unavailable; otherwise null |
| Recorded calories | Consumption entry nutrient snapshots for `entry_date` | Sum only when every entry has valid finite nonnegative energy; missing/invalid totals remain null, never zero |
| Tracking coverage | Valid recorded calorie dates | Logged completed dates / all completed dates in selected range; today shown in progress and excluded from summaries |
| Comparable calories | Existing reliable-day rule | Past date, valid positive target, valid total, check-in other than `not_recorded`, all entries high-confidence and user-confirmed |
| Calorie alignment | Existing 80–120% band | `0.8 ≤ actual / target ≤ 1.2`; `100 × aligned / comparable`, rounded to 1 decimal; null with no comparable dates |
| Mean calorie difference | Comparable date-aligned pairs | Mean of `actual − target`; null without pairs |
| Mean target / actual | Historical series | Mean target on comparable dates; mean recorded actual on all valid completed logged dates; denominators intentionally differ and these averages are not subtracted |
| Body Analysis | Owned photo-session/result metadata; existing history/comparison services | Existing estimated visual assessments retained; no conversion into canonical measurements |
| Insights | Authoritative counts/deltas and shared deterministic copy | Factual summaries; no LLM filler or medical claims |

Reliable logging does not prove complete daily intake. The UI labels recorded
calories and explains the existing product rule. Missing dates break chart paths;
only actual measurement points are plotted. Legacy copied snapshot values are not
new observations. Legacy repeated equal measurements cannot be recovered safely.

## Migrations

| Revision | Addition |
| --- | --- |
| `20261002_166` | Private support tickets, messages, read state and status audit |
| `20261002_167` | Exact shoulder width, observed fields and observation request identity |
| `20261002_168` | Nutrition plan lifecycle history; conservative migration-date baseline |
| `20261002_169` | Real workout reschedule history and explicit legacy coverage start |

All new schemas have upgrade/downgrade and model-contract tests. Historical gaps
are intentionally preserved, without fabricated backfills.

## APIs

- Member: `GET/POST /api/v1/support/tickets`; `GET /{id}` and `GET /{id}/messages`;
  `POST /{id}/messages`; `PUT /{id}/read`.
- Admin: matching list/detail/messages/read under `/api/v1/support/admin/tickets`;
  `PATCH /{id}/status`; filtered activity queue with open count.
- Progress: `GET /api/v1/progress/overview?preset=week|four_weeks|current_program&timezone=...`.
- Measurements: `POST /api/v1/profile/body-measurements`, UUID retry identity;
  profile input/output also supports exact shoulder width.
- Generated OpenAPI/Core contracts updated. Public Help is bundled structured
  content; no anonymous ticket endpoint.

## Web and Mobile

Web `frontend/src/features/support/` provides public `/support`, member list/create/
thread and Web-only admin workspace. More/header show only approved contacts.
`frontend/src/features/progress/` provides `/progress`, summary cards, selectable
body trend, calorie target/recorded series and details, training/recovery and lazy
existing Body Analysis history/comparison components.

Mobile `mobile/support/` mirrors member support. `mobile/progress/` mirrors the
read-model semantics and uses compact cards with collapsed secondary details.
Five configured primary destinations are Today / Training / Nutrition / Progress /
More; existing capability-based visibility is retained. The old Body Analysis tab
is hidden as a compatibility route, and capture/history/results/deep links remain.
Support and Progress share a persisted FA/EN presentation preference. Existing
legacy flows keep their current behavior.

Support reply notifications reuse the transactional notification architecture and
push delivery workers; Web inbox, Mobile inbox/push and cold-start/app links open
validated ticket destinations. Safe metadata contains platform/version/build/locale,
with no automatic photos, labs or health data. Retry metadata is frozen per intent.
Account changes clear private screen state immediately.

## Verification status

- Core: 127 tests after the categorical-axis regression.
- Web: 1,203 tests after final polish.
- Mobile logic: 619 tests; native rendering: 367 before final account regression,
  plus focused final feature regressions.
- Chromium and WebKit: 8 FA/EN Support/Progress checks at 320px and 1440px; screenshots reviewed.
- Core/Web builds, Web/Mobile typechecks, affected strict backend mypy/Ruff,
  Web lint, OpenAPI reproducibility and tracked secret scan passed.
- Mobile foundation/release-config tests: 61 passed.
- Broad affected backend suites: 1,328 passed; final Progress/migration/privacy/query-budget suite: 22 passed. The fresh-session 28-day overview stays within 20 SQL statements and excludes large plan snapshots.
- Final CI remains required and blocked by the dependency decision below.
- Initial full CI identified the WebKit fixture/service-worker interception issue;
  the fixture now blocks service workers and both browsers pass locally.
- Dependency CI is blocked by upstream `node-forge` advisory
  [GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv), inherited
  through Expo. The advisory and npm registry currently provide no patched release.
  The security gate remains unchanged; dependency strategy awaits user selection.

## Intentional v1 exclusions

Optional support attachments and assignment, article CMS, anonymous ticket creation,
set-by-set logging, clinical inference, fake historical backfills and LLM insights.
Production deployment, store publication and physical-device acceptance are not
part of this source implementation report. Full Definition of Done remains open
until final required CI is green.
