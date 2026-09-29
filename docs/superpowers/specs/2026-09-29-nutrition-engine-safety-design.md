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

## Admission policy details

- Weekly calorie tolerance is 5% of the target, further bounded to 25% of the
  intended deficit/surplus when maintenance energy is available. Daily tolerance
  is 10%. These are engine acceptance tolerances, not clinical recommendations.
- Protein and fat minimums are checked for every day and for the weekly average.
  Existing target-generation rules and applicable upper limits remain authoritative.
- A known micronutrient intake below 75% of its reference target, with at least
  80% composition coverage, blocks automatic admission for specialist review.
  This is a conservative escalation rule, not a deficiency diagnosis or an EAR.
  Sodium AI is not treated as a minimum required intake.
- Free Meal energy/macros are explicit planning allowances. Planned day totals
  include them once; food composition and actual-intake entries stay empty until
  the member records intake. Core comparisons with an allowance have medium confidence.
- A coherent extreme weight trend is retained. Loss above 1% of body weight per
  week, or gain above 1% (0.5% for muscle gain), triggers review before any automatic
  target adjustment. These are review triggers, not diagnoses.
- Unresolved allergen groups or insufficient verified allergy-safe catalogue
  coverage stop generation. Historical allergen metadata is not guessed or bulk
  backfilled. Historical quantity basis remains explicitly unknown.
- Equivalent replacements preserve energy, nutritional role, and portion bounds.
  Rounding cannot push a valid fractional boundary outside its allowed range.
- Both budget and ideal fallback selection compare admitted alternatives.

Scientific interpretation references:
[National Academies, Dietary Reference Intakes: Applications in Dietary Assessment](https://www.ncbi.nlm.nih.gov/books/NBK222891/)
and [NIH calcium fact sheet](https://ods.od.nih.gov/factsheets/Calcium-HealthProfessional/).
Reference intakes guide review of usual intake; they do not diagnose deficiency
from a generated meal plan alone.
