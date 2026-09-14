# Specialist review approval hardening

Date: 2026-09-14

## Approved decision

Coach review claims are persistent. They do not expire automatically. A claimed
case stays with its coach until approval, rejection, or explicit manual release
back to the queue.

The final approval state for both coach and physician reviews remains permanent.
No approval bypass is added for unsafe nutrition plans.

## Current failures

- Workout review claims use a 30-minute lease. The queue keeps expired claims in
  the coach's "mine" view, while save and approve reject them with
  `REVIEW_LEASE_EXPIRED`.
- Nutrition generation can return success while fibre is below its hard minimum.
  Physician approval correctly rejects the persisted revision with
  `PLAN_HARD_INVARIANTS_FAILED`, but the UI hides the nutrient-level reason.
- Web and native review screens replace structured API errors with generic text.

## Scope and invariants

- Apply the same review behavior to Web/PWA and native Mobile.
- Preserve role checks, origin protection, optimistic revision checks, and
  source-plan supersession rules.
- Keep nutrition hard floors, upper limits, and budget rules enforced.
- Do not add automatic approval, role changes, or a parallel assignment system.

## Design

### Persistent coach review claim

- Allow a claimed review to have a null `lease_expires_at`; retain the existing
  columns for compatibility and use `lease_acquired_at` as audit data.
- Change claim validation so another coach cannot take a claimed case merely
  because an old timestamp has passed. Re-claim by the current coach is
  idempotent.
- Treat save, reject, and approve as claim-based rather than time-based.
- Keep the renew endpoint as a compatibility no-op and remove client renewal
  timers.
- Add a trusted-origin `release` endpoint. Only the current coach can release a
  still-open case; release clears ownership and returns the preserved draft to
  the pending queue.
- Update Web and Mobile queue/detail actions to show persistent ownership and a
  manual release action. Other coaches see the case as unavailable.
- Add an Alembic migration that updates the consistency constraint, converts
  legacy expired open claims to pending, and removes expiry timestamps from
  remaining claimed cases.

### Nutrition generation and approval

- Include fibre in planner hard-minimum feasibility validation with zero
  tolerance, matching the scientific policy and physician approval guard.
- Add a fibre-specific infeasibility reason when portion bounds cannot repair
  the minimum.
- Keep physician approval blocked while any hard nutrient or budget invariant
  fails.
- Return structured approval problems containing nutrient code, status, planned
  value, limit, and unit; include budget details when budget is the blocker.
- Preserve the existing physician edit flow so a corrected revision can be
  generated and approved.

### Clear errors and problem highlighting

- Preserve API error code and detail payloads in Web and Mobile API clients.
- Coach screens render claim, revision, and draft-validation problems near the
  action area, including the affected exercise/field when supplied.
- Physician screens render a visible error summary after a failed approval and
  mark each failing nutrient row, for example `Fibre: 24.93 g/day; minimum:
  25 g/day`.
- Use Persian-first labels with English fallbacks and `aria-live`/native
  accessibility announcements for action failures.

## Verification

- Backend service/API tests cover persistent claims, expired legacy migration,
  release and re-claim, and approval after time advances.
- Planner tests cover fibre hard-floor success and infeasibility.
- Nutrition API tests cover structured hard-invariant details.
- Web and Mobile tests cover manual release, persistent approval actions, and
  nutrient/field-level error rendering.
- Run focused backend, Web, and native tests, then lint/type checks for changed
  packages.

## Main files

- `backend/app/workout_reviews/{models,repository,service,router}.py`
- `backend/app/nutrition/{planner_engine,portion_solver,plan_editing,router}.py`
- `backend/tests/workout_reviews/`, `backend/tests/nutrition/`
- `frontend/src/features/workoutReviews/`,
  `frontend/src/features/nutrition/`
- `mobile/coach/`, `mobile/physician/`, and shared API error handling
- `backend/alembic/versions/`
