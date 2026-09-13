# Product Entitlements and Quotas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Implement the first persisted Product, Entitlement, and Quota layer across Fitsho backend, database, shared contracts, Web, and shared React Native screens.

**Architecture:** Add an independent app/entitlements domain with an immutable code catalog, implicit Free fallback, unioned active grants, and transactional idempotent quota events. Feature domains receive explicit capability/lifecycle decisions and retain ProductMode onboarding and specialist-role authorization. Web and Mobile consume one authenticated shared snapshot through providers.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest, TypeScript, React 19, Vite, Vitest, React Native, Expo Router, React Native Testing Library.

**Spec:** docs/superpowers/specs/2026-09-12-product-entitlements-design.md

## Global Constraints

- Keep ProductMode exactly training, nutrition, and both; it remains onboarding/application routing state.
- Keep coach/physician SpecialistRole and UserSpecialistRole checks for specialist workspaces.
- Free access includes account/profile/onboarding, catalogue reads, manual tracking, existing plan/history/result reads, own-data access, deletion, and export.
- Do not add payment, prices, checkout, billing, invoice, transaction, refund, renewal, or provider tables/fields.
- Do not use package codes in feature authorization; check EntitlementCode capabilities.
- Use ON DELETE CASCADE for entitlement rows owned by users.
- Low-level entitlement/quota helpers do not commit; feature state and usage events commit atomically.
- Run backend commands from backend/ with uv run; run frontend and Mobile commands from their package directories.
- Each task follows Red-Green-Refactor: write a focused failing test, observe the expected failure, implement the smallest change, rerun the focused suite, then commit and push.
- Preserve dirty WIP and stage only named files for each commit.

## File Map

### Backend domain and database

- Create backend/app/entitlements/__init__.py: public domain exports.
- Create backend/app/entitlements/enums.py: stable package, package-kind, grant-source, and entitlement codes.
- Create backend/app/entitlements/catalog.py: immutable package definitions and the one-location quota policy map.
- Create backend/app/entitlements/models.py: UserAccessGrant and EntitlementUsageEvent ORM models.
- Create backend/app/entitlements/schemas.py: catalog, grant, quota, trial, and snapshot response schemas.
- Create backend/app/entitlements/exceptions.py: entitlement and quota domain errors.
- Create backend/app/entitlements/service.py: resolution, authorization, grants, Launch Trial, and quota transactions.
- Create backend/app/entitlements/dependencies.py: authenticated snapshot and capability dependency helpers.
- Create backend/app/entitlements/router.py: /api/v1/products and /api/v1/entitlements/me.
- Modify backend/alembic/env.py: import entitlement models for metadata registration.
- Create backend/alembic/versions/20260912_140_create_product_entitlements.py after rechecking the current Alembic head.
- Modify backend/app/main.py: register the router and global entitlement exception handlers.

### Backend integrations

- Modify backend/app/auth/service.py: provision Launch Trial only in new-account branches.
- Modify backend/app/workouts/router.py, service.py, repository.py, and signature.py: capability authorization, explicit review policy, direct-active versus coach-review lifecycle, and coach quota.
- Modify backend/app/nutrition/router.py, plan_service.py, plan_editing.py, and schemas.py: final-bundle selection review policy, safety entitlement errors, plan-management writes, food-photo access, clinical member writes, and additive response fields.
- Modify backend/app/body_photos/router.py, backend/app/body_analysis/router.py, and backend/app/body_analysis/service.py: Body Analysis entitlement preflight and idempotent seven-day quota.

### Shared/client layers

- Create packages/fitician-core/src/entitlements.ts and packages/fitician-core/src/entitlements.contract.test.ts.
- Modify packages/fitician-core/src/index.ts, packages/fitician-core/package.json, packages/fitician-core/src/i18n/fa.ts, and packages/fitician-core/src/i18n/en.ts.
- Create frontend/src/features/entitlements/api.ts, EntitlementContext.tsx, EntitlementGate.tsx, and focused tests.
- Modify frontend/src/App.tsx, shared/AppShell.tsx, Dashboard, workout, nutrition, Body Analysis, More, and their focused tests.
- Create mobile/entitlements/entitlementApi.ts, EntitlementProvider.tsx, EntitlementGate.tsx, and focused tests.
- Modify mobile/app/_layout.tsx, member tab/navigation, Home, workout, nutrition, Body Analysis, More, and focused tests.

### Test scope

- Create backend tests/entitlements/test_catalog.py, test_service.py, test_api.py, test_quota.py, test_launch_trial.py, and tests/database/test_entitlement_models.py.
- Update affected auth, workout/review, nutrition, Body Analysis, core, Web, and Mobile tests without weakening unrelated assertions.

---

### Task 1: Add the stable Entitlement catalog

**Files:**
- Create: backend/app/entitlements/__init__.py
- Create: backend/app/entitlements/enums.py
- Create: backend/app/entitlements/catalog.py
- Test: backend/tests/entitlements/test_catalog.py

**Interfaces:**
- Produces AccessPackageCode, AccessPackageKind, GrantSource, and EntitlementCode as StrEnum values.
- Produces frozen QuotaPolicy and PackageDefinition values, PACKAGE_CATALOG, QUOTA_POLICIES, package_definition(), and eligible_upgrade_packages().
- The exact package codes are free, training, training_coach, nutrition, nutrition_physician, complete, complete_care, and launch_trial.

- [ ] **Step 1: Write the failing catalog tests.** Assert the exact entitlement sets for every package, the three quota policies, package kind/purchasability, Complete’s exclusion of both human-review capabilities, and Launch Trial’s Complete Care-equivalent set.

~~~python
def test_catalog_matches_the_product_matrix() -> None:
    assert package_definition(AccessPackageCode.TRAINING).entitlements == frozenset({
        EntitlementCode.TRAINING_PLAN_GENERATE,
        EntitlementCode.TRAINING_CYCLE_MANAGE,
        EntitlementCode.BODY_ANALYSIS_RUN,
    })
    assert EntitlementCode.TRAINING_COACH_REVIEW not in package_definition(
        AccessPackageCode.COMPLETE
    ).entitlements
    assert package_definition(AccessPackageCode.LAUNCH_TRIAL).entitlements == package_definition(
        AccessPackageCode.COMPLETE_CARE
    ).entitlements
~~~

- [ ] **Step 2: Run the tests and verify the expected missing-domain failure.**

Run: uv run pytest tests/entitlements/test_catalog.py -q

Expected: collection fails because app/entitlements and its catalog symbols do not yet exist.

- [ ] **Step 3: Implement the immutable catalog.** Define the exact code values, make package definitions frozen, use frozenset entitlements, expose only the decided quota policies, and derive package quota responses from QUOTA_POLICIES.

- [ ] **Step 4: Run the focused catalog suite.**

Run: uv run pytest tests/entitlements/test_catalog.py -q

Expected: all catalog tests pass.

- [ ] **Step 5: Commit and push.**

~~~bash
git add backend/app/entitlements/__init__.py backend/app/entitlements/enums.py backend/app/entitlements/catalog.py backend/tests/entitlements/test_catalog.py
git commit -m "feat(entitlements): define access package catalog"
git push origin main
~~~

### Task 2: Add persisted grant and usage-event models

**Files:**
- Create: backend/app/entitlements/models.py
- Modify: backend/alembic/env.py
- Test: backend/tests/database/test_entitlement_models.py

**Interfaces:**
- Produces UserAccessGrant with UUID primary key, user cascade FK, package/source strings, timezone-aware start/end/revocation fields, nullable idempotency key, and created timestamp.
- Produces EntitlementUsageEvent with UUID primary key, user cascade FK, entitlement/resource keys, timezone-aware occurred/created timestamps, unique resource consumption, and the (user_id, entitlement_key, occurred_at) index.

- [ ] **Step 1: Write failing metadata/model tests.** Assert both table names, columns, user foreign keys with cascade, nullable Launch Trial idempotency key, the two uniqueness constraints, and the rolling-count index.

~~~python
def test_entitlement_usage_event_has_idempotent_resource_constraint() -> None:
    table = EntitlementUsageEvent.__table__
    assert any(
        constraint.name == "uq_entitlement_usage_events_user_entitlement_resource"
        and {column.name for column in constraint.columns}
        == {"user_id", "entitlement_key", "resource_key"}
        for constraint in table.constraints
    )
~~~

- [ ] **Step 2: Run the model test to observe the expected missing-table failure.**

Run: uv run pytest tests/database/test_entitlement_models.py -q

Expected: collection or assertion failure because the models are absent.

- [ ] **Step 3: Implement the two models and metadata import.** Use the repository’s Mapped/mapped_column style, explicit String lengths, DateTime(timezone=True), ForeignKey("users.id", ondelete="CASCADE"), and named constraints/indexes. Do not add speculative payment columns.

- [ ] **Step 4: Run model/lint checks.**

Run: uv run pytest tests/database/test_entitlement_models.py -q

Expected: model metadata tests pass.

- [ ] **Step 5: Commit and push.**

~~~bash
git add backend/app/entitlements/models.py backend/alembic/env.py backend/tests/database/test_entitlement_models.py
git commit -m "feat(entitlements): add access grant and usage models"
git push origin main
~~~

### Task 3: Create and verify the Alembic migration

**Files:**
- Create: backend/alembic/versions/20260912_140_create_product_entitlements.py (or the next valid revision if the head changed)
- Test: backend/tests/database/test_entitlement_models.py

**Interfaces:**
- Produces the actual next migration from the audited current head, 20260912_139 at planning time; recheck uv run alembic heads immediately before creation and use the real current revision if it has advanced.

- [ ] **Step 1: Extend the failing database test with an actual PostgreSQL round-trip.** Assert alembic upgrade head creates both tables and that duplicate semantic usage events and duplicate non-null user/idempotency pairs are rejected while multiple null idempotency keys are allowed.

- [ ] **Step 2: Run the focused migration/model test before the migration exists.**

Run: uv run pytest tests/database/test_entitlement_models.py -q

Expected: failure because the current database has no entitlement tables.

- [ ] **Step 3: Recheck the migration head and write the migration.** Create both tables, all foreign keys, indexes, named uniqueness constraints, and downgrade drops in reverse dependency order. Never edit migration 20260912_139.

Run: uv run alembic heads

- [ ] **Step 4: Verify upgrade and downgrade/upgrade safety.**

Run: uv run alembic upgrade head

Run the repository-supported downgrade/upgrade check at the new revision, then run: uv run pytest tests/database/test_entitlement_models.py -q

Expected: upgrade succeeds, downgrade and re-upgrade succeed where the test database permits it, and model tests pass.

- [ ] **Step 5: Commit and push.**

~~~bash
git add backend/alembic/versions/20260912_140_create_product_entitlements.py backend/tests/database/test_entitlement_models.py
git commit -m "feat(db): migrate product entitlement tables"
git push origin main
~~~

### Task 4: Implement access resolution and generic quotas

**Files:**
- Create: backend/app/entitlements/exceptions.py
- Create: backend/app/entitlements/service.py
- Create: backend/tests/entitlements/test_service.py
- Create: backend/tests/entitlements/test_quota.py

**Interfaces:**
- Produces AccessSnapshot, QuotaStatus, list_active_grants(), resolve_access_snapshot(), has_entitlement(), require_entitlement(), quota_status(), require_quota_available(), consume_quota(), and grant_package(). Signup Trial provisioning is owned by AccessCampaign.
- EntitlementRequiredError carries entitlement and eligible purchasable package codes.
- EntitlementQuotaExceededError carries entitlement, reset_at, and retry seconds.
- consume_quota() returns idempotently when the exact resource event already exists and never commits.

- [ ] **Step 1: Write failing service/quota tests.** Cover implicit Free, unioned active grants, expiry/revocation, paid-plus-trial union, primary-package ranking, rolling windows, reset time, duplicate resource idempotency, different-resource rejection, and a quota transaction that remains uncommitted until its caller commits.

~~~python
def test_same_resource_is_consumed_once(db: Session) -> None:
    user = make_user(db)
    grant_training_coach(db, user.id)
    assert consume_quota(
        db, user.id, EntitlementCode.TRAINING_COACH_REVIEW, "workout-plan:one"
    )
    assert not consume_quota(
        db, user.id, EntitlementCode.TRAINING_COACH_REVIEW, "workout-plan:one"
    )
    assert quota_status(db, user.id, EntitlementCode.TRAINING_COACH_REVIEW).used == 1
~~~

- [ ] **Step 2: Run the focused tests and verify expected missing-service failures.**

Run: uv run pytest tests/entitlements/test_service.py tests/entitlements/test_quota.py -q

Expected: failures because service symbols are absent.

- [ ] **Step 3: Implement resolution and authorization.** Always include Free in resolved packages, filter grants with starts_at <= now, revoked_at IS NULL, and (ends_at IS NULL OR ends_at > now), union capabilities, and rank only for display. Derive eligible upgrades from catalog definitions rather than package conditionals in feature modules.

- [ ] **Step 4: Implement transactional quota consumption.** Lock User with FOR UPDATE, look up the exact event, calculate window_start and the earliest-event reset, count current-window events, raise the domain error at the limit, or insert one event. Keep all changes pending for the caller transaction.

- [ ] **Step 5: Implement grant APIs.** Validate catalog codes, support arbitrary future normal grants, and use nullable (user_id, idempotency_key) idempotency. Signup Trial provisioning belongs to AccessCampaign.

- [ ] **Step 6: Run the focused suites.**

Run: uv run pytest tests/entitlements/test_service.py tests/entitlements/test_quota.py -q

Expected: all service/quota tests pass.

- [ ] **Step 7: Commit and push.**

~~~bash
git add backend/app/entitlements/exceptions.py backend/app/entitlements/service.py backend/tests/entitlements/test_service.py backend/tests/entitlements/test_quota.py
git commit -m "feat(entitlements): resolve access and enforce quotas"
git push origin main
~~~

### Task 5: Add the Entitlement API and standardized errors

**Files:**
- Create: backend/app/entitlements/schemas.py
- Create: backend/app/entitlements/dependencies.py
- Create: backend/app/entitlements/router.py
- Modify: backend/app/main.py
- Create: backend/tests/entitlements/test_api.py

**Interfaces:**
- Produces public GET /api/v1/products and authenticated GET /api/v1/entitlements/me.
- Produces CurrentAccessSnapshot and capability dependency helpers without requiring a completed profile.
- Maps missing capability to HTTP 403 and exhausted quota to HTTP 429 with structured details and Retry-After.

- [ ] **Step 1: Write failing API tests.** Cover catalog shape/no prices, unauthenticated snapshot rejection, incomplete-profile authenticated access, Free fallback, active trial/quotas, structured 403 fields, and structured 429/reset fields.

- [ ] **Step 2: Run the focused API tests before implementation.**

Run: uv run pytest tests/entitlements/test_api.py -q

Expected: import/route failures because the API is absent.

- [ ] **Step 3: Implement schemas and dependencies.** Serialize package code/kind/purchasability/entitlements/quota policies, access grant summaries, trial state, granted entitlements, and applicable quota statuses using snake_case fields matching shared TypeScript.

- [ ] **Step 4: Register the router and exception handlers.** Register the entitlement router in create_app(). Render ENTITLEMENT_REQUIRED and ENTITLEMENT_QUOTA_EXCEEDED centrally so workout, nutrition, and Body Analysis callers share the same contract.

- [ ] **Step 5: Run API and lint checks.**

Run: uv run pytest tests/entitlements/test_api.py -q

Run: uv run ruff check app/entitlements app/main.py

Expected: focused API tests and Ruff pass.

- [ ] **Step 6: Commit and push.**

~~~bash
git add backend/app/entitlements/schemas.py backend/app/entitlements/dependencies.py backend/app/entitlements/router.py backend/app/main.py backend/tests/entitlements/test_api.py
git commit -m "feat(api): expose member entitlements"
git push origin main
~~~

### Task 6: Provision Launch Trial in every new-account path

**Files:**
- Modify: backend/app/auth/service.py
- Create: backend/tests/entitlements/test_launch_trial.py
- Modify: backend/tests/auth/test_register.py, test_google_auth.py, test_apple_auth.py, test_phone_otp.py, test_mobile_auth.py

**Interfaces:**
- Produces one trial for email registration, new Google, new Apple, and new phone-only users.
- Does not create a trial for Google/Apple linking, existing provider login, existing phone login, password login, refresh, or session reissue.

- [ ] **Step 1: Add failing flow-count tests.** Create/count campaign redemption and UserAccessGrant rows by user for all four signup methods, provider-link cases, and repeated login/token issuance.

- [ ] **Step 2: Run the affected auth/trial tests before code changes.**

Run: uv run pytest tests/entitlements/test_launch_trial.py tests/auth/test_register.py tests/auth/test_google_auth.py tests/auth/test_apple_auth.py tests/auth/test_phone_otp.py tests/auth/test_mobile_auth.py -q

Expected: new trial assertions fail while existing auth assertions identify any baseline failures.

- [ ] **Step 3: Add provisioning after each genuinely new User flush.** Call provision_signup_campaigns(db, user.id, now=now) in register_user, the new-user branches of Google and Apple helpers, and the new branch in _verify_phone_otp_user. Keep existing helper return shapes unless a created flag is needed; no frontend/mobile provisioning.

- [ ] **Step 4: Re-run the same auth/trial scope.**

Run: uv run pytest tests/entitlements/test_launch_trial.py tests/auth/test_register.py tests/auth/test_google_auth.py tests/auth/test_apple_auth.py tests/auth/test_phone_otp.py tests/auth/test_mobile_auth.py -q

Expected: all focused trial/auth tests pass with no duplicate grants.

- [ ] **Step 5: Commit and push.**

~~~bash
git add backend/app/auth/service.py backend/tests/entitlements/test_launch_trial.py backend/tests/auth/test_register.py backend/tests/auth/test_google_auth.py backend/tests/auth/test_apple_auth.py backend/tests/auth/test_phone_otp.py backend/tests/auth/test_mobile_auth.py
git commit -m "feat(auth): provision signup access from campaigns"
git push origin main
~~~

### Task 7: Split workout generation into direct-active and coach-review lifecycles

**Files:**
- Modify: backend/app/workouts/router.py
- Modify: backend/app/workouts/service.py
- Modify: backend/app/workouts/repository.py
- Modify: backend/app/workouts/signature.py
- Modify: backend/tests/workouts/test_workout_plan_api.py, test_repository.py, test_service.py
- Modify: backend/tests/workout_reviews/test_api.py, test_service.py

**Interfaces:**
- WorkoutGenerationService.generate(user_id, overrides=None, *, review_required: bool = False) receives the lifecycle decision explicitly.
- WorkoutGenerationService.get_active(user_id, *, review_required: bool = False) uses the same lifecycle policy for stale/reuse signatures.
- activate_plan() never creates a review; persist_pending_review_plan() remains the only generation helper that creates one.

- [ ] **Step 1: Write/update failing workout tests.** Cover Free 403, Training direct ACTIVE with no review, Training Coach pending with one review and an unchanged prior active plan, approval activation, 28-day coach quota/idempotency, and Training-to-Training-Coach incompatible reuse. Update old repository assertions that intentionally encoded activate_plan() creating a review.

- [ ] **Step 2: Run the directly affected tests before implementation.**

Run: uv run pytest tests/workouts/test_workout_plan_api.py tests/workouts/test_repository.py tests/workouts/test_service.py tests/workout_reviews/test_api.py tests/workout_reviews/test_service.py -q

Expected: the new lifecycle assertions fail; record unrelated baseline failures without weakening them.

- [ ] **Step 3: Add route authorization and explicit policy propagation.** Require training.plan.generate before generation, resolve review_required = has_entitlement(training.coach_review), pass it for every deterministic, AI, bodyweight, and fallback path, and pass it to active-plan signature checks without changing read authorization.

- [ ] **Step 4: Add lifecycle-aware signatures and repository split.** Include the boolean lifecycle policy in deterministic/bodyweight/AI signatures. Route direct generation to activate_plan() and coach generation to persist_pending_review_plan(). Remove the unconditional ensure_pending_review() call from activate_plan().

- [ ] **Step 5: Add coach quota transaction handling.** Before a new coach-required generation, require the capability and check quota. For a newly persisted pending plan, consume training.coach_review with workout-plan:<plan_id> before commit. Keep the generation/plan/event transaction rollback-safe when the concurrent quota winner exhausts the quota; exact reuse returns without another event.

- [ ] **Step 6: Re-run focused workout/review tests and checks.**

Run: uv run pytest tests/workouts/test_workout_plan_api.py tests/workouts/test_repository.py tests/workouts/test_service.py tests/workout_reviews/test_api.py tests/workout_reviews/test_service.py -q

Run: uv run ruff check app/workouts app/workout_reviews

Expected: direct and review lifecycle tests pass; existing approval/editing behavior remains green.

- [ ] **Step 7: Commit and push.**

~~~bash
git add backend/app/workouts/router.py backend/app/workouts/service.py backend/app/workouts/repository.py backend/app/workouts/signature.py backend/tests/workouts/test_workout_plan_api.py backend/tests/workouts/test_repository.py backend/tests/workouts/test_service.py backend/tests/workout_reviews/test_api.py backend/tests/workout_reviews/test_service.py
git commit -m "feat(workouts): apply entitlement-aware review lifecycle"
git push origin main
~~~

### Task 8: Refactor nutrition bundle selection and response state

**Files:**
- Modify: backend/app/nutrition/plan_service.py
- Modify: backend/app/nutrition/router.py
- Modify: backend/app/nutrition/schemas.py
- Modify: backend/tests/nutrition/test_nutrition_api.py, test_bundle_selection.py, test_phase4_dual_optimization.py, test_clinical_review_api.py

**Interfaces:**
- generate_weekly_plan(db, user_id, *, physician_review_entitled: bool = False) generates candidates without attaching a physician review.
- select_bundle_plan(..., physician_review_entitled: bool = False) makes the selected candidate active directly or enters exactly one physician review.
- WeeklyPlanResponse adds physician_review_required: bool and physician_review_status: str | None, while retaining physician_approved and review_status.

- [ ] **Step 1: Write failing nutrition lifecycle tests.** Assert standard Nutrition generation/selection creates no review and an active usable plan, Nutrition Physician generation creates no review before selection, selection attaches review only to the chosen candidate, the other candidate is archived/not queued, and repeated selection does not consume the 28-day quota twice.

- [ ] **Step 2: Run affected nutrition tests before implementation.**

Run: uv run pytest tests/nutrition/test_nutrition_api.py tests/nutrition/test_bundle_selection.py tests/nutrition/test_phase4_dual_optimization.py tests/nutrition/test_clinical_review_api.py -q

Expected: new standard/no-review assertions fail against current eager-review behavior.

- [ ] **Step 3: Make generation persist candidate plans without reviews.** Change successful budget candidate lifecycle to GENERATED, remove eager NutritionPlanPhysicianReview construction/notifications, retain the ideal reference architecture, and leave final selection as the review/activation boundary.

- [ ] **Step 4: Implement selection policy transactionally.** Lock the bundle/target, preserve an existing active plan while a physician review is pending, archive unselected candidates, activate standard selections, or create one review for the selected physician-tier candidate. Require/check/consume nutrition.physician_review with nutrition-plan:<plan_id>:revision:<revision> before commit; roll back on quota failure.

- [ ] **Step 5: Add explicit response state.** Derive physician_review_required from an attached review or persisted safety requirement, return nullable actual review status, and never set physician_approved=True for a plan with no review.

- [ ] **Step 6: Require plan generation entitlement and pass physician capability.** Gate POST /nutrition/plans with nutrition.plan.generate; keep ProductMode checks. Resolve physician capability through EntitlementCode and pass the boolean into generation/selection instead of inspecting package names.

- [ ] **Step 7: Run affected tests and type/lint checks.**

Run: uv run pytest tests/nutrition/test_nutrition_api.py tests/nutrition/test_bundle_selection.py tests/nutrition/test_phase4_dual_optimization.py tests/nutrition/test_clinical_review_api.py -q

Run: uv run ruff check app/nutrition/plan_service.py app/nutrition/router.py app/nutrition/schemas.py

Expected: focused nutrition lifecycle tests pass.

- [ ] **Step 8: Commit and push.**

~~~bash
git add backend/app/nutrition/plan_service.py backend/app/nutrition/router.py backend/app/nutrition/schemas.py backend/tests/nutrition/test_nutrition_api.py backend/tests/nutrition/test_bundle_selection.py backend/tests/nutrition/test_phase4_dual_optimization.py backend/tests/nutrition/test_clinical_review_api.py
git commit -m "feat(nutrition): defer physician review until plan selection"
git push origin main
~~~

### Task 9: Enforce nutrition safety, plan management, food-photo, and clinical capabilities

**Files:**
- Modify: backend/app/nutrition/router.py
- Modify: backend/app/nutrition/plan_editing.py
- Modify: backend/app/nutrition/service.py only where response/policy plumbing requires it
- Modify: backend/tests/nutrition/test_food_photo_estimation.py, test_food_photo_queue.py, test_clinical_review_api.py, test_nutrition_api.py

**Interfaces:**
- Standard safety remains automatic for base Nutrition.
- Automatic-draft safety without physician capability raises structured ENTITLEMENT_REQUIRED; manual/hard-block outcomes remain unchanged.
- Member lab upload requires nutrition.labs.manage; member supplement acknowledgement requires nutrition.supplements.manage; physician specialist routes still use require_physician.

- [ ] **Step 1: Write failing tests for entitlement boundaries.** Cover Free generation/photo-AI denial, Nutrition generation/photo-AI success, plan-management denial, standard no-review response, safety-required physician denial/success, unchanged hard/manual outcomes, existing photo estimate read/edit/confirm/delete, lab upload denial/read/delete, and supplement acknowledgement denial/read.

- [ ] **Step 2: Run the directly affected tests.**

Run: uv run pytest tests/nutrition/test_nutrition_api.py tests/nutrition/test_food_photo_estimation.py tests/nutrition/test_food_photo_queue.py tests/nutrition/test_clinical_review_api.py -q

Expected: new entitlement assertions fail while existing safety/queue tests provide the regression baseline.

- [ ] **Step 3: Add plan-edit capability checks.** Gate confirm/remove/replacement/partial-regeneration writes that create or mutate plan content with nutrition.plan.manage; leave reads, manual tracking, existing estimate operations, and deletion available.

- [ ] **Step 4: Add safety-aware physician entitlement behavior.** Before automatic safety-required activation, require nutrition.physician_review; return the standardized 403 with nutrition_physician and complete_care eligible packages when absent. Do not convert manual or hard-blocked outcomes into automatic plans.

- [ ] **Step 5: Gate only new clinical member writes and food-photo AI creation.** Check nutrition.food_photo.analyze after idempotent replay lookup and before new queue/rate-limit work. Check nutrition.labs.manage before new upload and nutrition.supplements.manage before member acknowledgement. Preserve operational rate limits, consent, queue, storage, specialist, and ownership behavior.

- [ ] **Step 6: Run nutrition regression and checks.**

Run: uv run pytest tests/nutrition/test_nutrition_api.py tests/nutrition/test_food_photo_estimation.py tests/nutrition/test_food_photo_queue.py tests/nutrition/test_clinical_review_api.py -q

Run: uv run ruff check app/nutrition

Expected: all focused nutrition safety/clinical/photo tests pass.

- [ ] **Step 7: Commit and push.**

~~~bash
git add backend/app/nutrition/router.py backend/app/nutrition/plan_editing.py backend/app/nutrition/service.py backend/tests/nutrition/test_nutrition_api.py backend/tests/nutrition/test_food_photo_estimation.py backend/tests/nutrition/test_food_photo_queue.py backend/tests/nutrition/test_clinical_review_api.py
git commit -m "feat(nutrition): enforce capability and safety boundaries"
git push origin main
~~~

### Task 10: Add Body Analysis entitlement and weekly quota

**Files:**
- Modify: backend/app/body_photos/router.py
- Modify: backend/app/body_analysis/router.py
- Modify: backend/app/body_analysis/service.py
- Modify: backend/tests/body_photos/test_session_api.py, backend/tests/body_analysis/test_analysis_api.py, backend/tests/body_analysis/test_history.py

**Interfaces:**
- New session creation performs body_analysis.run capability/quota preflight.
- Member queue/retry consumes body_analysis.run with body-analysis-session:<session_id> only for a new analysis resource.
- Existing history/result/comparison/photo/delete paths remain readable/available; admin retry remains specialist/admin-authorized and does not consume member quota.

- [ ] **Step 1: Write failing Body Analysis tests.** Cover Free denial, paid success, first consumption, same-session retry idempotency, different-session 429 with correct reset, and readable history/result after grant expiry.

- [ ] **Step 2: Run the focused Body Analysis scope.**

Run: uv run pytest tests/body_photos/test_session_api.py tests/body_analysis/test_analysis_api.py tests/body_analysis/test_history.py -q

Expected: new entitlement/quota assertions fail against current unrestricted queue behavior.

- [ ] **Step 3: Add session preflight.** In the member create-session route, call require_entitlement and require_quota_available before the user uploads photos; keep cycle ownership and session validation intact.

- [ ] **Step 4: Add atomic queue consumption.** After _snapshot_for_creation() succeeds and before _create_analysis() commits a new analysis, call consume_quota() when member enforcement is enabled. Return existing non-failed analysis without a second event; pass enforcement off for admin retry.

- [ ] **Step 5: Run focused tests and checks.**

Run: uv run pytest tests/body_photos/test_session_api.py tests/body_analysis/test_analysis_api.py tests/body_analysis/test_history.py -q

Run: uv run ruff check app/body_photos/router.py app/body_analysis/router.py app/body_analysis/service.py

Expected: Body Analysis quota and read-access tests pass.

- [ ] **Step 6: Commit and push.**

~~~bash
git add backend/app/body_photos/router.py backend/app/body_analysis/router.py backend/app/body_analysis/service.py backend/tests/body_photos/test_session_api.py backend/tests/body_analysis/test_analysis_api.py backend/tests/body_analysis/test_history.py
git commit -m "feat(body-analysis): enforce access and weekly quota"
git push origin main
~~~

### Task 11: Add shared TypeScript contracts and package labels

**Files:**
- Create: packages/fitician-core/src/entitlements.ts
- Create: packages/fitician-core/src/entitlements.contract.test.ts
- Modify: packages/fitician-core/src/index.ts
- Modify: packages/fitician-core/package.json
- Modify: packages/fitician-core/src/i18n/fa.ts, en.ts
- Modify: packages/fitician-core/src/nutrition.ts

**Interfaces:**
- Produces readonly accessPackageCodes, entitlementCodes, AccessPackageCode, EntitlementCode, ProductCatalogItem, QuotaStatus, EntitlementState, AccessGrantSummary, and EntitlementSnapshot.
- EntitlementState is the gate state union "granted" | "missing" | "quota_exhausted".
- EntitlementSnapshot uses backend snake_case fields and contains primary/active packages, trial, granted entitlements, and quota statuses.
- Adds physician_review_required and nullable physician_review_status to the shared nutrition plan type.

- [ ] **Step 1: Write failing contract tests.** Assert the exact code unions/arrays, snapshot parsing shape, quota fields, no package-string duplication requirement, and the additive nutrition fields.

- [ ] **Step 2: Run the package test before implementation.**

Run: npm test -- --run src/entitlements.contract.test.ts

Expected: missing-module/type failures.

- [ ] **Step 3: Implement contracts and exports.** Follow existing as const package style, export from root and ./entitlements, and add centralized Persian/English package labels using the exact requested labels.

- [ ] **Step 4: Build and test the core package.**

Run: npm test

Run: npm run build

Expected: all core tests and declaration build pass.

- [ ] **Step 5: Commit and push.**

~~~bash
git add packages/fitician-core/src/entitlements.ts packages/fitician-core/src/entitlements.contract.test.ts packages/fitician-core/src/index.ts packages/fitician-core/package.json packages/fitician-core/src/i18n/fa.ts packages/fitician-core/src/i18n/en.ts packages/fitician-core/src/nutrition.ts
git commit -m "feat(core): add shared entitlement contracts"
git push origin main
~~~

### Task 12: Add the Web entitlement provider and gate

**Files:**
- Create: frontend/src/features/entitlements/api.ts
- Create: frontend/src/features/entitlements/EntitlementContext.tsx
- Create: frontend/src/features/entitlements/EntitlementGate.tsx
- Create: focused Web entitlement tests
- Modify: frontend/src/App.tsx

**Interfaces:**
- getProducts() calls /api/v1/products; getEntitlementSnapshot() calls /api/v1/entitlements/me.
- useEntitlements() exposes snapshot, loading, error, retry, hasEntitlement(), and quotaFor().
- Provider fetches once per authenticated user identity, clears on logout, and does not require a completed profile.

- [ ] **Step 1: Write failing provider/API/gate tests.** Cover request paths, login fetch, logout clear, retry, duplicate-request avoidance, granted/missing gate behavior, and quota lookup.

- [ ] **Step 2: Run focused Web entitlement tests.**

Run: npm test -- src/features/entitlements

Expected: missing-module/context failures.

- [ ] **Step 3: Implement API and provider.** Use the existing request<T> transport and useAuth(), guard asynchronous responses with a generation/ref, retain errors for retry, and return a safe missing state while unauthenticated/loading.

- [ ] **Step 4: Implement EntitlementGate.** Render children only for a granted capability and render an explicit caller fallback for missing or quota-exhausted state; do not hide existing data by default.

- [ ] **Step 5: Insert provider once in App.tsx.** Place it under AuthProvider and above Profile/App routes so authenticated member pages share one request.

- [ ] **Step 6: Run focused tests, lint, and build.**

Run: npm test -- src/features/entitlements

Run: npm run lint

Run: npm run build

Expected: provider/gate tests, lint, and build pass.

- [ ] **Step 7: Commit and push.**

~~~bash
git add frontend/src/features/entitlements frontend/src/App.tsx
git commit -m "feat(web): add entitlement provider and gate"
git push origin main
~~~

### Task 13: Integrate Web navigation and member actions

**Files:**
- Modify: frontend/src/shared/AppShell.tsx
- Modify: frontend/src/pages/DashboardPage.tsx
- Modify: frontend/src/features/workouts/WorkoutPlanPage.tsx
- Modify: frontend/src/features/nutrition/NutritionEstimatePage.tsx, WeeklyNutritionPlan.tsx, NutritionTrackingPage.tsx, NutritionLabsPage.tsx, NutritionSupplementsPage.tsx
- Modify: frontend/src/features/bodyPhotos/BodyProgressPage.tsx, BodyPhotoWizard.tsx
- Modify: frontend/src/pages/MorePage.tsx
- Modify: affected Web tests

**Interfaces:**
- ProductMode controls domain/onboarding visibility only.
- Existing content remains rendered after entitlement expiry; only new paid actions become locked.
- Body Analysis history navigation is no longer training-only; fresh analysis uses body_analysis.run and quota status.

- [ ] **Step 1: Write/update failing Web integration tests.** Assert locked generation buttons, visible old plans/history/PDF links, base Nutrition no physician-pending copy, manual tracking with photo-AI lock only, Body Analysis navigation in Nutrition mode, quota reset messaging, and More trial/package summary.

- [ ] **Step 2: Run affected Web tests before implementation.**

Run: npm test -- src/shared/AppShell.test.tsx src/pages/DashboardPage.test.tsx src/features/workouts/WorkoutPlanPage.test.tsx src/features/nutrition/NutritionEstimatePage.test.tsx src/features/nutrition/NutritionTrackingPage.test.tsx src/features/bodyPhotos

Expected: new entitlement assertions fail against current ProductMode-only actions and physician-pending interpretation.

- [ ] **Step 3: Correct AppShell and dashboard behavior.** Keep Training/Nutrition ProductMode navigation, make Body Analysis history discoverable for either domain, and replace generation calls with entitlement-aware locked actions while preserving existing content cards.

- [ ] **Step 4: Correct workout/nutrition presentation.** Use actual workout review state for coach status, use new nutrition review fields for no review required/waiting/approved, gate new plan/edit/photo/lab/supplement actions, and leave reads/history/PDF/manual tracking available.

- [ ] **Step 5: Correct Body Analysis and More surfaces.** Show quota remaining/reset before fresh capture, keep history/results visible, and add compact current package/trial expiration without prices or purchase UI.

- [ ] **Step 6: Run affected tests, lint, and build.**

Run: npm test -- src/shared/AppShell.test.tsx src/pages/DashboardPage.test.tsx src/features/workouts/WorkoutPlanPage.test.tsx src/features/nutrition/NutritionEstimatePage.test.tsx src/features/nutrition/NutritionTrackingPage.test.tsx src/features/bodyPhotos src/pages/MorePage.test.tsx

Run: npm run lint

Run: npm run build

Expected: affected Web behavior and build checks pass.

- [ ] **Step 7: Commit and push.**

~~~bash
git add frontend/src/shared/AppShell.tsx frontend/src/pages/DashboardPage.tsx frontend/src/features/workouts/WorkoutPlanPage.tsx frontend/src/features/nutrition/NutritionEstimatePage.tsx frontend/src/features/nutrition/WeeklyNutritionPlan.tsx frontend/src/features/nutrition/NutritionTrackingPage.tsx frontend/src/features/nutrition/NutritionLabsPage.tsx frontend/src/features/nutrition/NutritionSupplementsPage.tsx frontend/src/features/bodyPhotos/BodyProgressPage.tsx frontend/src/features/bodyPhotos/BodyPhotoWizard.tsx frontend/src/pages/MorePage.tsx frontend/src/**/*.test.tsx
git commit -m "feat(web): gate paid actions without hiding member data"
git push origin main
~~~

### Task 14: Add the Mobile entitlement provider and gate

**Files:**
- Create: mobile/entitlements/entitlementApi.ts
- Create: mobile/entitlements/EntitlementProvider.tsx
- Create: mobile/entitlements/EntitlementGate.tsx
- Create: focused Mobile entitlement tests
- Modify: mobile/app/_layout.tsx

**Interfaces:**
- Mobile uses @fitician/core/entitlements types and never defines package strings locally.
- useMobileEntitlements() exposes snapshot, loading/error, refresh/retry, hasEntitlement(), and quotaFor().
- Provider is nested inside MobileAuthProvider, clears on sign-out, and remains independent of route ProductMode and specialist state.

- [ ] **Step 1: Write failing Mobile provider/gate tests.** Cover authenticated load, sign-out clear, retry/refresh, shared code usage, and gate states.

- [ ] **Step 2: Run focused Mobile entitlement tests.**

Run: npm test -- entitlements

Expected: missing-module/provider failures.

- [ ] **Step 3: Implement the provider and API.** Use auth.request, fetch only when status === "signed_in" and a user exists, guard stale responses, and expose shared helpers.

- [ ] **Step 4: Insert the provider in _layout.tsx.** Keep MobileAuthProvider outermost; place EntitlementProvider inside it and above route/query/specialist consumers.

- [ ] **Step 5: Run focused Mobile tests and TypeScript checks.**

Run: npm test -- entitlements

Run: npx tsc --noEmit

Expected: provider/gate tests and TypeScript pass.

- [ ] **Step 6: Commit and push.**

~~~bash
git add mobile/entitlements mobile/app/_layout.tsx
git commit -m "feat(mobile): add entitlement provider and gate"
git push origin main
~~~

### Task 15: Integrate Mobile navigation and member actions

**Files:**
- Modify: mobile/app/(member)/member/(tabs)/_layout.tsx
- Modify: mobile/app/(member)/member/(tabs)/body-analysis.tsx
- Modify: mobile/app/(member)/member/body-analysis-capture.tsx
- Modify: mobile/bodyAnalysis/BodyAnalysisHistoryScreen.tsx, BodyAnalysisEmptyState.tsx, bodyPhotoApi.ts
- Modify: mobile/home/MemberHomeScreen.tsx
- Modify: mobile/workouts/WorkoutPlansScreen.tsx and exact API/model files used by generation
- Modify: mobile/nutrition/NutritionFoundationScreen.tsx, NutritionPlanSection.tsx, NutritionTrackingSection.tsx, NutritionDoctorSupervision.tsx, NutritionClinicalSection.tsx
- Modify: mobile/more/MoreScreen.tsx, MoreScreen.rntl.test.tsx
- Modify: affected Mobile RNTL/navigation tests

**Interfaces:**
- ProductMode route guards stay unchanged for Training/Nutrition onboarding/domain access.
- Body Analysis history/tab access has no Training ProductMode requirement; fresh capture requires body_analysis.run and quota state.
- Existing workout/nutrition/result/history content remains available after grant expiry; generation and clinical/photo-AI actions use shared entitlements.

- [ ] **Step 1: Write/update failing Mobile tests.** Cover Body Analysis tab in Nutrition mode, fresh capture lock/reset state, same-session resume, existing result/history visibility, Home workout/nutrition locks, manual food logging, photo-AI lock, base Nutrition no doctor-pending copy, physician review status, trial summary, and shared code usage.

- [ ] **Step 2: Run affected Mobile tests before implementation.**

Run: npm test -- mobile/home/MemberHomeScreen.rntl.test.tsx mobile/workouts/WorkoutPlansScreen.rntl.test.tsx mobile/nutrition/NutritionFoundationScreen.rntl.test.tsx mobile/nutrition/NutritionDoctorSupervision.rntl.test.tsx mobile/bodyAnalysis/BodyAnalysisHistoryScreen.rntl.test.tsx mobile/ui/navigation.test.ts mobile/more/MoreScreen.rntl.test.tsx

Expected: new entitlement assertions fail against current ProductMode-only and physician boolean behavior.

- [ ] **Step 3: Remove the Body Analysis Training route coupling.** Remove requiredCapability="training" from the history tab and make the tab visible for completed member routes independent of ProductMode; leave other route capabilities intact.

- [ ] **Step 4: Gate Body Analysis capture and Home actions.** Check capability/quota before starting fresh capture, preserve resume/history/result paths, and render useful reset information. Keep manual nutrition tracking usable and lock only paid generation/photo-AI/clinical actions.

- [ ] **Step 5: Correct workout/nutrition review presentation and More summary.** Use actual review fields, distinguish no-review from waiting/approved, gate new generation/mutation actions, and show current package/trial expiration without payment UI.

- [ ] **Step 6: Run affected RNTL/navigation tests and TypeScript.**

Run: npm test -- mobile/home/MemberHomeScreen.rntl.test.tsx mobile/workouts/WorkoutPlansScreen.rntl.test.tsx mobile/nutrition/NutritionFoundationScreen.rntl.test.tsx mobile/nutrition/NutritionDoctorSupervision.rntl.test.tsx mobile/bodyAnalysis/BodyAnalysisHistoryScreen.rntl.test.tsx mobile/ui/navigation.test.ts mobile/more/MoreScreen.rntl.test.tsx

Run: npx tsc --noEmit

Run: npm run validate:device-matrix

Expected: affected native-contract/RNTL/navigation/type checks pass; device-matrix results are reported separately from handset evidence.

- [ ] **Step 7: Commit and push.**

~~~bash
git add mobile/app/(member)/member/(tabs)/_layout.tsx mobile/app/(member)/member/(tabs)/body-analysis.tsx mobile/app/(member)/member/body-analysis-capture.tsx mobile/bodyAnalysis mobile/home/MemberHomeScreen.tsx mobile/workouts mobile/nutrition mobile/more/MoreScreen.tsx mobile/more/MoreScreen.rntl.test.tsx mobile/ui/navigation.test.ts
git commit -m "feat(mobile): gate paid actions and preserve member data"
git push origin main
~~~

### Task 16: Complete targeted verification and broad regression review

**Files:**
- Modify only tests or source files identified by failing targeted checks.
- Do not stage unrelated dirty WIP.

**Interfaces:**
- Produces verified backend, shared-core, Web, and Mobile behavior with an explicit failure inventory.

- [ ] **Step 1: Run the complete targeted backend sequence.**

~~~bash
cd backend
uv run pytest tests/entitlements tests/database/test_entitlement_models.py -q
uv run pytest tests/auth tests/entitlements/test_launch_trial.py -q
uv run pytest tests/workouts tests/workout_reviews -q
uv run pytest tests/nutrition/test_nutrition_api.py tests/nutrition/test_bundle_selection.py tests/nutrition/test_food_photo_estimation.py tests/nutrition/test_food_photo_queue.py tests/nutrition/test_clinical_review_api.py tests/nutrition/test_phase4_dual_optimization.py -q
uv run pytest tests/body_photos/test_session_api.py tests/body_analysis/test_analysis_api.py tests/body_analysis/test_history.py -q
uv run ruff check
uv run mypy
~~~

- [ ] **Step 2: Run shared core, Web, and Mobile checks.**

~~~bash
cd packages/fitician-core
npm test
npm run build
cd ../../frontend
npm test
npm run lint
npm run build
cd ../mobile
npm test
npx tsc --noEmit
npm run validate:device-matrix
~~~

- [ ] **Step 3: Run broad regression suites once.** Run the repository-supported full backend/frontend/mobile suites only after targeted suites are clean. Record pre-existing unrelated failures with exact command output; do not weaken assertions or claim handset/native signing evidence from Linux checks.

- [ ] **Step 4: Verify runtime/API/migration evidence.** Inspect alembic current/heads, OpenAPI routes/schemas, authenticated cookie and bearer calls for products/entitlements, grant expiry, structured 403/429 responses, read access after expiry, and deletion cascade. Do not claim provider/image/payment functionality.

- [ ] **Step 5: Inspect final diff and status.** Confirm no prices/payment code/secrets, no ProductMode replacement, no generated-tree edits, and only intended files in each entitlement commit. Use git diff --check, git status --short, and git log.

- [ ] **Step 6: Report final results.** Include created/modified files, actual migration revision/down revision, exact matrix, quotas, Launch Trial behavior, workout/nutrition/Body Analysis lifecycle changes, Web/Mobile changes, exact commands and pass/fail counts, and remaining unrelated failures.
