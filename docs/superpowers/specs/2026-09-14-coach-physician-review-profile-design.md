# Coach and Physician Review Profile Summary

Date: 2026-09-14

## Approved decisions

- The specialist detail view loads the user's current profile when it opens. No profile snapshot, duplicate body fields, migration, or new public endpoint is added.
- Coach review queues use Persian date groups. Pending and claimed requests are grouped by request date; approved requests are grouped by approval date. Every card shows the request date, and approved cards also show the approval date.
- The same concise-but-complete profile summary is available to both coaches and physicians. It is included only in authorized review detail responses, not in queue payloads.
- The summary presents important highlights first and keeps the remaining current data in expandable sections. It includes body measurements, training/profile preferences, nutrition preferences and constraints, medical flags, conditions, medications, and the latest safety decision when those records exist.

## Data flow

1. Add a backend `ReviewProfileSummary` response model and a single profile-summary builder in the profile module.
2. Build the summary from the existing `UserProfile` and latest append-only `BodyMeasurement`, plus the user's existing nutrition, food, structured-exercise, medical, medication, condition, and safety-decision records.
3. Add `profile_summary` to `WorkoutReviewDetailResponse`.
4. Add an optional `profile_summary` field to `WeeklyPlanResponse`, populated only by physician-assigned plan/review responses. Existing member and public nutrition responses remain unchanged in behavior.
5. Reuse the existing authorization boundaries: a coach can receive the summary only through an accessible workout-review detail; a physician can receive it only through an assigned nutrition-review plan detail or action response. Queue responses continue to contain only queue-safe fields.
6. Extend the shared workout-review grouping helper with an explicit timestamp field so Web and Android use the same Tehran-local grouping rules and approved-date behavior.

## UI behavior

- Web and Android coach workspaces render Persian date headings in pending, mine, and approved views.
- Each request card renders its submitted date. Approved cards render their approval date when available.
- Coach and physician detail views render a compact profile card with the most important fields visible: age/birth date, sex, height, latest weight and measurement date, goal, training frequency, limitations, and cautions.
- An expandable “complete profile” section renders the remaining current training, nutrition, food, medical, medication, condition, and safety information without exposing it in the queue.
- Existing review actions, plan data, photo access, lab access, and file permissions are unchanged.

## Resilience and privacy

- Missing optional nutrition or medical records produce empty/optional sections; they do not duplicate or invent profile values.
- The shared profile and latest measurement remain the sources of truth. Body-analysis review versions are not copied into this summary.
- Summary construction stays behind the existing role and relationship checks. No specialist can obtain a user's profile by changing an ID in a queue or unrelated endpoint.
- No database migration is required.

## Verification

- Backend tests cover complete summary serialization, optional sections, authorized coach detail and physician assigned-plan responses, and queue non-leakage.
- Core tests cover approved-date grouping, request-date fallback, Tehran boundaries, and ordering.
- Web and Android tests cover date headings, request/approval dates, highlight fields, and expandable complete-profile content.
- Focused lint, typecheck, backend tests, shared-package tests, and frontend tests run before the implementation is reported complete.

## Non-goals

- Changing claim, assignment, approval, rejection, or review lifecycle rules.
- Persisting a profile snapshot on a review.
- Creating a parallel access-control or entitlement system.
- Changing raw body-photo, lab, or file permission rules.
