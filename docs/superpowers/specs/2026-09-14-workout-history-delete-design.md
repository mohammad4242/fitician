# Workout history archive and delete UX

## Goal

Make archived workout-plan history understandable before a member deletes a version. The archive list should show a useful identity for each plan, expand into a compact overview, and use an intentional in-app delete dialog instead of the browser confirmation prompt.

## Scope

- Keep the existing workout-plan history endpoint and API types unchanged.
- Keep the current member-history eligibility rules: only superseded and failed versions are deletable; active and pending versions remain protected.
- Replace the small archive action rows with accessible expandable archive entries.
- Load a full plan only when its archive entry is opened, then cache that result for the current page.
- Show only overview information: presentation number, creation date, generation source, duration, number of training days, and day names.
- Do not render exercise names, prescriptions, media, or per-day exercise details in the history overview or delete dialog.
- Replace `window.confirm` with an accessible custom dialog that repeats the selected plan overview and exposes cancel/delete actions.

## User experience

Each archived row is closed by default and contains:

- a presentation-only plan number derived from the visible archive order;
- the localized creation date/time;
- an `Archived` status label;
- an expand/collapse control with a visible chevron and `aria-expanded` state.

Opening a row requests `getWorkoutPlan(version.id)` if the plan is not cached. The expanded panel shows:

- creation date;
- `Fitician Coach` for `internal_engine` and `AI` for `ai`;
- duration in weeks;
- total training-day count;
- the localized title of each training day only.

The delete control appears inside the expanded panel. Clicking it opens a modal with the same compact overview, a clear irreversible-action message, `Cancel`, and `Delete permanently`. The delete request keeps the existing API call and refresh behavior. On success, the dialog closes, the archive disappears, and a deleted selected archive returns the member to the current plan. On failure, the dialog stays open, the confirmation becomes available again, and the existing retryable page error remains visible.

The compact overview is the default archive experience. A secondary `View full version` action preserves the existing ability to inspect an immutable historical plan without adding exercise details to the archive summary or delete dialog.

## Data flow and state

`WorkoutPlanPage` keeps the existing `history` summary state and adds page-local detail cache/loading state keyed by plan ID. Expanding an archive reads the cache first, otherwise calls the existing `getWorkoutPlan` endpoint. Detail-load failures are rendered inside that archive entry and do not mutate the rest of the page.

The delete dialog receives the selected summary and its already-loaded detail. The existing deletion guard and refresh path remain the source of truth for eligibility and persistence. No backend, database, shared contract, or route changes are required.

## Visual direction

Use the existing Fitician dark canvas, aqua accent, coral destructive accent, and typography tokens. The archive list becomes a vertical set of quiet bordered rows; the expanded overview uses a small metadata grid and a restrained day-name list. The delete dialog uses a dimmed backdrop, a compact raised surface, a coral action boundary, and clear keyboard focus states. Respect the existing RTL/LTR language direction, mobile stacking, and reduced-motion rule.

## Error and accessibility behavior

- Archive headers are keyboard-operable buttons with localized labels and `aria-expanded`/`aria-controls`.
- Loading and detail errors are visible and localized; an error does not silently appear as an empty plan.
- The delete dialog has `role="dialog"`, `aria-modal="true"`, a localized accessible name, and disabled/busy confirmation while deletion is in progress.
- Active and pending versions never receive a delete action.
- No destructive request is sent when the user cancels or closes the dialog.

## Verification

Frontend tests will cover:

1. archived rows show visible date and plan number while remaining collapsed;
2. expanding an archive lazily requests and renders source, duration, day count, and day names without rendering exercise details;
3. detail loading is cached on repeated expand/collapse;
4. the custom dialog shows the selected overview and cancellation sends no delete request;
5. successful deletion refreshes history and removes the row;
6. deletion failure keeps a retryable error and re-enables the action;
7. active and pending versions remain non-deletable.

Run the focused workout-page tests, frontend lint, typecheck, and production build before completion.

## Non-goals

- Changing workout-plan lifecycle rules or deletion authorization.
- Adding persisted version numbers.
- Changing the workout detail presentation or the backend history payload.
- Adding new exercise-level information to the archive summary or delete dialog.
