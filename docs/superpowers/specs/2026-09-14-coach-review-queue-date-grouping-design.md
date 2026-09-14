# Coach review queue date grouping

## Scope

Organize the existing coach workout-review queues in Web and React Native so
that the same three tabs remain available while queue items are grouped by how
recently the program was sent. The narrow Web layout and Android layout must
show either the queue or the selected review detail, keeping the screen usable
on phone widths.

## Design

The existing `GET /api/v1/coach/workout-reviews?view=...` contract remains the
source of truth. It already returns `created_at`, which is the review/program
sent timestamp. The backend query changes its ordering to descending
`created_at` with a deterministic ID tie-breaker.

The shared `@fitician/core/workout-reviews` module gains a pure grouping helper.
It copies and sorts queue items newest-first, then assigns them to these
relative Tehran-date buckets:

- each of the seven most recent days gets its own date group;
- days 8–14, 15–21, and 22–28 become week 2, week 3, and week 4 groups;
- items 28 days old or older become one `month` group.

Empty daily and weekly groups are omitted. This keeps the queue compact while
preserving chronological order. The helper accepts an optional current
timestamp so its boundaries are deterministic in tests. It uses Tehran local
calendar dates for the bucket calculation; storage remains ISO UTC.

Web and native render the helper's groups in all three existing tabs:
«در انتظار بررسی», «در حال بررسی من», and «تأییدشده». Each group has a clear
date/range heading. Each compact item shows the member, goal/experience, exact
Tehran send date and time, status, and the existing action. No review action,
claim behavior, lease behavior, or detail contract changes.

On desktop Web, the existing queue/detail two-column workspace remains. On
phone-width Web and Android, selecting a review hides the queue and shows the
detail; the existing back action returns to the queue. The selected detail is
not made executable or otherwise changed.

## Components and data flow

1. Backend `list_reviews` returns the current view in newest-first order.
2. Web and native receive the existing queue item shape.
3. Both clients call the shared grouping helper and render localized group
   headings and send timestamps.
4. Selecting an item uses the existing claim/get API and opens the existing
   detail editor.

## Error and edge handling

Existing loading, offline, empty, retry, claim-conflict, and detail-error
states remain unchanged. An empty group is not rendered. A queue item remains
visible in its selected tab after a failed action, and review leases continue
to use the existing renewal path.

## Verification

- Core tests cover newest-first ordering, seven daily buckets, three weekly
  buckets, the older-than-28-days month bucket, same-day ordering, and Tehran
  midnight boundaries.
- Backend tests verify the queue endpoint returns newest-first items.
- Web tests verify all tabs render grouped headings and sent timestamps, and
  the selected-review mobile mode preserves the existing claim flow.
- Native tests verify grouped headings, sent timestamps, tab behavior, and
  that the queue is replaced by detail when a review is selected.
- Run focused tests, core build/typecheck, Web lint/build, native tests,
  native typecheck, and a final diff/status review.

## Non-goals

No new endpoint, pagination, database migration, review-status change,
notification change, claim/lease change, workout-plan editor change, or
unrelated visual redesign.
