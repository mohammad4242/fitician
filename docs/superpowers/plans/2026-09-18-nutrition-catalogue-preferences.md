# Catalogue-backed nutrition preferences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make nutrition preferences canonical Food/Meal Catalogue selections and enforce them through verified persistence, planning, substitutions, budget repair, and Web/Mobile onboarding.

**Architecture:** Extend the existing `NutritionFoodItem` snapshot with a nullable meal foreign key and typed API projections. Centralize combined catalogue search in one public cached backend service. Thread canonical profile and feedback identities through the immutable planner snapshot, then enforce them at eligibility, substitution, repair, and final validation boundaries.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, pytest; React/TypeScript/Vitest; React Native/RNTL; shared TypeScript core and generated OpenAPI.

**Spec:** `docs/superpowers/specs/2026-09-18-nutrition-catalogue-preferences-design.md`

## Global Constraints

- Only verified, non-retired catalogue rows may be selected or resolved.
- New preference writes persist one canonical food-or-meal identity per row; historical unresolved rows remain readable.
- Client labels are display-only; backend names always come from the database.
- Allergies and intolerances are hard; dislikes are strict normal-plan avoidance; meal constraints never expand to ingredient constraints.
- Existing feedback, dietary, nutrient, budget, and repetition behavior remains active.
- No unrelated dirty-worktree artifacts are staged.
- Every logical step has a failing test, focused verification, a specific Conventional Commit, and a push when the remote is available.

### Task 1: Backend canonical target contract and migration

**Files:**
- Modify: `backend/app/nutrition/models.py`, `backend/app/nutrition/schemas.py`, `backend/app/nutrition/service.py`
- Create: `backend/alembic/versions/20260918_159_add_catalogue_meal_targets_to_nutrition_preferences.py`
- Test: `backend/tests/nutrition/test_nutrition_api.py`

**Interfaces:**
- Produce `NutritionCatalogueTargetInput`, `NutritionCatalogueConstraintInput`, and response target models.
- Produce bulk target validation and structured domain errors.

- [ ] Add API tests for valid food/meal targets, invalid IDs/types/status, duplicates, conflicts, and legacy rejection.
- [ ] Run the new tests red.
- [ ] Add the meal FK, XOR/check/index model metadata and current-head migration.
- [ ] Implement bulk verification, canonical snapshot names, legacy exact-match resolution, and deprecated response projections.
- [ ] Run focused API tests, Alembic upgrade/head checks, Ruff, and mypy.
- [ ] Commit `feat(nutrition): persist verified food and meal preference targets` and push.

### Task 2: Combined public catalogue options endpoint

**Files:**
- Create: `backend/app/nutrition/catalogue_options.py`, `backend/tests/nutrition/test_catalogue_options.py`
- Modify: `backend/app/nutrition/router.py`, food/meal catalogue mutation invalidation paths

- [ ] Add search tests for Persian/English/name/alias/code, prefix ordering, limit, status filtering, and no private fields.
- [ ] Run them red.
- [ ] Implement bounded two-query search, deterministic ranking, cache serialization, and public route.
- [ ] Invalidate the namespace from catalogue mutations.
- [ ] Run endpoint tests and OpenAPI generation/check.
- [ ] Commit `feat(nutrition): add cached verified catalogue option search` and push.

### Task 3: Planner preference snapshot and hard/avoidance semantics

**Files:**
- Modify: `backend/app/nutrition/preference_snapshot.py`, `plan_service.py`, `planner_engine.py`, `template_substitution.py`, `budget_optimizer.py`, `candidate_selection.py`, `food_constraints.py`, `planner_policy.py`
- Test: `backend/tests/nutrition/test_preference_snapshot.py`, `test_food_constraints.py`, `test_planner_engine.py`, `test_template_substitution.py`, `test_budget_optimizer.py`

- [ ] Add failing unit and end-to-end tests for food/meal boosts, strict dislike, food/meal hard blocks, recipes, impossible avoidance, repetition, safety precedence, and budget repair.
- [ ] Run focused tests red.
- [ ] Add exact food IDs to normalized constraints and canonical profile sets to snapshots/inputs.
- [ ] Filter before ranking, rank favourites deterministically, pass context to substitutions and budget repair, and add final defense validation.
- [ ] Run all focused planner tests plus unhandled-profile regression.
- [ ] Commit `feat(nutrition): enforce catalogue preferences in plan generation` and push.

### Task 4: Shared contracts and OpenAPI

**Files:**
- Modify: `packages/fitician-core/src/nutrition.ts`, `packages/fitician-core/src/onboarding.ts`, generated contract via script

- [ ] Add core canonical target and input types and canonical profile fields.
- [ ] Run backend OpenAPI export and core contract tests.
- [ ] Build core and check generated OpenAPI.
- [ ] Commit `feat(core): add canonical nutrition catalogue contracts` and push.

### Task 5: Web picker and onboarding/profile/draft integration

**Files:**
- Create: `frontend/src/features/nutrition/CatalogueTargetMultiSelect.tsx`, its test
- Modify: `frontend/src/features/nutrition/api.ts`, `types.ts`, `nutritionOnboarding.css`, `NutritionOnboardingFlow.tsx`, `ProfilePage.tsx`, `publicOnboarding/onboardingDraft.ts`, related tests

- [ ] Add failing picker and flow tests for search/loading/errors, keyboard selection, chips, duplicate/arbitrary rejection, hydration, and ID-only payloads.
- [ ] Run them red.
- [ ] Implement the accessible debounced picker and canonical state/draft hydration.
- [ ] Run Web focused tests, typecheck, lint, and build.
- [ ] Commit `feat(web): replace nutrition preference text fields with catalogue picks` and push.

### Task 6: Native picker and onboarding/profile integration

**Files:**
- Create: `mobile/nutrition/CatalogueTargetPicker.tsx`, focused tests
- Modify: `mobile/nutrition/nutritionApi.ts`, `nutritionCatalogueApi.ts`, `mobile/data/queryKeys.ts`, onboarding/profile models and screens, related tests

- [ ] Add failing native model/API/picker tests for search, sheet selection, chips, accessibility, hydration, and ID-only payloads.
- [ ] Run them red.
- [ ] Implement the shared Sheet-based picker and canonical form state without comma splitting.
- [ ] Run mobile tests, native typecheck, core build, and relevant contract checks.
- [ ] Commit `feat(mobile): add shared catalogue preference picker` and push.

### Task 7: Full verification and handoff

**Files:**
- No production files unless verification exposes a scoped regression.

- [ ] Run the complete focused backend list, Ruff, mypy, migration checks, OpenAPI generation/check, core tests/build, frontend tests/build/lint, and mobile tests/typecheck.
- [ ] Inspect `git diff`, `git status`, commit history, and staged paths.
- [ ] Push the current branch and report exact evidence and any genuine remaining gaps.
