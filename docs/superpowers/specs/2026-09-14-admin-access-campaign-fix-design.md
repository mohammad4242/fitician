# Admin access campaign creation and activation fix

## Problem

The campaign API receives creation requests, but the admin page collapses every
save or activation failure into the generic access-loading message. The current
primary button also uses a dark foreground on a dark background. The supported
training terms are already defined as 4, 6, and 8 weeks in both the frontend and
backend; the live failed request is a validation failure, not a missing term
option.

## Scope

- Make the campaign save action readable with accessible contrast in its normal,
  hover, focus, and disabled states.
- Validate campaign fields in the admin form before sending a request: code,
  name, benefit duration, redemption cap, and training term required by the
  selected package.
- Keep the existing package semantics: Signup Trial remains `launch_trial` with
  term 4; Manual Promotion excludes `free` and `launch_trial`.
- Preserve the existing 4/6/8 term options for manual campaigns and send the
  selected value unchanged as `term_weeks`.
- Show a localized, actionable error for validation, activation conflicts, and
  generic API failures instead of reporting a load failure.
- Keep activation policy unchanged: only one active Signup Trial window is
  allowed. A conflict must be visible to the admin rather than silently
  deactivating another campaign.

## Architecture and data flow

The page remains the owner of form state and calls the existing
`adminAccessApi` functions. The API contract and access-management service remain
authoritative for package and term rules. The frontend performs only immediate
field checks and maps `ApiError` responses to display text; it does not duplicate
server authorization or activation policy.

Create/update flow:

1. The admin edits the form and selects 4, 6, or 8 weeks for a manual training
   package.
2. The page validates the form and sends the normalized request through
   `createCampaign` or `updateCampaign`.
3. On success, the returned campaign replaces or prepends the local record.
4. On failure, the form stays open and displays the server or field error.

Activation flow:

1. The page calls the existing activate/deactivate endpoint.
2. On success, the returned campaign updates the local list.
3. On failure, the affected action stops and the API error remains visible.

## Error handling

- Empty or malformed client fields are shown beside the relevant form field and
  do not trigger a request.
- HTTP 422 details are summarized in the form error area.
- Signup Trial overlap and other structured API conflicts use a dedicated
  localized message.
- Unknown failures use the existing save/action error copy.
- A failed save must not close the form or mark the page as a load failure.

## Testing

- Frontend component tests cover readable save state, client validation, error
  rendering, and create requests with each manual term: 4, 6, and 8.
- Frontend component tests cover activation failure rendering.
- Existing backend campaign API/service tests remain unchanged and continue to
  verify authoritative package and term semantics.
- Run the focused frontend access-management tests, focused backend campaign
  tests, frontend lint/build, and the final diff/status check.

## Acceptance criteria

- An admin can create a valid Manual Promotion for 4, 6, or 8 training weeks.
- The selected term is persisted and displayed in the campaign list.
- The save button is clearly readable and its disabled state is distinguishable.
- Failed create, update, or activation actions show the actual actionable cause
  without losing the form state.
- Existing Signup Trial overlap and package restrictions remain enforced.
