# Admin Overview and User 360

## Architecture

All screens remain under Admin → Subscriptions & Access (`/admin/billing`). The new Overview tab uses `/admin/billing/overview`; user details keep `/admin/billing/users/:userId`. Offers, campaigns, users, orders, audit and access/grant actions remain available.

Focused admin-only APIs aggregate canonical database records. The paginated timeline uses a SQL union of existing product history and new explicit activity, excluding historical duplicates for the same resource. User summaries batch names, grants, trials and activity; a regression test pins six queries regardless of page size. Existing entitlement ranking and workout/nutrition serialization are reused. Nutrition safety/visibility checks remain enforced.

The activity domain is small and transactional: success events are written in the original transaction; retries reuse stable domain identifiers. Metadata is allowlisted, scalar and bounded. Admin projections exclude credentials, provider payloads, raw photos/media, medical history and clinical notes. Body analysis exposes operational status/revision/dates only. Progress filters carried-forward values when observation provenance is available; legacy snapshots are labeled as uncertain.

## Main files

- `backend/app/user_activity/`: model and transactional recording service.
- `backend/app/access_management/{activity_queries,insights_schemas,insights_service,insights_router,plan_insights}.py`: analytics and safe history APIs.
- Existing auth, profile, workouts/cycles, nutrition, billing, body analysis and support services: success hooks.
- `frontend/src/features/accessManagement/AdminAccessOverviewPage.tsx`, `AdminUser360Sections.tsx`, existing user pages/API/CSS and `frontend/src/App.tsx`.
- Core Persian/English translations, regenerated `contracts/openapi.json` and `packages/fitician-core/src/generated/api.ts`.

## Migration

`20261007_172_user_activity_events.py` follows the verified `20261007_171` head. It adds the activity table, cascade ownership FK, unique deduplication key and user/time, event/time and resource lookup indexes. The users signup index is created/dropped concurrently. A guarded PostgreSQL test exercises downgrade/upgrade and index/FK assertions. No historical backfill is performed.

## API contract

Prefix: `/api/v1/admin/access`.

- `GET /overview`
- `GET /users`: `{items,total,limit,offset}`; existing search, signup period/custom range and sorting. This intentionally replaces the old array response; Web consumer and generated contracts are updated.
- Existing `GET /users/{user_id}` stays focused on access management.
- `GET /users/{user_id}/{insights,activity,logins,workout-plans,nutrition-plans,progress,body-analyses}`.
- `GET /users/{user_id}/workout-plans/{plan_id}` and `/nutrition-plans/{plan_id}`.

Collection responses have bounded `limit` (1–100), `offset` (0–1,000,000), total count and stable ordering. Activity supports an optional event type. Detail ownership is checked.

## Explicit events

`auth.registered`, `auth.login_succeeded`, `profile.completed`, `profile.updated`, `workout.plan_generated`, `workout.plan_started`, `workout.session_completed`, `workout.session_skipped`, `workout.weekly_checkin`, `nutrition.plan_generated`, `nutrition.plan_started`, `nutrition.daily_checkin`, `body.measurement_recorded`, `body_analysis.completed`, `billing.order_paid`, `support.ticket_created`.

## Verification

- Backend feature/migration and nutrition start tests: `uv run pytest tests/access_management tests/user_activity tests/nutrition/test_plan_start_api.py -q --tb=short`: **89 passed**.
- Affected-domain regression before final count review: `uv run pytest tests/access_management tests/user_activity tests/auth tests/profile tests/workout_cycles tests/workouts/*.py tests/billing tests/body_analysis tests/support tests/entitlements tests/progress tests/account_deletion tests/nutrition/test_weekly_plan_api.py tests/nutrition/test_tracking_api.py tests/nutrition/test_plan_start_api.py tests/nutrition/test_bundle_selection.py -q --tb=short`: **1,228 passed**.
- After the final soft-delete count review: `uv run pytest tests/access_management tests/user_activity tests/entitlements -q --tb=short`: **103 passed**, including the new regression.
- Frontend: `npm run test --workspace frontend`: **154 files, 1,273 tests passed**. Access management subset: **7 files, 45 tests passed**.
- `npm run test:core`: **20 files, 130 tests passed**.
- `npm run build --workspace @fitician/core` and `npm run build --workspace frontend`: passed; frontend TypeScript, Vite, SSR and 351-page prerender completed.
- `npm run generate:openapi`, `npm run check:openapi`, `npm run test:contracts`: passed; **1 contract test passed**. Generated files were produced by the repository generator.
- `uv run ruff check` on all affected Python files: passed.
- `uv run mypy --follow-imports=silent` on affected domains/services: **30 source files passed**.
- `npm run lint --workspace frontend`: passed with two unchanged warnings in `webTransport.test.ts` and `WeeklyNutritionPlan.tsx`.
- `git diff --check`: passed.
- Mocked browser component QA: Persian RTL and English LTR, dark/light, desktop/mobile; four views had no runtime errors or horizontal overflow. This is local fixture-based QA, not production or real-user verification.

A wider backend run was interrupted after 2,816 passing tests. Eight workout benchmark tests failed against an auxiliary schema missing `exercises.is_public`; one new assertion used tied transaction timestamps and was fixed to identify its measurement resource. Full-import mypy also reports 11 errors in four unchanged workout engine files. These are separate from the passing affected-file typecheck and targeted regression gate.

## Historical limits

Exact login count includes only newly recorded `auth.login_succeeded` events. Retained legacy Web sessions and native token-issued records are labeled evidence, never certain logins; Web registration can create a session. Expired/deleted legacy records and never-persisted historical actions cannot be reconstructed. Older measurement snapshots lack observation-field provenance; their stored values remain visible with an uncertainty note and may include carried-forward values. Historical product records remain the source for plans, sessions, check-ins, progress, purchases and analyses.

Metrics use Tehran midnight, Saturday week start and Gregorian month boundaries, with existing Persian/Jalali display. Active users mean a meaningful persisted action or retained authentication evidence in the period; this is not continuous presence or page-view tracking. Completed body analyses include inference completion pending specialist review.

Implementation is committed/pushed only; no production deployment is included.
