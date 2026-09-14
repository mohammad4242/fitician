# Specialist review queue week headers

## Scope

Update the existing coach workout-review and physician nutrition-review
queues so their case groups are based on the real Tehran-local week offset from
the current date. Today remains a separate day group. All other cases are
placed in seven-day groups with explicit offsets, and each group receives a
clear two-line header on Web and Native.

## Root cause

`groupReviewQueueByRecency` currently assigns ages 7–13, 14–20, and 21–27 to
the keys `week-2`, `week-3`, and `week-4`. The pages then derive the visible
number with `group.key.slice(-1)`, so a real offset of one is displayed as two.
The helper also collapses every item at age 28 or more into one `month` group,
which prevents week offsets from continuing. Coach, physician Web, and both
Native screens each build the visible heading separately.

## Design

The shared `@fitician/core/workout-reviews` helper remains the single source of
grouping truth. It converts each selected timestamp to a Tehran calendar date,
computes the non-negative calendar-day age from the current Tehran date, and
uses `Math.floor(age / 7)` as the explicit `weekOffset`.

- age 0 is a `day` group for today only;
- ages 1–6 are `weekOffset: 0` (`این هفته` / `This week`);
- ages 7–13 are `weekOffset: 1` (`۱ هفته قبل` / `1 week ago`);
- every later seven-day interval continues with offsets 2, 3, 4, and higher;
- empty groups are omitted and items remain newest-first.

Week group keys use the offset (`week-0`, `week-1`, and so on), but rendering
never parses the key. The group contract exposes `weekOffset`, `startDate`,
and `endDate`. For offset zero, the date range covers the non-today items in
the current seven-day window (`today - 6` through `today - 1`), so the header
describes exactly the cards under it. Older ranges cover their full seven-day
bucket.

## Components and presentation

Web Coach and Web Physician use one shared `ReviewQueueGroupHeader` component.
It renders an accessible group heading with a primary title row, a secondary
Jalali/Gregorian date-range row, and the existing item count. The current week
uses the shared localized label and does not need an extra badge. CSS uses the
existing dark/turquoise tokens, full available width, rounded surface, subtle
turquoise border, an inline-start accent bar (right side in RTL), controlled
vertical spacing, `min-width: 0`, and safe wrapping for narrow viewports.

Native Coach and Physician keep platform-native layout, but consume the same
core `weekOffset` and localized week-label helper. Their title and date are
rendered as separate text rows with RTL-safe wrapping and the same ordering.

Queue tabs, filters, cards, actions, API fields, approval behavior, selected
case behavior, and the existing today/day timestamp presentation remain
unchanged apart from the new grouping boundary and header hierarchy.

## Verification

- Core tests cover today, week offsets 0, 1, 2, and 4, continuation beyond 4,
  exact date ranges, newest-first ordering, and Tehran midnight boundaries.
- Web tests cover both coach and physician headers, separated title/date
  hierarchy, Persian labels, and the absence of legacy `هفتهٔ N` output.
- Native contract/render tests cover both specialist queues and preserve the
  existing tabs and card actions.
- Run focused tests, package checks, Web lint/build, Native checks, diff
  validation, and final Git synchronization.

## Non-goals

No API, database, migration, review-status, filter, card-action, claim/lease,
or unrelated page redesign changes.
