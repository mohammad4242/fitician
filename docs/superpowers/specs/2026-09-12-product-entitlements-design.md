# Fitsho Product Entitlements and Quotas Design

**Date:** 2026-09-12
**Status:** Approved for implementation

## Goal

Add the first real Product, Entitlement, and Quota layer without changing the
meaning of `ProductMode`, replacing specialist authorization, taking existing
member data hostage, or introducing payment concepts.

## Architectural boundary

`backend/app/entitlements/` is an independent domain module. It owns stable
package codes, entitlement codes, the immutable product catalog, persisted
member grants, persisted usage events, access resolution, quota enforcement,
and standardized access errors.

Auth, profile, workouts, nutrition, and Body Analysis consume resolved
capabilities. They do not inspect paid package codes to authorize operations.
`ProductMode` remains the onboarding/application path (`training`, `nutrition`,
or `both`). Coach and physician specialist roles remain the authorization
boundary for their workspaces.

## Catalog and resolution

The catalog is code-defined, immutable, and version-controlled. It contains no
price, checkout, transaction, provider, invoice, or payment table.

Package kinds are `free`, `subscription`, and `trial`; only subscription
packages are purchasable in this phase. The stable package codes are:

| Package | Entitlements |
| --- | --- |
| `free` | none |
| `training` | `training.plan.generate`, `training.cycle.manage`, `body_analysis.run` |
| `training_coach` | Training plus `training.coach_review` |
| `nutrition` | `nutrition.plan.generate`, `nutrition.plan.manage`, `nutrition.food_photo.analyze`, `body_analysis.run` |
| `nutrition_physician` | Nutrition plus `nutrition.physician_review`, `nutrition.labs.manage`, `nutrition.supplements.manage` |
| `complete` | Training union Nutrition, without human review capabilities |
| `complete_care` | Training Coach union Nutrition Physician |
| `launch_trial` | Complete Care feature set, non-purchasable, 30 days |

Quota policies are declared once in the catalog and exposed by products and
member access responses:

| Entitlement | Limit | Rolling window |
| --- | ---: | ---: |
| `body_analysis.run` | 1 | 7 days |
| `training.coach_review` | 1 | 28 days |
| `nutrition.physician_review` | 1 | 28 days |

No new subscription quota is added for food-photo analysis or plan generation;
existing operational safeguards remain authoritative.

For resolution, Free is an implicit baseline. Active grants are the rows whose
start is at or before `now`, are not revoked, and either have no end or end in
the future. All active package entitlements are unioned. `primary_package` is
only a display value chosen by the ranking
`complete_care`, `complete`, `training_coach`/`nutrition_physician`,
`training`/`nutrition`, `launch_trial`, `free`; it is never used for
authorization. A paid package therefore never removes overlapping trial access.

## Persistence and service contracts

`user_access_grants` stores UUID grants, user ownership with cascade deletion,
package code, grant source, start/end/revocation timestamps, an optional
idempotency key, and creation time. A nullable `(user_id, idempotency_key)`
unique constraint prevents duplicate semantic grants while allowing repeated
normal grants across a user's lifetime.

`entitlement_usage_events` stores UUID user-owned usage, entitlement key,
resource key, occurrence time, and creation time. A unique
`(user_id, entitlement_key, resource_key)` constraint makes consumption
idempotent. An index on `(user_id, entitlement_key, occurred_at)` supports
rolling-window counts.

The service exposes focused operations for active grants, access snapshots,
capability checks, quota status/check/consumption, package grants, and
idempotent Launch Trial provisioning. Low-level service methods do not commit.
Quota consumption locks the stable `users` row, checks the exact resource event,
counts the rolling window, raises a domain quota error when exhausted, or
inserts one event. The feature transition and event commit together.

Missing capability is HTTP 403 with `ENTITLEMENT_REQUIRED`, entitlement, and
eligible purchasable packages. Exhausted quota is HTTP 429 with
`ENTITLEMENT_QUOTA_EXCEEDED`, entitlement, `reset_at`, and
`retry_after_seconds` plus `Retry-After`.

The API exposes a public catalog at `/api/v1/products` and an authenticated,
profile-independent snapshot at `/api/v1/entitlements/me`. The snapshot
contains active package summaries, display primary package, trial state,
granted capabilities, and applicable quota status.

## Launch Trial provisioning

`ensure_launch_trial_grant` creates exactly one `launch_trial` grant with source
`launch_trial`, idempotency key `launch_trial:v1`, and an end exactly 30 days
after its start. It runs after a newly created User has an ID and before the
account transaction commits.

The email registration branch, new Google account branch, new Apple account
branch, and new phone-only account branch provision the grant. Existing Google
or Apple login/linking, existing phone login, password login, token refresh, and
session reissue do not provision it.

## Workout lifecycle

`POST /api/v1/workout-plans/generate` requires
`training.plan.generate`. The router resolves
`review_required = access.has(training.coach_review)` and passes that boolean
explicitly to `WorkoutGenerationService`; the service never derives a package.

Generation signatures include the lifecycle policy so an old directly-active
plan cannot be reused after the member becomes coach-review eligible. The same
policy is applied to deterministic, AI, bodyweight, and fallback paths.

Direct Training generation persists a new plan as `ACTIVE`, supersedes the
previous active version according to the existing foreground/archive rules, and
does not create a `WorkoutPlanReview`. Training Coach generation persists one
`PENDING_REVIEW` plan, keeps the prior active plan usable, creates one review,
and consumes `training.coach_review` with resource
`workout-plan:<plan_id>` in the same persistence transaction. Review approval
continues to use the existing specialist lifecycle.

Retry/reuse of the same compatible resource is idempotent and does not consume
another quota. A concurrent quota winner causes the new review-generation
transaction to roll back before an unauthorized pending review remains.

## Nutrition lifecycle and safety

The existing budget/ideal bundle architecture remains. Automatic generation
persists candidate plans without attaching a physician review. Final selection
is the transition point.

For standard safety, a member with Nutrition capability selects a candidate and
that selected plan becomes usable without a physician review. A member with
Nutrition Physician capability selects one final candidate; only that plan gets
one `NutritionPlanPhysicianReview`, enters physician review, and consumes
`nutrition.physician_review` with resource
`nutrition-plan:<plan_id>:revision:<revision>` atomically.

The budget and ideal candidates are never both sent to the physician. Repeating
the same final plan/revision is idempotent and does not consume quota twice.

Safety outcomes remain authoritative:

- `standard_automatic`: normal entitlement rules apply.
- `automatic_draft_requires_physician_review`: plain Nutrition cannot activate
  the result and receives a structured physician-entitlement-required response;
  physician-capable access may continue to review.
- `physician_manual_plan_required`: the existing manual physician workflow is
  preserved.
- `unsupported_or_hard_blocked`: remains blocked.

Nutrition plan responses add `physician_review_required` and nullable
`physician_review_status` while retaining existing compatibility fields. A plan
without a review is not represented as physician-approved and is not displayed
as waiting for a physician.

New plan generation requires `nutrition.plan.generate`. New paid plan edits or
regeneration require `nutrition.plan.manage`; existing plan reads, history,
PDFs, and member-owned data remain available after expiry. Food-photo creation
requires `nutrition.food_photo.analyze` but keeps consent, idempotency, queue,
storage validation, and the operational rate limit. Manual tracking, estimate
reads, existing-estimate edits/confirmation, and deletion remain available.

Member lab upload uses `nutrition.labs.manage`; member supplement-order
acknowledgement uses `nutrition.supplements.manage`. Physician prescription,
review, and workspace routes continue to use the existing physician specialist
authorization. Existing lab/supplement data remains readable or deletable
according to current ownership rules.

## Body Analysis lifecycle

Creating a new Body Photo session requires `body_analysis.run` and a quota
preflight before photos are uploaded. Existing sessions, photos, histories,
results, comparisons, and deletion remain readable/available.

At the actual member analysis queue transition, after input and measurement
validation, the service consumes `body_analysis.run` with resource
`body-analysis-session:<session_id>` immediately before the new analysis is
committed. Same-session retries find the same usage event and do not consume
again. A different session in the seven-day window receives HTTP 429. Admin
retry remains under existing admin authorization and does not use member quota.

## Shared and client contracts

`packages/fitician-core/src/entitlements.ts` defines readonly package and
entitlement unions/constants, product catalog item, quota status, grant summary,
and entitlement snapshot contracts. It is exported from the package root and
the `@fitician/core/entitlements` subpath. Core locale files own package labels.

Web adds one authenticated entitlement provider, API client, and gate. The
provider reacts to login/logout, avoids duplicate snapshot requests, exposes
snapshot/loading/error/retry and capability/quota helpers, and is placed once in
the authenticated provider tree. Pages use it for paid actions only.

Web preserves ProductMode routing and domain visibility. Body Analysis history
is discoverable for both training and nutrition modes; starting a new analysis
uses the entitlement/quota UX. Existing workout/nutrition plans and PDF/history
remain visible after expiry. More and Dashboard show locked states and a compact
current-package/trial summary without prices or purchase UI.

Mobile adds equivalent API, provider, and gate using the shared core contracts.
The provider is nested under `MobileAuthProvider`, clears on sign-out, and stays
independent from route ProductMode and specialist state. Body Analysis history
and tab access no longer require Training ProductMode; fresh capture and paid
actions use capabilities and quota state. Android and iOS share the same
implementation.

## Verification

Verification is incremental: entitlement catalog/service/model/API/quota and
migration tests first; auth and Launch Trial tests next; focused workout/review,
nutrition, food-photo/clinical, and Body Analysis tests after each integration;
then core package tests, Web Vitest/type/build checks, Mobile tests/type checks,
and broad regression suites. Existing unrelated failures are recorded without
weakening assertions. Every verified logical step is committed with only the
named files staged and pushed when the configured remote accepts it.
