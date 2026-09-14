# Physician review queue date grouping

## Scope

Group the existing physician nutrition-review queue items in all three Web
tabs: pending, claimed/in review, and approved. The queue remains the same
workflow; only its ordering and presentation are organized by the time the
case was sent for review.

## Design

The existing `GET /api/v1/nutrition/physician/reviews?view=...` contract
remains unchanged. `requested_at` is the authoritative sent-to-review
timestamp for every queue view, including approved cases. The backend returns
each view newest-first by `requested_at`, with `review_id` as a deterministic
tie-breaker.

The shared `@fitician/core` package gains a generic, pure recency-grouping
helper. The helper accepts a read-only list, a timestamp selector, and an
optional current timestamp for deterministic tests. It sorts a copy of the
input, converts timestamps to Tehran calendar dates, and returns ordered groups:

- today and each of the previous six Tehran calendar days as separate groups;
- week 2, week 3, and week 4 for ages 7–13, 14–20, and 21–27 calendar days;
- one month group for items at least 28 calendar days old.

Empty groups are omitted. Items inside every group remain newest-first. The
existing coach queue helper delegates to the generic helper so its behavior
stays unchanged, while the physician page supplies `requested_at`.

The physician page renders the helper output inside each existing queue tab.
Each group has a localized date or date-range heading. Existing case cards,
claim behavior, read-only approved behavior, detail loading, and actions stay
unchanged.

## Components and data flow

1. `review_queue()` orders each physician view by `requested_at DESC` and
   `review_id DESC`.
2. The API returns the existing queue item shape.
3. The Web page calls the shared helper for the active view using
   `requested_at`.
4. The Web page renders ordered non-empty groups and existing case actions.

No endpoint, response field, database column, migration, or review lifecycle
state changes are needed.

## Error and edge handling

Existing loading, empty, error, claim-conflict, and detail-error states remain
unchanged. Invalid timestamps are rejected by the shared helper rather than
silently assigned to the wrong group. Tehran midnight boundaries are covered
by tests. A group is not rendered when it has no items.

## Verification

- Shared-core tests cover daily, weekly, and month groups, newest-first order,
  same-day order, Tehran midnight boundaries, and the physician timestamp
  selector.
- Backend tests verify newest-first ordering for physician queue views.
- Web tests verify grouped headings and ordering in all three physician tabs,
  while preserving the existing claim and detail flow.
- Run focused tests, core checks, Web lint/build, and a final diff/status
  review.

## Non-goals

No pagination, new API contract, database migration, priority-policy change
beyond the requested newest-first ordering, notification change, claim/lease
change, plan-editor change, or unrelated visual redesign.
