# Nutrition engine safety corrections

Approved approach: shared validation for generated plans and edited revisions.

Scope: the twelve nutrition audit findings only. Preserve unrelated work and existing
actual-intake tracking, physician authorization, and supplement locking.

1. Resolve food allergies to allergen groups as well as specific foods. Require
   verified allergen metadata for allergy decisions, including recipe ingredients.
2. Use the stored daily food nutrient average once in supplement exposure checks.
3. Revalidate every edited revision before persistence. Offer compatible, energy
   equivalent replacements with bounded portions; reject invalid edits atomically.
4. Apply existing goal-specific automatic safety limits to user-requested rates.
5. Reserve a free meal's energy allocation without inventing consumed nutrients.
6. Narrow calorie acceptance and preserve the intended deficit or surplus.
7. Repair reliable micronutrient gaps; unresolved gaps require explicit review.
   Missing composition data is uncertainty, not proof of deficiency.
8. Distinguish coherent extreme weight trends from isolated erroneous weighings.
9. Snapshot and display measurement basis in the API, Web, Mobile, and PDF.
10. Validate daily macro floors as well as weekly totals.
11. Enforce repetition limits and evaluate feasible alternatives before accepting.
12. Recalculate edited fat metrics from total_fat_g.

Verification: regression tests for each finding; planner and edit API tests;
cross-platform type checks; reproducible realistic profile traces. No deployment.
