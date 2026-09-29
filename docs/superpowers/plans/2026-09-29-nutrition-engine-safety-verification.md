# Nutrition engine correction verification

## Scope

The twelve approved nutrition findings are addressed by shared admission rules for
new plans and edited revisions, bounded weight-rate requests, exposure arithmetic,
and consistent quantity/Free Meal presentation. Unrelated workspace changes are
preserved. No production migration or deployment is included.

## Regression coverage

| Finding | Verified behavior / regression |
| --- | --- |
| 1. Allergy leakage | Canonical milk excludes yogurt; missing verified metadata or unresolved allergen groups block admission. `test_engine_safety_regressions`, `test_food_constraints`. |
| 2. Supplement exposure | Stored daily food exposure is counted once alongside active supplements and the applicable limit. `test_supplement_workflow_api`. |
| 3. Unsafe edits | Removal and replacements share admission before quota/persistence; incompatible oil/protein substitution is excluded; immutable history and quota atomicity remain covered. `test_plan_editing_api`. |
| 4. Unsafe requested rate | User requests use the existing goal-specific limits; old estimate cache signatures become stale; Web/Mobile show safety adjustment. `test_weight_rate_policy`, `test_nutrition_estimate_api`, weight-rate card tests. |
| 5. Free Meal excess | Main meals and free snacks reserve the correct energy/macros; planned totals include allowances once, while composition and actual-intake entries remain separate. `test_engine_safety_regressions`, `test_weekly_plan_api`, `test_tracking_api`. |
| 6. Calorie drift | Weekly/daily tolerances and deficit/surplus preservation reject the previously admitted 1248 → 1480 kcal drift. `test_engine_safety_regressions`. |
| 7. Reliable low micronutrients | Portion repair can exchange foods at similar energy; large unresolved reliable gaps require review. Unknown data does not diagnose deficiency. `test_portion_solver`, `test_engine_safety_regressions`. |
| 8. Extreme trends discarded | Sustained −2 kg/week is retained and escalated before automatic adjustment; isolated inconsistent outliers remain rejected. `test_progress_review_policy`, `test_progress_review_api`. |
| 9. Quantity basis lost | Basis is snapshotted and survives catalogue changes; API, Web, Mobile and PDF show it. Historical basis is explicitly unknown. `test_weekly_plan_api`, `test_pdf`, shared quantity/Web tests. |
| 10. Daily macro gaps hidden | Individual days must meet macro floors even if weekly means are adequate. `test_engine_safety_regressions`. |
| 11. Repetition/first-result acceptance | Template caps are hard; exhausted coverage returns an explicit failure; both budget and ideal fallback compare admitted alternatives. `test_candidate_selection`, `test_template_substitution`, `test_budget_optimizer`. |
| 12. Edited fat becomes zero | Fat derives from immutable `total_fat_g` snapshots, including legacy zero aggregate reads. `test_engine_safety_regressions`, `test_weekly_plan_api`. |

Additional regressions cover stale post-repair costs, fractional replacement bounds
including PostgreSQL NUMERIC(20, 8) rounding,
review/quota atomicity, and preserving prepared-recipe metadata across revisions.

## Verification status

- Standard nutrition suite: **577 passed** (excluding the slow profile trace file).
- Historical stress profiles: **19 passed**, with explicit safe/infeasible outcomes.
- Core: **118 passed**; Web nutrition views: **65 passed**; native tests: **20 passed**.
- Backend Ruff checks and strict mypy checks for eight changed engine modules passed.
- Core build, Web production build, mobile typecheck, and OpenAPI contract check passed.
- The final full standard run included the replacement-ratio precision regression
  and corrected composition-equivalent entitlement fixtures.
- These checks ran in the shared workspace; unrelated existing WIP was preserved.
  Logs and profile trace data are retained locally under `.codex-tmp/`.

## Profile traces

All 19 historical stress profiles completed without uncaught engine errors:
9 successful plans, 9 explicit target-infeasible outcomes, and 1 catalogue/template
infeasibility. Successful traces had no allergen, exclusion, or medical-policy
violations. Their daily and weekly energy totals met the new admission limits.
Profiles included female weight loss, male muscle gain, sedentary/high-activity
users, restricted budgets, allergies, and dislikes. Infeasible outcomes are
explicit failures; they are not usable diet prescriptions.

## Deployment requirements and limits

- Migration `20260929_165` adds immutable quantity snapshots and registers the
  shared admission policy. Apply through the normal migration/deployment process.
- Historical portions are not reinterpreted or guessed. Existing plan history is
  preserved; regenerated plans receive the new admission rules and quantity basis.
- Allergen information must be verified in the catalogue. The engine cannot turn
  missing ingredient/allergen information into a safe classification.
- The 75% micronutrient threshold and weight-rate trend thresholds are review
  policies, not diagnoses. The numerical rationale is documented in the design.
- A safe ideal reference plan can be offered when an affordable budget plan is
  unavailable; ideal-plan success does not imply budget feasibility.
