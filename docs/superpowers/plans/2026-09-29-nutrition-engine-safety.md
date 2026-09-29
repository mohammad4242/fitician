# Nutrition Engine Safety Implementation Plan

> Execution: main agent, using executing-plans and test-driven-development.

**Goal:** Correct all twelve verified nutrition audit findings.
**Architecture:** One shared admission policy for planner results and stored edits.
Safety remains deterministic; presentation uses immutable nutrition snapshots.
**Tech Stack:** Python/FastAPI/SQLAlchemy, TypeScript/React/React Native.
**Spec:** ../specs/2026-09-29-nutrition-engine-safety-design.md

## Global Constraints

Preserve unrelated dirty files. No deployment. No fabricated nutrient values.
Do not diagnose deficiency from RDA comparisons. Keep actual intake separate.

## Review Focus

- Canonical allergies and prepared recipes with missing metadata.
- Multiple active supplements and total-intake versus supplemental-only limits.
- Removed meals, incompatible replacements, and historical plan snapshots.
- Free meal reservations alongside daily macro and energy admission.
- Coherent rapid trends, isolated outliers, and incomplete adherence records.

## Tasks

### 1. Safety and arithmetic
Files: food_constraints.py, supplement_service.py, weight_rate_policy.py,
plan_editing.py; focused nutrition regression tests.
- [x] Write and run failing regressions for findings 1, 2, 4, 12.
- [x] Correct allergen propagation, exposure units, bounded overrides, fat mapping.
- [x] Run focused tests and commit only owned changes.

### 2. Shared plan admission and edits
Files: shared plan validation module, planner_engine.py, planner_policy.py,
plan_editing.py, budget_optimizer.py, plan_service.py; planner/edit tests.
- [x] Reproduce findings 3, 5, 6, 7, 10, 11 with failing tests.
- [x] Implement energy reservations and shared daily/weekly admission.
- [x] Validate edits atomically and offer compatible bounded replacements.
- [x] Exercise alternative candidates and explicit unresolved quality outcomes.
- [x] Run planner, budget, candidate, and edit tests; commit owned changes.

### 3. Progress and quantity presentation
Files: progress_review.py, planner/plan snapshots and schemas, nutrition PDF,
shared types, Web and Mobile nutrition views; corresponding tests.
- [x] Reproduce findings 8 and 9 with failing tests.
- [x] Expose coherent rapid trends and immutable measurement basis.
- [x] Run progress, response, PDF and platform tests; commit owned changes.

### 4. End-to-end validation
- [x] Run full focused nutrition suite and relevant lint/type checks.
- [x] Trace realistic profiles including allergies, deficits, gains, and free meals.
- [x] Review owned diff and preserve existing WIP; push verified commits.
