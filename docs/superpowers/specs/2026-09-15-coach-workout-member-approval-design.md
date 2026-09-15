# Coach workout editing and member approval

Status: approved for implementation on 2026-09-15.

## Goal

Allow a coach to edit the complete structure of a workout case before it is
accepted by the member. A coach can add, remove, reorder, and edit days and
exercises. Every exercise editor is collapsed by default. The previous active
plan remains unchanged until the member accepts the coach proposal.

## Lifecycle

The existing `WorkoutPlanReview` aggregate remains the workflow boundary.

```text
pending -> claimed -> awaiting_member_acceptance -> approved
                          ^                         |
                          |                         v
                   member_changes_requested   active plan
```

- `pending`: available to coaches.
- `claimed`: owned by one coach while being edited.
- `awaiting_member_acceptance`: the coach submitted a validated proposal.
- `member_changes_requested`: the member rejected the proposal with a required
  explanation; the assignment remains with the same coach.
- `approved`: the member accepted the proposal and the proposed plan became
  the active immutable version.
- Existing `rejected` and `superseded` states remain compatible for older coach
  decisions and obsolete reviews.

The coach submission creates a non-active pending `WorkoutPlan` proposal linked
to the review. A member rejection keeps the prior active version active. A
resubmission replaces only the pending proposal. A member acceptance locks the
review and active plan, supersedes the previous active/source versions, marks
the proposal active, and records the structured coach difference summary.

## Editing contract

The draft accepts one to six sequential days and one to ten exercises per day.
An empty day is invalid; removing its last exercise requires removing the day.
Day titles, exercise order, exercise selection, sets, reps or duration, RIR,
rest, and bilingual exercise notes are persisted in the draft. New exercises
must come from the active, programmable, reviewed exercise catalogue captured by
the source plan. Existing prescription and semantic safety validation remains
the final server-side gate.

The source plan and accepted versions remain immutable. Draft edits are stored
with optimistic `draft_revision` checks and the existing coach lease rules.

## Backend/API

- Extend review status and database fields with the pending proposal link and
  member rejection feedback.
- Replace fixed source-slot validation with sequential day/exercise structure
  validation while preserving catalogue, prescription, duration, and semantic
  checks.
- Add explicit coach submission and member review actions. Keep ownership
  checks, trusted-origin protection, stale revision conflicts, and idempotent
  acceptance.
- Expose a member-safe proposal response containing source plan, proposed plan,
  coach note, structured difference entries, review status, and revision.
- Add notification events for a proposal awaiting member acceptance and for
  member-requested coach changes.
- Keep member plan history and timeline semantics based on active plans only;
  pending proposals are displayed as awaiting approval and never start a cycle.

## Web UX

Coach workspace:

- Keep day accordions collapsed by default.
- Wrap every exercise editor in a collapsed exercise accordion.
- Add controls for adding/removing/reordering days and exercises, editing day
  titles, and editing the existing exercise prescription fields.
- Change the final action to “send for member approval”; approved cases remain
  read-only. Returned cases reopen for the assigned coach.

Member workout page:

- Show the pending proposal and a bilingual structured before/after summary.
- Show the coach note and current proposal status.
- Provide accept and reject actions; rejection requires a non-empty explanation.
- Refresh the active plan, history, and timeline after either action. A rejected
  proposal remains visible as returned-to-coach while the prior active plan is
  still used.

All new copy supports Persian RTL and English LTR. Existing mobile and
accessibility behavior remains unchanged outside the web member and coach
surfaces in scope.

## Verification

- Backend unit/service/API tests cover structure changes, validation, proposal
  creation, member ownership, stale revisions, rejection, acceptance,
  idempotency, and active-plan preservation.
- Frontend tests cover collapsed exercise accordions, day/exercise add/remove,
  coach submission, member diff rendering, required rejection feedback, and
  active-plan refresh.
- The existing specialist E2E workflow is extended to verify persisted coach
  edits, member rejection, resubmission, member acceptance, revision lineage,
  and cross-user isolation with real services.
- Run focused backend/frontend checks first, then the relevant broader suites,
  lint/typecheck/build, inspect the final diff, commit only scoped files, and
  push the current branch.
