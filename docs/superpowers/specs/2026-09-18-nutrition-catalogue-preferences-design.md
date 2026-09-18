# Catalogue-backed nutrition preferences

## Goal

Replace free-text favourite, disliked, allergy, and intolerance profile values with verified Food Catalogue and Meal Catalogue identities that remain authoritative from onboarding through weekly-plan generation.

## Contract

The shared identity is `NutritionCatalogueTarget`:

```ts
type NutritionCatalogueTargetType = "food" | "meal";

type NutritionCatalogueTarget = {
  target_type: NutritionCatalogueTargetType;
  target_id: string;
  name_fa: string;
  name_en: string;
  category: string | null;
  image_url: string | null;
};
```

Write inputs carry only `target_type`, `target_id`, and optional constraint details. The backend loads names and metadata from verified catalogue rows. Canonical response fields are `favourite_catalogue_items`, `disliked_catalogue_items`, `allergy_catalogue_items`, and `intolerance_catalogue_items`; the existing string fields remain deprecated compatibility projections.

## Persistence

`nutrition_food_items` remains the profile preference snapshot table. It gains nullable `catalogue_meal_id` with a `SET NULL` foreign key. New rows require exactly one of `catalogue_food_id` or `catalogue_meal_id`; historical unresolved rows remain nullable. Partial unique indexes deduplicate canonical food and meal identities independently, allowing equal display names across the two catalogues. An XOR check constraint prevents both identities on one row.

The next migration is based on the current `20260918_158` head and does not delete unresolved historical rows.

## Search

`catalogue_options.py` owns one bounded, deterministic search over verified, non-retired foods and meals. Food names, English names, slugs, and normalized aliases are searched; meals search Persian name, English name, and code. Prefix matches rank before substring matches, ties use stable type/name/id ordering, and the result is cached in the existing nutrition cache with a dedicated namespace. The unauthenticated read endpoint exposes catalogue metadata only so public onboarding can use it.

Catalogue mutations invalidate the search namespace together with the existing food or meal namespaces.

## Validation and errors

Profile writes bulk-load all selected food and meal IDs, reject missing, wrong-type, draft, and retired targets with structured 422 errors, reject duplicate or contradictory selections, and never persist client labels. Legacy string fields are accepted only when exactly one verified catalogue target matches after existing normalization; ambiguous and unmatched values are rejected. Canonical target identity is used for all new storage and planner input.

## Planner semantics

The immutable preference snapshot combines canonical profile selections with existing meal feedback. It contains liked/disliked food and meal IDs, hard-excluded food and meal IDs, feedback exclusions, positive feedback, and adherence. Food constraints carry exact canonical food IDs; meal constraints remain template-level and do not expand to ingredient constraints.

Eligibility excludes hard and disliked foods/meals before ranking, including prepared-recipe ingredients. Favourites boost equivalent food-containing templates and exact favourite meals, while safety, dietary pattern, nutrient feasibility, budget, and repetition remain higher priority. Substitution and budget repair receive the same context and cannot reintroduce avoided targets. A final deterministic plan scan converts any violation into an infeasible result with `PREFERENCE_AVOIDANCE_NO_FEASIBLE_PLAN`.

## Client flow

Web and native clients share the core types and send canonical IDs. The Web and React Native pickers query the same bounded endpoint with debounce, stale-request protection, keyboard/screen-reader or TalkBack support, removable chips, and no free-text commit path. Public drafts persist the canonical objects unchanged through account hydration. Existing profiles hydrate canonical response items directly.

Preference changes do not mutate active plans. The existing generation input snapshot records canonical selections and a deterministic preference signature, allowing the UI to identify that a visible plan predates current preferences and ask the user to regenerate.

## Verification

Backend tests cover search visibility/ranking, canonical validation, persistence, snapshots, exact food constraints, planner eligibility, substitution, budget repair, final defense, and 100-profile regression. Web and native tests cover query behavior, chips, keyboard/sheet interaction, hydration, accessibility, draft persistence, and ID-only payloads. OpenAPI is regenerated from backend schemas, then core, frontend, native typechecks, focused tests, builds, and lint run.
