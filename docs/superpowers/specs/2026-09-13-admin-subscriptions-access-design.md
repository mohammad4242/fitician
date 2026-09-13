# Admin Subscriptions and Access Design

## Goal

Add a Web-only Admin control plane at `/admin/billing` for plans, campaigns,
member package access, billing history, and immutable admin audit history while
preserving the existing Product, Entitlement, Billing, specialist-role, and
member-facing behavior.

## Architecture

The new `access_management` domain owns campaign definitions, redemptions,
admin member lookup, package grants, and package revocation. It delegates every
package assignment to `app.entitlements.service.grant_package`; it never stores
or toggles individual entitlement codes. Campaign redemption records are
unique per campaign/user and are created in the same transaction as the grant.

The new `admin_audit` domain owns immutable business-mutation audit events.
`record_admin_audit_event()` only adds an event to the active SQLAlchemy
transaction. Campaign writes, manual grants, revocations, and billing offer
updates therefore commit or roll back together with their audit event.

## Data model

- `access_campaigns` stores immutable code/kind/package/benefit semantics and
  mutable name, description, active state, eligibility window, and redemption
  cap. The initial migration seeds `launch_trial_v1` with the current 30-day,
  four-week Launch Trial semantics.
- `access_campaign_redemptions` stores one campaign/user redemption and a
  snapshot of the campaign semantics used to create the grant.
- `admin_audit_events` stores actor/target references, stable action codes,
  safe business before/after JSON, reason, resource identity, and timestamp.

Campaign dates are evaluated by the backend. Active signup campaigns cannot
overlap. Signup provisioning runs only on a newly created account in the
email, Google, Apple, and phone authentication paths; linking or logging into
an existing account does not provision anything.

## Transaction and security rules

All Admin access routes require `require_admin`; state-changing Web routes also
require `require_trusted_origin`. Manual grants and campaign redemption require
finite access end dates and trimmed reasons. The server fixes the grant source,
rejects `free`, rejects arbitrary entitlement keys, and never changes coach,
physician, or admin roles. Revocation sets `revoked_at` and retains the grant;
it does not change a paid order to refunded.

The existing `ensure_launch_trial_grant()` remains only as a backwards-
compatible legacy helper for callers/tests that still use environment settings.
Normal signup provisioning uses database campaigns, and the legacy settings are
not used by the new Admin control plane.

## API and UI

Admin access APIs live under `/api/v1/admin/access`; audit queries live under
`/api/v1/admin/audit`; existing billing offer/order APIs are extended only where
needed. Safe member summaries exclude credentials and provider secrets.

`AdminSubscriptionCenterPage` is a nested-route layout with five URL-backed
sections: plans/pricing, campaigns/trials, users/access, orders/payments, and
change history. Existing offer management is reused for plans. Campaign and
member pages expose package choices and grant lifecycle actions, never
entitlement checkboxes. Orders remain read-only and there is no fake refund or
unrevoke action.

## Validation

Backend tests cover model constraints, migration upgrade/downgrade, campaign
eligibility/idempotency/immutability, all signup providers, safe member
search/detail, manual grant/revoke, paid-order preservation, account deletion,
and audit atomicity/query authorization. Frontend tests cover the layout and
each of the five pages, API calls, URL navigation, safe revoke messaging, and
read-only order/audit behavior. OpenAPI and generated TypeScript contracts are
regenerated from the application after the API stabilizes.
