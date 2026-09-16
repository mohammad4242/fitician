# Specialist Workbench UI Implementation Plan

> Execution checklist for the Specialist Workbench redesign.

**Goal:** Turn the Coach and Physician review routes into compact, responsive Specialist Workbenches while preserving every existing review API and action.

**Architecture:** A presentation-only shared workbench layer owns the shell, four-section navigation, stats, compact case list, case header, and localized status badge. Coach and Physician keep separate orchestrators and domain components for queue loading, case data, editing, labs, supplements, notes, and final actions. The active section is stored in `?section=` without changing either route.

**Tech Stack:** React 19, TypeScript strict, React Router, Testing Library, Vitest, Playwright, existing Fitician CSS tokens and i18n.

**Spec:** User-provided Specialist Workbench redesign brief in this task.

## Global Constraints

- Preserve `/coach/workouts` and `/physician/nutrition` exactly.
- Change `frontend/` only; do not touch `mobile/` or `backend/` unless an essential missing field is proven.
- Keep existing claim, save-draft, correction, approve, reject, lab, food-edit, and supplement API calls and payloads.
- Never render raw backend statuses or production raw JSON snapshots.
- Keep RTL and English copy, semantic tabs, keyboard focus, empty/loading/error states, safe areas, and no fixed action overlay.
- Use client-side search and sorting over the currently loaded queue data.
- Run targeted tests after each logical task, then commit only that task's files and push when the remote is available.
- Follow TDD for new UI behavior: add a failing test, verify the expected failure, implement, then verify green.

## File Map

- Create `frontend/src/shared/specialistWorkbench/{types.ts,SpecialistWorkbenchShell.tsx,SpecialistWorkbenchNav.tsx,SpecialistStatsGrid.tsx,SpecialistCaseList.tsx,SpecialistCaseHeader.tsx,SpecialistStatusBadge.tsx,specialistWorkbench.css}` for reusable presentation.
- Create Coach section components under `frontend/src/features/workoutReviews/` and keep API/domain helpers there.
- Create Physician section components and `physicianWorkspace.css` under `frontend/src/features/nutrition/`.
- Keep general nutrition rules in `nutritionEstimate.css`; move only the Physician workspace rules.
- Extend the existing feature tests and add `frontend/src/shared/specialistWorkbench/SpecialistWorkbench.test.tsx`.
- Update only the specialist selectors in `frontend/e2e/specialist-multirole.spec.ts`.

### Task 0: Baseline and plan

**Files:** `docs/superpowers/plans/2026-09-16-specialist-workbench-ui.md`

- [x] Read the requested Coach, Physician, shared, route, E2E, core, API, and type files.
- [x] Search tracked uses of `.coach-review-*`, `.physician-review-*`, and `.physician-clinical-*`.
- [x] Record baseline: Coach 18/18, Physician 33/33, specialist E2E 4/4 passed.

### Task 1: Shared workbench primitives

**Files:**
- Create: `frontend/src/shared/specialistWorkbench/*`
- Test: `frontend/src/shared/specialistWorkbench/SpecialistWorkbench.test.tsx`

**Interfaces:**
- `SpecialistWorkbenchNav` accepts the four section keys, localized labels, active key, and `onChange`; it renders an accessible `tablist`.
- `SpecialistStatsGrid` accepts `{label, value, hint?, tone?}[]` and renders compact statistic items.
- `SpecialistCaseList<T>` accepts items, localized search/sort controls, a `getSearchText` function, a sorted `renderItem`, and explicit loading/empty content.
- `SpecialistCaseHeader` accepts avatar/name, localized status context, metadata, and a back callback.
- `SpecialistStatusBadge` maps `pending`, `claimed`/`in_review`, `approved`, `awaiting_member_acceptance`, `superseded`, and contextual `rejected` to user-facing labels and tones; unknown values use a safe localized fallback.
- `SpecialistWorkbenchShell` composes the page heading, shared navigation, optional stats, error region, and section content without domain logic.

- [x] Add tests for navigation state, status context labels, RTL direction, empty list, compact case rendering, and no raw status fallback.
- [x] Run the shared test and the two existing feature tests.
- [x] Implement the primitives and CSS with scrollable mobile navigation, focus-visible styling, compact desktop rows, and no fixed action positioning.
- [x] Commit `ebd8a302 feat(web): add shared specialist workbench primitives` and push.

### Task 2: Coach workbench orchestration

**Files:**
- Modify: `frontend/src/features/workoutReviews/CoachWorkoutReviewPage.tsx`
- Create: `CoachDashboard.tsx`, `CoachReviewQueue.tsx`, `CoachReviewCase.tsx`, and a small editor component only if needed.
- Modify: `frontend/src/features/workoutReviews/coachWorkoutReview.css`
- Test: `frontend/src/features/workoutReviews/CoachWorkoutReviewPage.test.tsx`

**Interfaces:**
- The page owns queue loading, selected detail, draft state, lease renewal, and unchanged API callbacks.
- `CoachDashboard` receives pending/mine/approved arrays and opens `queue`, `mine`, or `history` through the shared navigation.
- `CoachReviewQueue` receives one queue and opens a case through the existing claim/detail callback; it owns client-side name search and newest/oldest sorting.
- `CoachReviewCase` receives the selected detail plus existing draft/editor callbacks and renders Summary, Profile, Workout, Feedback, and Notes tabs.

- [x] Add feature assertions for default Dashboard, `Promise.all` counts, needs-action/recent sections, four navigation sections, search/sort, case tabs, and mobile queue-to-case separation.
- [x] Extract the current Coach markup and callbacks without changing API paths, payloads, revision handling, or edit controls.
- [x] Render compact queue rows with goal, experience, time, localized status, and action.
- [x] Render the case header and tabs; place final actions at the end of the review content and keep them non-fixed.
- [x] Run `npm test -- CoachWorkoutReviewPage.test.tsx` and commit `b9e3e6d4 feat(web): restructure coach reviews as a specialist workbench`.
- [x] Push the commit.

### Task 3: Physician workbench orchestration

**Files:**
- Modify: `frontend/src/features/nutrition/PhysicianNutritionReviewPage.tsx`
- Create: `PhysicianDashboard.tsx`, `PhysicianReviewQueue.tsx`, `PhysicianReviewCase.tsx`, `physicianWorkspace.css`.
- Modify: `frontend/src/features/nutrition/nutritionEstimate.css`
- Test: `frontend/src/features/nutrition/NutritionWorkflowPages.test.tsx`

**Interfaces:**
- The page keeps the existing `Promise.all` load of pending/claimed/approved plus catalogue loading and all current action callbacks.
- `PhysicianDashboard` receives the three queues and derives counts, real overdue attention, priority ordering, and recent activity.
- `PhysicianReviewQueue` receives a queue and opens the existing `claimPhysicianReview`/plan loading flow; sorting is priority, oldest, or newest.
- `PhysicianReviewCase` receives plan, review metadata, labs, orders, catalogues, notes, and callbacks and renders Summary, Nutrition, Labs, Supplements, and Notes.

- [x] Add feature assertions for dashboard counts/overdue attention, four navigation sections, search/sort, case tabs, all clinical data, actions, hidden raw status, and hidden raw JSON.
- [x] Extract the current case UI and preserve all API calls, including food quantity/replacement, lab review/request, supplement CRUD/transition, and plan actions.
- [x] Replace the production `<pre>` with localized key/value rows and disclosures for input snapshot, budget, price snapshot, provenance, and safety data; omit absent values.
- [x] Map all visible statuses through `SpecialistStatusBadge`, including final Physician rejection wording.
- [x] Run `npm test -- NutritionWorkflowPages.test.tsx`, commit `3684272a feat(web): rebuild physician nutrition review as specialist workbench`, and push.

### Task 4: Visual and responsive pass

**Files:**
- Modify: `frontend/src/features/workoutReviews/coachWorkoutReview.css`
- Create/modify: `frontend/src/features/nutrition/physicianWorkspace.css`
- Modify: `frontend/src/features/nutrition/nutritionEstimate.css` only to remove moved Physician rules.
- Test: shared and feature tests plus CSS assertions.

- [x] Add CSS assertions for no fixed action bar and compact list/case behavior.
- [x] Implement the shared dark-green/turquoise visual system with restrained borders/glow and dense hierarchy.
- [x] Verify responsive rules for desktop, tablet, and mobile queue/case layouts, including scrollable nav/tabs, safe-area padding, and touch-sized controls.
- [x] Run targeted tests, `npm run lint`, and `npm run build`.

### Task 5: Accessibility and regression coverage

**Files:**
- Modify: `CoachWorkoutReviewPage.test.tsx`, `NutritionWorkflowPages.test.tsx`, `SpecialistWorkbench.test.tsx`
- Modify: changed components/CSS only where tests expose an issue.

- [x] Cover keyboard-accessible tabs with `aria-selected`, visible focus, localized labels, empty/loading/error states, avatar labels, and status text independent of color.
- [x] Re-run the focused Coach and Physician suites until fully green without weakening existing assertions.
- [x] Commit `2daae5ab feat(web): add keyboard navigation for specialist case tabs` and push.

### Task 6: E2E adaptation and final verification

**Files:** `frontend/e2e/specialist-multirole.spec.ts`

- [x] Update E2E locators to semantic roles and stable `data-testid` values for workbench sections, case rows, case header, tabs, and actions; keep API/database assertions unchanged.
- [x] Run `npx playwright test e2e/specialist-multirole.spec.ts` against the dedicated E2E setup and fix production selector/behavior issues only.
- [x] From `frontend/`, run the required Coach test, Physician test, lint, build, and specialist E2E; run the additional focused shared test.
- [x] Inspect `git diff`, confirm no `mobile/` or backend changes, and commit `49111109 test(e2e): align physician specialist flow with workbench`.
- [x] Push the final commit and report implementation, verification, and API limitations.

## Completion evidence

- Focused tests: Coach `22/22`, Physician `37/37`, Shared `6/6`.
- Verification: `npx tsc -b --pretty false`, `npm run lint` (exit 0 with existing warnings), `npm run build`, and specialist E2E `4/4` across Chromium/WebKit.
- Scope: frontend only; no backend or native/mobile files changed. Existing API endpoints and review payloads remain in use.
