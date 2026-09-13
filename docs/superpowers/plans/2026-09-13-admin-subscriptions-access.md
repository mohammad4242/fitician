# Admin Subscriptions and Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete Web Admin Subscriptions & Access control plane on top of existing package entitlements and billing.

**Architecture:** Add focused `access_management` and `admin_audit` backend domains. Campaigns and manual operations select package codes, call `grant_package()`, and write immutable audit events in the same transaction. Add a nested Web Admin route layout that reuses billing offers and reads the new access/audit APIs.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest, React 19, TypeScript, React Router, Vitest, i18next, OpenAPI TypeScript generation.

**Spec:** `docs/superpowers/specs/2026-09-13-admin-subscriptions-access-design.md`

## Global Constraints

- Preserve existing ProductMode semantics and specialist coach/physician authorization.
- Do not create a second Entitlement or Billing system.
- Admin assigns packages only; `grant_package()` remains the package grant boundary.
- Do not delete grants, campaigns, redemptions, orders, or audit events.
- All Admin routes require `require_admin`; Web mutations also require `require_trusted_origin`.
- Never expose credentials, tokens, provider secrets, callback payloads, card data, or raw health data.
- No campaign delete, audit delete, grant unrevoke, fake refund, or mobile Admin UI.
- Preserve unrelated dirty work and stage only files belonging to each completed task.
- Run targeted checks after each task and commit/push each verified logical step.

---

### Task 1: Add audit domain and migration-safe model registration

**Files:**
- Create: `backend/app/admin_audit/__init__.py`
- Create: `backend/app/admin_audit/enums.py`
- Create: `backend/app/admin_audit/models.py`
- Create: `backend/app/admin_audit/schemas.py`
- Create: `backend/app/admin_audit/service.py`
- Modify: `backend/alembic/env.py`
- Test: `backend/tests/admin_audit/test_service.py`

**Interfaces:**
- Produce `AdminAuditAction`, `AdminAuditEvent`, `record_admin_audit_event(db, ...)`.
- `record_admin_audit_event()` adds only safe JSON business state and never commits.

- [ ] Write service/model tests for stable action values, event persistence, and no secret fields in serialized business state.
- [ ] Run the focused tests and observe the expected missing-module failure.
- [ ] Implement the immutable audit model with SET NULL actor/target FKs and required indexes.
- [ ] Register models with Alembic metadata and make the service accept UUID/string action values.
- [ ] Run `uv run pytest tests/admin_audit/test_service.py -q` and commit `feat(admin-audit): add immutable admin audit domain`.

### Task 2: Add access campaign models, enums, schemas, migration, and seed

**Files:**
- Create: `backend/app/access_management/__init__.py`
- Create: `backend/app/access_management/enums.py`
- Create: `backend/app/access_management/models.py`
- Create: `backend/app/access_management/schemas.py`
- Create: `backend/app/access_management/exceptions.py`
- Modify: `backend/alembic/env.py`
- Create: `backend/alembic/versions/20260913_145_create_access_management.py`
- Test: `backend/tests/access_management/test_campaign_models.py`
- Test: `backend/tests/database/test_access_management_migration.py`

**Interfaces:**
- Produce `AccessCampaignKind`, `AccessCampaign`, `AccessCampaignRedemption`, and typed request/response schemas.
- Migration down revision must be the actual current Alembic head, `20260913_144` at audit time.

- [ ] Add failing model tests for package/duration/term/window/cap validation and the campaign/user uniqueness rule.
- [ ] Run the model tests before implementation.
- [ ] Implement enum-backed campaign fields, snapshot fields, FKs, indexes, check constraints, and bounded validation.
- [ ] Add the initial `launch_trial_v1` signup campaign with package `launch_trial`, 30 days, term 4, active, and no price.
- [ ] Add migration downgrade/upgrade coverage and run `uv run alembic upgrade head` plus focused migration tests.
- [ ] Commit `feat(access-management): add campaign persistence and launch trial seed`.

### Task 3: Implement campaign repository/service and campaign tests

**Files:**
- Create: `backend/app/access_management/repository.py`
- Create: `backend/app/access_management/service.py`
- Test: `backend/tests/access_management/test_campaign_service.py`

**Interfaces:**
- Produce campaign CRUD, activation, `redeem_campaign()`, `provision_signup_campaigns()`, and safe response conversion.
- `redeem_campaign()` locks the campaign, checks the unique redemption, validates active/window/cap, calls `grant_package()`, snapshots, flushes, and does not commit.

- [ ] Write failing tests for campaign CRUD, overlap prevention, immutable redeemed semantics, signup eligibility, cap, disabled campaigns, idempotency, and no auto-application of manual promotions.
- [ ] Run `uv run pytest tests/access_management/test_campaign_service.py -q` and verify feature failures.
- [ ] Implement repository queries and service validation with UTC normalization and campaign locking.
- [ ] Implement signup provisioning over active signup campaigns and manual-only promotion behavior.
- [ ] Run the full access-management service/model subset and commit `feat(access-management): implement campaign lifecycle and redemption`.

### Task 4: Move new-account auth provisioning to database campaigns

**Files:**
- Modify: `backend/app/auth/service.py`
- Modify: `backend/tests/auth/test_register.py`
- Modify: `backend/tests/auth/test_google_auth.py`
- Modify: `backend/tests/auth/test_apple_auth.py`
- Modify: `backend/tests/auth/test_phone_otp.py`
- Modify: `backend/tests/entitlements/test_launch_trial.py`
- Create/modify: `backend/tests/access_management/test_signup_campaigns.py`

**Interfaces:**
- Auth calls `provision_signup_campaigns()` only after a newly created `User` has an ID and before the account transaction commits.
- Existing account login/linking branches do not call provisioning.

- [ ] Add failing regression tests for email, Google, Apple, phone, existing login/linking, and repeat redemption behavior.
- [ ] Run those tests and confirm they fail because auth still uses the legacy helper.
- [ ] Replace every new-account Trial helper call with database campaign provisioning; legacy settings must not remain operational.
- [ ] Run the provider-focused auth and campaign tests; separate the known SMS-provider baseline setup failures if they remain.
- [ ] Commit `feat(auth): provision signup access from database campaigns`.

### Task 5: Add Admin campaign API

**Files:**
- Create: `backend/app/access_management/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/access_management/test_campaign_api.py`

**Interfaces:**
- Add `/api/v1/admin/access/campaigns` list/detail/create/update/activate/deactivate routes.
- Add `/api/v1/admin/access/users/{user_id}/campaigns/{campaign_id}/redeem` for manual promotions with a required reason.

- [ ] Write failing API tests for Admin-only/trusted-origin protection, campaign responses/counts, activation, mutable/immutable fields, and manual promotion redemption.
- [ ] Run focused API tests to verify missing-route failures.
- [ ] Implement dependency-protected routes and domain error mapping.
- [ ] Register the router, run campaign API tests, and commit `feat(admin-access): expose campaign management API`.

### Task 6: Add safe member access search/detail and manual package lifecycle

**Files:**
- Modify: `backend/app/access_management/repository.py`
- Modify: `backend/app/access_management/schemas.py`
- Modify: `backend/app/access_management/service.py`
- Modify: `backend/app/access_management/router.py`
- Test: `backend/tests/access_management/test_admin_user_access.py`
- Test: `backend/tests/access_management/test_manual_grants.py`
- Test: `backend/tests/access_management/test_revocation.py`

**Interfaces:**
- Add `/api/v1/admin/access/users`, `/api/v1/admin/access/users/{user_id}`, `/api/v1/admin/access/users/{user_id}/grants`, and `/api/v1/admin/access/grants/{grant_id}/revoke`.
- Responses include safe identity, entitlement snapshot, all grant states, campaign links, and billing order links where available.

- [ ] Write failing tests for UUID/email/phone/display-name search, secret exclusion, package-only validation, finite dates, reason, idempotency, source forcing, revoke idempotency, and paid-order preservation.
- [ ] Run the tests before production code.
- [ ] Implement safe joins and status classification without changing specialist roles or historical data.
- [ ] Implement manual grants through `grant_package()` and revocation through locked `revoked_at` mutation plus audit hook.
- [ ] Run access-management API tests and commit `feat(admin-access): add member package grant and revoke controls`.

### Task 7: Add Admin audit API and billing offer audit integration

**Files:**
- Modify: `backend/app/admin_audit/schemas.py`
- Modify: `backend/app/admin_audit/service.py`
- Create: `backend/app/admin_audit/router.py`
- Modify: `backend/app/billing/service.py`
- Modify: `backend/app/billing/admin_router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/billing/test_admin_offers.py`
- Test: `backend/tests/admin_audit/test_api.py`

**Interfaces:**
- Add `/api/v1/admin/audit` newest-first query with action/actor/target/resource/date filters.
- `update_offer_config(..., actor_user_id=...)` captures safe before/after values, records `billing.offer.updated`, and does not commit independently.

- [ ] Write failing tests for audit query authorization/filtering and price/activation audit rows, including rollback on insertion failure.
- [ ] Run those tests before implementation.
- [ ] Refactor offer update commit ownership so audit and pricing mutation share one transaction while preserving existing behavior.
- [ ] Implement safe actor/target summaries and register the audit router.
- [ ] Run billing/admin-audit suites and commit `feat(admin-audit): audit billing changes and expose history API`.

### Task 8: Improve Admin billing order responses and verify backend behavior

**Files:**
- Modify: `backend/app/billing/repository.py`
- Modify: `backend/app/billing/schemas.py`
- Modify: `backend/app/billing/service.py`
- Modify: `backend/app/billing/admin_router.py`
- Modify: `backend/tests/billing/test_admin_offers.py`

**Interfaces:**
- Preserve existing order routes; add safe status/provider/user filters if useful and expose access grant linkage and existing transaction fields.
- Never expose provider secrets or callback/card data.

- [ ] Add failing tests for order filters, access grant linkage, transaction state fields, and absence of sensitive fields.
- [ ] Implement bounded query filters and safe response fields.
- [ ] Run focused billing tests and commit `feat(admin-billing): expose safe order and transaction administration`.

### Task 9: Add shared i18n and typed frontend Admin access API

**Files:**
- Modify: `packages/fitician-core/src/i18n/fa.ts`
- Modify: `packages/fitician-core/src/i18n/en.ts`
- Create: `frontend/src/features/accessManagement/adminAccessApi.ts`
- Test: `frontend/src/features/accessManagement/adminAccessApi.test.ts`

**Interfaces:**
- Add typed client functions for campaigns, users, grants, revokes, redemptions, and audit events using `request()`.
- Reuse `AccessPackageCode` from `@fitician/core/entitlements`.

- [ ] Add failing client tests for paths, methods, serialized payloads, and package-code typing.
- [ ] Implement API types and i18n keys for all five sections and access states.
- [ ] Run core/frontend focused tests and commit `feat(admin-access-web): add shared copy and typed access API`.

### Task 10: Build Admin Subscription Center layout and pages

**Files:**
- Create: `frontend/src/features/accessManagement/AdminSubscriptionCenterPage.tsx`
- Create: `frontend/src/features/accessManagement/AdminSubscriptionCenterPage.test.tsx`
- Create: `frontend/src/features/accessManagement/AdminAccessCampaignsPage.tsx`
- Create: `frontend/src/features/accessManagement/AdminAccessCampaignsPage.test.tsx`
- Create: `frontend/src/features/accessManagement/AdminUserAccessPage.tsx`
- Create: `frontend/src/features/accessManagement/AdminUserAccessPage.test.tsx`
- Create: `frontend/src/features/accessManagement/AdminUserAccessDetailPage.tsx`
- Create: `frontend/src/features/accessManagement/AdminUserAccessDetailPage.test.tsx`
- Create: `frontend/src/features/accessManagement/AdminAccessAuditPage.tsx`
- Create: `frontend/src/features/accessManagement/AdminAccessAuditPage.test.tsx`
- Create: `frontend/src/features/accessManagement/accessManagement.css`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/MorePage.tsx`
- Modify: `frontend/src/features/billing/adminApi.ts`
- Create: `frontend/src/features/billing/AdminBillingOrdersPage.tsx`
- Create: `frontend/src/features/billing/AdminBillingOrdersPage.test.tsx`
- Create: `frontend/src/features/billing/AdminBillingOrderDetailPage.tsx`
- Create: `frontend/src/features/billing/AdminBillingOrderDetailPage.test.tsx`

**Interfaces:**
- Nested routes: `/admin/billing/offers`, `/campaigns`, `/users`, `/users/:userId`, `/orders`, `/orders/:orderId`, `/audit` under `AdminRoute`.
- Layout renders one `Outlet` and five URL-backed navigation links.

- [ ] Add failing component tests for URL navigation, five labels, campaign create/edit states, user search/detail actions, revoke paid-order warning, read-only order detail, and audit filters/details.
- [ ] Implement layout and page components with existing visual tokens, React Router navigation, shared i18n, and no mobile files.
- [ ] Reuse `AdminBillingOffersPage` for `/offers`; add typed order list/detail clients and pages without refund actions.
- [ ] Update MorePage to one `اشتراک و دسترسی‌ها` / `Subscriptions & Access` entry.
- [ ] Run all affected Admin frontend tests and commit `feat(admin-access-web): add subscriptions and access center`.

### Task 11: Regenerate contracts and run staged verification

**Files:**
- Generated: `contracts/openapi.json`
- Generated: `packages/fitician-core/src/generated/api.ts`
- Modify only if needed: affected backend/frontend source and tests.

- [ ] Run `npm run generate:openapi` after backend routes stabilize.
- [ ] Run `npm run check:openapi`, `npm run test:contracts`, and core contract tests serially.
- [ ] Run focused backend suites: access management, admin audit, billing admin, entitlements, and auth provider regressions.
- [ ] Run focused frontend tests, `npm run lint`, TypeScript/build checks, then broader practical backend/web regression.
- [ ] Inspect `git diff --check`, `git status`, and all changed paths for unrelated WIP.
- [ ] Commit `chore(api): regenerate subscriptions and access contracts` if generated files are the only remaining logical change.

### Task 12: Final verification and handoff

**Files:**
- No new source files unless a verified failure requires a focused fix.

- [ ] Verify actual starting and ending HEADs, migration revision/down revision, tables, seeded Launch Trial behavior, routes, five UI sections, auth flows, grant/revoke/audit semantics, and sensitive-field exclusions.
- [ ] Run final targeted and broad commands again only as needed; record exact pass/fail counts and known baseline failures.
- [ ] Push each verified commit/current branch when the configured remote accepts it.
- [ ] Report changed files, test commands/results, generated-contract result, and any unrelated pre-existing failures without overstating evidence.
