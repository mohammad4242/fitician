# Program Timeline and Explicit Plan Start Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement explicit workout and nutrition starts plus one backend-owned local-date program timeline consumed by shared core, web, and mobile.

**Architecture:** Keep workout plans as content and create dated `WorkoutCycleSession` rows only when a member starts a plan. Keep nutrition as a seven-day recurring template anchored by `start_date`. Expose both through a read-only `program_timeline` service and generated OpenAPI types.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, React/TypeScript/Vite, React Native/Expo, React Query, Vitest, Jest/RNTL.

**Spec:** `docs/superpowers/specs/2026-09-13-program-timeline-explicit-start-design.md` and the user-provided Program Timeline / Explicit Plan Start requirements.

## Global Constraints

- Preserve unrelated working-tree changes and stage only files belonging to the current task.
- Use `zoneinfo.ZoneInfo`; do not add a timezone dependency or a second calendar library.
- Use Fitician weekdays `0=Saturday` through `6=Friday`; centralize Python-date conversion.
- Workout plan activation/approval is distinct from workout-cycle start.
- Nutrition approval/selection is distinct from nutrition start; active legacy nutrition plans remain compatible.
- Do not fabricate historical workout sessions for existing cycles.
- Keep weekly check-ins, replacements, completion feedback, nutrition tracking, and adherence behavior intact.
- Generated OpenAPI typings are regenerated, never hand-edited.
- Every backend domain behavior follows a failing-test, focused-red, minimal-green cycle.
- After each verified logical task, commit only that task and push `main` when the configured remote accepts it.

### Task 1: Backend calendar semantics and profile timezone

**Files:**
- Create: `backend/app/time_context.py`
- Create: `backend/tests/test_time_context.py`
- Modify: `backend/app/profile/models.py`
- Modify: `backend/app/profile/schemas.py`
- Modify: `backend/app/profile/service.py`
- Modify: `backend/app/profile/router.py`
- Create: `backend/tests/profile/test_timezone_api.py`

**Interfaces:**
- Produce `validate_timezone_name`, `local_date_for_timezone`, `local_midnight_utc`, and `fitician_weekday`.
- Produce `TimezoneUpdateRequest`, `TimezoneResponse`, `update_user_timezone`, and `PUT /api/v1/profile/timezone`.

- [ ] Write tests for all six calendar cases and valid update, invalid update, isolation, and missing-profile behavior.
- [ ] Run `cd backend && uv run pytest tests/test_time_context.py tests/profile/test_timezone_api.py -q`; confirm failures identify missing helpers/route.
- [ ] Implement the helper with `ZoneInfo`, add `UserProfile.timezone` with UTC defaults, and update only that field under a row lock.
- [ ] Run the focused test command again and run affected Ruff checks.
- [ ] Inspect the diff, stage only Task 1 files, commit `feat: persist member timezone for program timelines`, and push.

### Task 2: Database migration and exact workout-session model

**Files:**
- Create: `backend/alembic/versions/20260913_148_add_program_timeline.py` (or the next available revision after the verified Alembic head)
- Modify: `backend/app/workout_cycles/enums.py`
- Modify: `backend/app/workout_cycles/models.py`
- Modify: `backend/app/nutrition/enums.py`
- Modify: `backend/app/nutrition/models.py`
- Create: `backend/tests/database/test_program_timeline_migration.py`

**Interfaces:**
- Produce `WorkoutCycleSessionStatus` and `WorkoutCycleSession` with ordered `WorkoutCycle.sessions`.
- Add `NutritionWeeklyPlan.started_at` and the `ready_to_start` lifecycle value.

- [ ] Add migration/model tests for non-null UTC backfill, nullable nutrition `started_at`, lifecycle check acceptance, session foreign keys/indexes/uniques/checks, and empty legacy cycles.
- [ ] Run the migration-focused tests before implementation and confirm the schema/model contract fails.
- [ ] Read `uv run alembic heads` immediately before writing the migration, use that revision as `down_revision`, and add all columns/constraints without historical session inserts.
- [ ] Implement matching SQLAlchemy models and relationships with deterministic session ordering.
- [ ] Run `uv run pytest tests/database/test_program_timeline_migration.py tests/workout_cycles/test_weekly_check_in_model.py -q` and `uv run alembic upgrade head` against the test database.
- [ ] Commit `feat: add program timeline persistence schema` and push after inspection.

### Task 3: Workout session generation, lifecycle, and mutations

**Files:**
- Create: `backend/app/workout_cycles/session_service.py` if it keeps generation/mutation logic focused
- Modify: `backend/app/workout_cycles/service.py`
- Modify: `backend/app/workout_cycles/schemas.py`
- Modify: `backend/tests/workout_cycles/test_service.py`
- Create: `backend/tests/workout_cycles/test_session_service.py`

**Interfaces:**
- Produce explicit `start_cycle(..., workout_plan_id, start_date, timezone_name)`.
- Produce `build_cycle_sessions`, `complete_current_cycle_session`, `skip_current_cycle_session`, and `reschedule_current_cycle_session`.
- Produce `WorkoutCycleStartRequest`, `WorkoutCycleSessionResponse`, and extended current-cycle metadata.

- [ ] Add focused failing tests for weekday mapping, rest-day starts, repeated rolling weeks, exact count, legacy weekday fallback, idempotent same-date starts, conflicting starts, all transitions, collisions, and before-start dates.
- [ ] Run the new service tests and existing cycle service tests; verify the failures are behavioral, not fixture typos.
- [ ] Implement plan ownership/status/executable checks, local-midnight UTC storage, profile timezone persistence, session generation from `WorkoutDay.weekday` then profile snapshot/default engine policy, and transaction-safe row locks.
- [ ] Implement derived unfinished-session ordering without storing overdue, and preserve existing cycle/check-in behavior.
- [ ] Run the focused service suite and affected Ruff/mypy checks.
- [ ] Commit `feat: create dated workout cycle sessions on explicit start` and push.

### Task 4: Workout routes, current-cycle selection, and coach approval

**Files:**
- Modify: `backend/app/workout_cycles/router.py`
- Modify: `backend/app/workout_reviews/service.py`
- Modify: `backend/tests/workout_cycles/test_api.py`
- Create: `backend/tests/workout_cycles/test_session_api.py`
- Modify: `backend/tests/workout_reviews/test_service.py`

**Interfaces:**
- Produce start and complete/skip/reschedule routes with trusted-origin protection and 404/409/422 mappings.
- Make `get_current_active_cycle_for_user` join the current active executable workout plan.
- Make coach approval create an active approved plan without creating a cycle.

- [ ] Add failing API/regression tests for auth, ownership, invalid transitions, route methods/payloads, current-plan filtering, and approval-without-cycle.
- [ ] Run only the targeted API/review tests and confirm red failures.
- [ ] Add route handlers and error mapping; update review approval without changing review history or active replacement semantics.
- [ ] Run `uv run pytest tests/workout_cycles/test_session_api.py tests/workout_cycles/test_service.py tests/workout_cycles/test_api.py tests/workout_reviews/test_service.py -q`.
- [ ] Commit `feat: expose explicit workout session lifecycle endpoints` and push.

### Task 5: Nutrition ready state, explicit start, and recurring helpers

**Files:**
- Create: `backend/app/nutrition/plan_lifecycle_service.py` if needed
- Modify: `backend/app/nutrition/plan_service.py`
- Modify: `backend/app/nutrition/plan_editing.py`
- Modify: `backend/app/nutrition/router.py`
- Modify: `backend/app/nutrition/schemas.py`
- Create: `backend/tests/nutrition/test_plan_start_api.py`
- Modify: `backend/tests/nutrition/test_bundle_selection.py`
- Modify: `backend/tests/nutrition/test_weekly_plan_api.py`
- Modify: `backend/tests/nutrition/test_tracking_api.py`
- Modify: `backend/tests/nutrition/test_adherence_api.py`

**Interfaces:**
- Produce `NutritionPlanStartRequest`, explicit nutrition-start service behavior, `nutrition_pattern_day_index`, and `nutrition_absolute_day_number`.
- Preserve selected bundle/reference-plan rules and existing modulo tracking/adherence.

- [ ] Add failing tests for ready/today, future scheduled start, ownership, comparison rejection, required review rejection, seven-date realignment, active legacy compatibility, and Day 8 modulo mapping.
- [ ] Run the focused nutrition tests and confirm old auto-activation assumptions are the only intentional failures.
- [ ] Change finalized unstarted plans to `ready_to_start`, remove date-based approval activation, add start validation/lineage archiving/row locking, and expose the trusted-origin start route.
- [ ] Keep `active_weekly_plan` tracking eligibility date-gated and let future explicit starts remain active with timeline `scheduled_start`.
- [ ] Run `uv run pytest tests/nutrition/test_plan_start_api.py tests/nutrition/test_tracking_api.py tests/nutrition/test_adherence_api.py tests/nutrition/test_bundle_selection.py -q`.
- [ ] Commit `feat: require explicit nutrition plan start` and push.

### Task 6: Backend program timeline read model

**Files:**
- Create: `backend/app/program_timeline/__init__.py`
- Create: `backend/app/program_timeline/schemas.py`
- Create: `backend/app/program_timeline/service.py`
- Create: `backend/app/program_timeline/router.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/program_timeline/__init__.py`
- Create: `backend/tests/program_timeline/test_service.py`
- Create: `backend/tests/program_timeline/test_api.py`

**Interfaces:**
- Produce `GET /api/v1/program-timeline/today` with optional validated timezone query.
- Produce the strict workout/nutrition state enums and root response specified by the contract.

- [ ] Add failing service/API tests for every workout and nutrition state, Sunday-to-Monday scheduling, missing Wednesday overdue precedence, completion, legacy cycle, Day 8, timezone boundary, ownership, and invalid query timezone.
- [ ] Run `uv run pytest tests/program_timeline -q` and confirm red failures.
- [ ] Implement current-plan joins, exact-session precedence, next-session selection, legacy handling, selected nutrition plan resolution, modulo day mapping, and device-timezone override.
- [ ] Register the router without disturbing dynamic route order.
- [ ] Run `uv run pytest tests/program_timeline -q` plus focused backend static checks.
- [ ] Commit `feat: expose unified program timeline read model` and push.

### Task 7: OpenAPI and shared core contracts

**Files:**
- Generated: `contracts/openapi.json`
- Create: `packages/fitician-core/src/local-date.ts`
- Create: `packages/fitician-core/src/local-date.test.ts`
- Create: `packages/fitician-core/src/program-timeline.ts`
- Modify: `packages/fitician-core/src/index.ts`
- Modify: `packages/fitician-core/src/workouts.ts`
- Modify: `packages/fitician-core/src/nutrition.ts`
- Modify: `packages/fitician-core/package.json`

**Interfaces:**
- Produce local date/timezone helpers and generated `ProgramTimelineToday` aliases.
- Add `weekday?: number | null`, `ready_to_start`, `started_at`, and generated workout session/start types as needed.

- [ ] Add failing local-date boundary tests and compile references to the new generated schemas.
- [ ] Run the core test/build commands before implementation and confirm missing exports/types.
- [ ] Run `npm run generate:openapi`, export aliases/helpers and package subpaths, then use only generated output for API aliases.
- [ ] Run serially `npm run check:openapi`, `npm run test:contracts`, `npm run build:core`, and `npm run test:core`.
- [ ] Commit `feat: publish program timeline core contracts` and push.

### Task 8: Web APIs, timezone lifecycle, and timeline query

**Files:**
- Create: `frontend/src/features/programTimeline/api.ts`
- Create: `frontend/src/features/programTimeline/types.ts`
- Modify: `frontend/src/features/profile/api.ts`
- Modify: `frontend/src/features/profile/ProfileContext.tsx`
- Modify: `frontend/src/features/workouts/api.ts`
- Modify: `frontend/src/features/nutrition/api.ts`
- Modify: `frontend/src/features/workouts/types.ts` if generated aliases are needed
- Tests: corresponding web API/profile tests

**Interfaces:**
- Produce `getProgramTimelineToday`, `updateTimezone`, workout session mutations, and `startNutritionPlan` using `shared/apiClient`.
- Use `resolvedIanaTimeZone` for every timeline/start request and one identity/timezone `useRef` key for persistence suppression.

- [ ] Add failing URL/method/payload tests and a ProfileContext timezone-sync test for duplicate suppression, identity changes, and non-blocking failures.
- [ ] Run the affected web API/profile tests and confirm red failures.
- [ ] Implement the thin API modules, explicit timezone query encoding, and best-effort effect.
- [ ] Run focused API/profile tests and `npm run build --workspace frontend`.
- [ ] Commit `feat: add web program timeline transport` and push.

### Task 9: Web workout plan and dashboard behavior

**Files:**
- Modify: `frontend/src/features/workouts/WorkoutPlanPage.tsx`
- Modify: `frontend/src/features/workouts/workoutPlan.css`
- Modify: `frontend/src/features/workouts/WorkoutPlanPage.test.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/pages/DashboardPage.test.tsx`
- Modify: `packages/fitician-core/src/i18n/fa.ts`
- Modify: `packages/fitician-core/src/i18n/en.ts` if those files own the relevant strings

**Interfaces:**
- Focus workout presentation by timeline session IDs, preserve historical read-only behavior and weekly check-ins, and render explicit start/rest/overdue/completed/legacy states.
- Use timeline nutrition totals/pattern day and `timeline.local_date` for dashboard tracking.

- [ ] Add failing regression tests for first-day mislabeling, start card, rest/actual next, actual focus, overdue actions, mutation refresh, historical isolation, check-in retention, Day 8 nutrition, and rest-day dashboard behavior.
- [ ] Run the focused WorkoutPlanPage/Dashboard tests and confirm red failures.
- [ ] Implement state-driven presentation and refetches without broad visual redesign.
- [ ] Run the focused web suite, nutrition tests, build, and affected lint.
- [ ] Commit `feat: drive web workout and dashboard from program timeline` and push.

### Task 10: Web nutrition plan and local calendar behavior

**Files:**
- Modify: `frontend/src/features/nutrition/NutritionEstimatePage.tsx`
- Modify: `frontend/src/features/nutrition/WeeklyNutritionPlan.tsx`
- Modify: `frontend/src/features/nutrition/NutritionTrackingPage.tsx`
- Modify: `frontend/src/features/nutrition/api.ts`
- Modify: related nutrition tests and CSS only where required

**Interfaces:**
- Fetch one timeline at parent scope, pass recurring pattern state into the plan component, and preserve manual day browsing after initial anchoring.

- [ ] Add failing tests for ready start UI, future state, initial pattern selection on Day 9, post-edit selection preservation, and local-date tracking requests.
- [ ] Run relevant web nutrition tests and confirm red failures.
- [ ] Implement explicit start controls, query invalidation/refetch, timeline anchoring, and replace only member-calendar UTC ISO derivations.
- [ ] Run focused nutrition tests, frontend build, and affected lint.
- [ ] Commit `feat: add web nutrition program start and recurring day view` and push.

### Task 11: Mobile transport, timezone sync, and presentation models

**Files:**
- Create: `mobile/programTimeline/programTimelineApi.ts`
- Create: `mobile/programTimeline/programTimelineModel.ts`
- Create: corresponding API/model tests
- Modify: `mobile/data/queryKeys.ts`
- Modify: `mobile/profile/profileApi.ts`
- Modify: `mobile/ui/navigation/RouteGuards.tsx`
- Modify: `mobile/workouts/workoutCycleApi.ts`
- Modify: `mobile/workouts/workoutCycleModel.ts`
- Modify: `mobile/home/homeModel.ts`

**Interfaces:**
- Produce generated-schema mobile timeline/start/session APIs, `programTimelineKeys`, best-effort timezone sync, and pure workout/home presentation helpers.

- [ ] Add failing API/query/model tests for timezone query/payloads, all presentation states, rest vs first day, overdue/today/next, and auth identity retry behavior.
- [ ] Run focused mobile unit tests and confirm red failures.
- [ ] Implement generated aliases, authenticated transport calls, invalidation-ready keys, and pure state mapping.
- [ ] Run focused mobile tests, `npm run build:core`, and `npm run typecheck:mobile`.
- [ ] Commit `feat: add mobile program timeline data layer` and push.

### Task 12: Mobile workout and nutrition UI integration

**Files:**
- Modify: `mobile/workouts/WorkoutPlansScreen.tsx`
- Modify: `mobile/workouts/WorkoutCyclePanel.tsx`
- Modify: `mobile/home/MemberHomeScreen.tsx`
- Modify: `mobile/nutrition/nutritionPlanApi.ts`
- Modify: `mobile/nutrition/NutritionPlanSection.tsx`
- Modify: `mobile/nutrition/NutritionTodayMeals.tsx`
- Modify: `mobile/nutrition/NutritionSummaryCard.tsx`
- Modify: `mobile/nutrition/NutritionTrackingSection.tsx`
- Modify: `mobile/nutrition/NutritionAdherenceSection.tsx`
- Modify: affected RNTL/native contract tests

**Interfaces:**
- Use the timeline query as the sole workout day focus/current-state source and use pattern index/local date for nutrition, while retaining weekly check-ins, replacements, feedback, and history.

- [ ] Add failing RNTL/native tests for explicit starts, rest/overdue/completed/legacy states, actual session focus/actions, historical isolation, Day 8 meals/summary, and no duplicated local-date helpers.
- [ ] Run the affected mobile tests and confirm red failures.
- [ ] Integrate queries/mutations with React Query invalidation and existing Fitician tokens/components; update structural contract assertions intentionally.
- [ ] Run focused programTimeline/home/workouts/nutrition/profile/navigation tests, native contract tests, `npm run typecheck:mobile`, and mobile validation.
- [ ] Commit `feat: integrate program timeline into mobile member flows` and push.

### Task 13: Final focused verification and assumption audit

**Files:**
- Inspect only: backend, core, frontend, and mobile files changed above; no unrelated cleanup.

- [ ] Run the complete focused backend sequence from the specification, including workout review, nutrition, timeline, migration, and static checks.
- [ ] Run serial OpenAPI/core verification and focused web verification, then the affected broad mobile suite and native contracts.
- [ ] Search and classify `plan?.days?.[0]`, `plan.days[0]`, `dayIndex === 0`, and `toISOString().slice(0, 10)`; remove only member-calendar/current-workout uses and document safe remaining cases.
- [ ] Verify all acceptance scenarios A–J with tests or explicit evidence, inspect `git diff`/`git status`, and confirm no secrets or unrelated files are staged.
- [ ] Commit any final feature-only verification repair as a specific Conventional Commit and push; mark the implementation complete only after fresh command output confirms it.
