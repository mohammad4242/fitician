# Support Center and My Progress: Phase 0

Date: 2026-10-02. Inspected commit: `259817ef` on `main`.
Status: repository audit complete; architecture below is proposed, awaiting selection.
This document does not claim implementation, passing feature tests, or runtime acceptance.

## Repository findings

- Web member routes live in `frontend/src/App.tsx`; `DashboardPage`, `MorePage`,
  `AuthenticatedHeader`, and `AppShell` own member entry points. No Support or unified
  Progress destination exists. The header includes generic Instagram, Telegram,
  Facebook, and X links.
- Mobile configures Today / Training / Nutrition / Body Analysis / More in
  `mobile/app/(member)/member/(tabs)/_layout.tsx`. `MemberBottomTabBar` also defines
  order and icons. Training/Nutrition can be hidden by product capability.
  This verifies source configuration, not a running handset.
- `WorkoutCycleSession` persists scheduled/completed/skipped states and terminal
  timestamps. Rescheduling shifts unfinished sessions in place; there is no durable
  old-date or reschedule-event history. Weekly check-ins contain difficulty and
  recovery enums. End-cycle feedback and AthleteState are separate existing sources.
- `BodyMeasurement` in `backend/app/profile/models.py` is the canonical historical
  source for weight, waist circumference, hip circumference, and shoulder
  circumference. **Shoulder width does not exist.** Existing profile controls collect
  shoulder circumference; they must keep their current meaning.
- Profile updates copy unchanged measurements into newly dated snapshots. Therefore
  treating every non-null column on every row as a fresh observation is incorrect.
  Shared-profile weight writes also require inspection during the provenance change.
- Nutrition persists consumption nutrient snapshots, entry dates, confidence,
  confirmation, daily check-ins, and pinned plan revision IDs. Plans contain recurring
  seven-day nutrient totals, lineage/revision, `start_date`, `started_at`, and lifecycle.
- `effective_nutrition_plan_for_date` resolves currently ACTIVE plans by start date
  and revision. It is useful for live scheduling, but is not a complete temporal
  archive. Revisions can retain an earlier start date and plans can become archived.
  A historical chart cannot blindly call the current resolver for every old date.
- Two nutrition metrics already exist: the continuous calorie score in
  `adherence_service.py`, and reliable-day 80–120% calorie alignment in
  `progress_review.py`. The latter currently compares against the current plan.
  Reuse its rule, but resolve historical targets separately and correctly.
- Body Analysis already has capture, results, private media, timeline, specialist
  reviews, and versioned comparisons on both clients. Its visual assessments are
  not numeric clinical circumference/width observations. Do not convert them.
- `BodyProgressHistoryService` bulk-loads histories and photo references. The overview
  should use a bounded metadata projection, not load this entire timeline or media.
- Notifications already have a transactional outbox, deduplication, inbox, preference
  filtering, FCM/APNs, and routing. New events need content/preference integration
  as well as both inbox and native notification routing.
- Program conversations are review-specific, with sender/request uniqueness,
  deterministic ordering, read state, cursor pagination, and participant checks.
  Reuse patterns only; create a separate support domain.
- Admin authorization is `require_admin`; authenticated writes use the existing
  mutation guard. The Redis rate limiter is available for authenticated abuse limits.
- Shared Core owns transport, generated OpenAPI types, FA/EN resources, formatting,
  local-date logic, entitlement contracts, and Body Analysis contracts.
- Existing Web CSS tokens and Mobile `fiticianTokens` cover the requested petrol,
  aqua, typography, surfaces, spacing, radii, and accessibility sizes. SVG is already
  used for trends, and Mobile already depends on `react-native-svg`.
- Store metadata references `FITICIAN_SUPPORT_URL` and `FITICIAN_SUPPORT_EMAIL`.
  No real approved support email was found in tracked configuration. Instagram
  `@fitician.fit` is supplied by this request. Do not invent an email address.
- Local Alembic head is `20260929_165`, verified with `uv run alembic heads`.
  CI routes changes into backend, frontend, shared, mobile, browser, Android,
  contract, security, and release checks. Native store releases have separate gates.
- Tracked worktree was clean. Existing untracked artifacts and a regression test are
  unrelated work and must remain unstaged and untouched.

## Proposed architecture

1. `backend/app/support/`: separate tickets, messages, read state, status audit;
   member ownership queries and Web-only admin endpoints. Authenticated access is
   independent of paid entitlements and profile completion, so account problems can
   be reported. Public Help is read-only; there is no anonymous ticket endpoint.
2. Shared Help content registry in Core: stable article IDs, category, FA/EN title,
   keywords, content, and search normalization. No CMS. Public contact config is
   backend-owned and returned through a public configuration endpoint; store
   readiness tooling validates those same public values. Default support destination
   is the configured public origin plus `/support`, required HTTPS in production.
3. `backend/app/progress/`: bounded, owner-scoped read projection. No copied workout,
   nutrition, or Body Analysis domain tables. Backend returns context, visibility,
   denominators, series, latest analysis metadata, recovery, and deterministic insight
   codes/parameters. Core shares transport and localization; clients do presentation.
4. Minimal canonical additions: nullable `shoulder_width_cm` plus per-metric
   observation provenance/timestamps in the profile architecture; durable nutrition
   activation/effective-date events that reference immutable plan revisions; durable
   session reschedule events that reference sessions. These preserve missing history
   rather than reconstructing it from today's state. No numeric data duplication.
5. Web `/progress`; Mobile replaces the Body Analysis primary tab with Progress.
   Preserve legacy Body Analysis routes through a hidden compatibility route and
   existing capture/history/result routes. Five configured primary tabs remain;
   existing capability visibility remains in force.
6. Summary first, compact cards, one selectable body chart, two-line calorie chart,
   compact training/recovery, collapsible Body Analysis/details. Reuse existing
   timeline/comparison components in details. Chronological chart axes remain
   chronological in RTL; labels, navigation, and layout follow FA/EN direction.
   SVG point and segment geometry uses actual times and values; missing intake
   breaks the actual line. No smoothing that suggests unrecorded intermediate values.

### Progress sources and formulas

| Metric | Authoritative source | Proposed semantics |
| --- | --- | --- |
| Goal/program/week | Profile, selected started nutrition plan, active workout plan/cycle | Separate training/nutrition context when periods differ |
| Training | Owned cycle sessions, current schedule, completion/skip timestamps | Due = elapsed scheduled dates plus resolved sessions today; completed/due × 100, null when due=0; upcoming excluded |
| Planned week | Owned session schedule | Scheduled total shown separately from elapsed-session adherence |
| Rescheduled | New forward-only session events | Count affected sessions; historical unknown remains unknown |
| Tracking coverage | Consumption entries with valid recorded calorie values | Logged days / elapsed calendar days; today shown separately as in-progress |
| Calorie actual | Sum of valid consumption energy snapshots per local entry date | Null with no entries or invalid calorie coverage; never default missing to zero; recorded partial intake labeled as recorded intake |
| Calorie target | Pinned daily revision, then recorded activation/effective interval | Actual recurring day total; reference revision/source returned; unresolved or conflicting historical targets remain null |
| Reliable calorie alignment | Existing progress-review rule, with date-correct targets | Valid check-in, all entries high-confidence and user-confirmed; 0.8 ≤ actual/target ≤ 1.2; positive valid target required; aligned/comparable reliable days × 100 |
| Continuous calorie score | Existing adherence formula, separately named | max(0, 100 − abs(actual−target)/target × 100), only for comparable data |
| Mean calorie difference | Date-aligned actual/target pairs | mean(actual−target); averages use the same paired-day denominator; null with no pairs |
| Weight / waist / hip | Canonical explicit BodyMeasurement observations | kg / cm / cm; latest−first within selected range; at least two comparable points |
| Shoulder width | New canonical explicit width observation | cm; no backfill from shoulder/chest circumference |
| Recovery/difficulty | Weekly check-ins | Ordinal self-report; latest with one observation; trend only with at least two; reuse existing enum ordering |
| Body Analysis | Owned current result versions and comparisons | Visual/estimated source labeled; no media URLs in overview |

The 80–120% band is an existing product rule, not a new scientific claim. Reliable
logging does not prove a complete day's intake. Do not describe partial food logs as
total consumption or mix this metric with self-reported plan compliance.

Ranges: this local week, rolling 28 calendar days, current period. Week starts follow
the shared Fitician calendar. Resolve server-side timezone and return actual boundaries.
Current-period response provides separate domain start dates and comparable-day coverage.
Today may appear in series but is excluded from completed-day nutrition classification.
Older uncertain measurement snapshots keep legacy provenance; carry-forward fields are
not fresh observations. Repeated explicit observations remain valid in future writes.
Historical gaps cannot be repaired by invented backfills.

### Support contract

- Categories: technical, account, billing, workout, nutrition, body_analysis,
  feature_request, other. Internal status values: open, awaiting_user, resolved, closed.
- Create starts open; admin reply normally awaits user; member reply reopens awaiting
  or resolved tickets; closed tickets reject replies. Admin status changes are audited.
- Create and reply have sender-scoped request UUIDs, payload conflict checks, and
  concurrency-safe database uniqueness. Replies, activity updates, and notification
  outbox enqueue share one transaction. Stable timestamp/UUID pagination.
- Member ticket list/detail never exposes another owner's tickets. Admin sees only
  account identifier and support content/metadata, not health/profile records.
- Safe metadata: platform, app/version, build, locale. No automatic photos, labs,
  health documents, message bodies, or personal device identifiers in push payloads.
- `support_ticket_reply` carries validated ticket ID and generic notification copy;
  member routes open that ticket after authentication, including cold-start handling.
- V1 defers optional screenshots and assignment, not ticket functionality. No CMS,
  anonymous ticket creation, set logging, medical claims, or LLM insights.

### APIs proposed

- Public: `GET /api/v1/support/config`; Help registry ships in Core.
- Member: `GET/POST /api/v1/support/tickets`, detail, paginated messages, reply,
  mark-read routes under `/tickets/{ticket_id}`.
- Admin: queue, counts, detail, reply, and status routes under
  `/api/v1/support/admin/tickets`.
- Progress: `GET /api/v1/progress/overview?range=...&timezone=...`.
  Split body/calorie series only if overview query/payload evidence justifies it.
- Extend profile measurement input/output and generated contracts for exact width
  and provenance. Keep existing circumference fields and specialist contracts intact.

## Bounded implementation tasks

| Phase | Main modules | Exit check |
| --- | --- | --- |
| 1 | support models/service/router/migration | ownership, admin auth, idempotency, status, transaction tests |
| 2 | Core Help, Web public/member support, Mobile support | shared search, loading/error/empty, member rendering |
| 3 | Web admin support | queue/search/filters/counts/replies/status tests |
| 4 | contact config, notification content/outbox/routes | notification dedup, preferences, warm/cold deep links, release config |
| 5 | progress projection/contracts | authorization, modes, bounded queries, timezone/range tests |
| 6 | profile measurement provenance/width | migration, existing profile behavior, missing/single/repeated/delta/unit tests |
| 7 | nutrition effective history/calorie aggregation | activation/revision/date boundaries, null intake, paired summary tests |
| 8 | Web progress/charts | metric toggles, tooltip, empty states, RTL/LTR, browser responsive checks |
| 9 | Mobile progress/navigation | five tabs, legacy links, query invalidation, native rendering |
| 10 | shared polish and session history | accessible chart details, recovery, reschedule semantics, performance checks |
| 11 | affected suites/contracts/builds/CI | backend shards, Core, Web, native tests, lint/typecheck, migrations/OpenAPI, CI |

Per task: focused tests/checks, explicit file staging, behavior-specific commit and
push. Full affected validation runs once the feature is coherent. Use the existing
OpenAPI generator and rebuild Core before client validation. Production deployment
and store publishing remain separate from implementing and validating these features.

## Decisions needed before implementation

Architecture options:
1. Canonical records plus provenance and lifecycle events — Recommended.
2. Canonical records plus conservative unknown-history gaps, without new lifecycle events.

Both require exact shoulder width and observation provenance. Option 2 cannot recover
targets after lifecycle changes or report reschedule history; it must return unknown
where evidence is insufficient. Option 1 preserves these facts for future activity.
No option invents legacy observations or activation history.

The approved public support email must be supplied before contact/release completion.
Architecture selection also confirms use of the existing reliable-day calorie band,
the explicit denominators above, and authenticated support before profile completion.

## Verification in Phase 0

Source inspection covered the named Web/Mobile/backend domains, shared Core,
translations, privacy/upload architecture, tests, example environment, migrations,
runtime configuration, store metadata, and CI workflows. Migration head was read
without applying migrations. No feature tests, app runtime checks, builds, or full CI
were run. No production source or schema changed.
