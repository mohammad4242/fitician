# Nutrition progress review

Approved scope: only item 1 in the latest explanation (item 2 in the second audit).

Add a review panel to nutrition tracking on Web and mobile. Review the last 28 completed local days since the effective active plan started. Show recorded days, reported adherence, calorie logging coverage, and a trend based on multiple distinct weighing days. Missing food or weight data never means zero intake or zero progress.

Use conservative product eligibility rules: at least 14 completed days, 14 checked-in days with calorie entries, high-confidence intake records, and four weighing days spanning at least 14 days. Require measurements in both halves and a recent measurement. These are product eligibility thresholds, not validated clinical diagnostic cutoffs. Decline numeric adjustments for weight series spanning more than 10 percent of median body weight. Compare observed scale-weight direction/rate with the existing engine's applied goal rate; do not claim causal fat or muscle change.

When reported adherence or recorded calorie intake is inconsistent, recommend improving adherence before changing targets. When the trend is aligned, recommend continuing. For a persistent mismatch with sufficient data, preview a small change to the existing requested weekly rate, calculated through the current scientific engine in safe mode. Do not infer TDEE from scale changes or implement a new calorie equation. If existing bounds prevent a meaningful adjustment, refer to specialist review. Recomposition/maintenance and medical/review-dependent plans never receive autonomous calorie adjustment.

Confirm the exact proposal using a server recomputed fingerprint and current active plan ID. Preserve the fitness goal, scientific safety limits, and medical review workflow. Store evidence and consent on the existing target consent record. Confirmation changes targets only, atomically; the active meal plan remains intact. After confirmation provide the existing new-plan flow so its billing, quota, planner, selection and start gates remain authoritative. Retry is idempotent. Do not pretend an updated target already changed meal portions.

Invalidate a proposal when its evidence, plan, safety, profile or goal changes. Allow at most one confirmed review per seven days. A target/active-plan rate mismatch requires a new plan before another numeric adjustment. Never propose a larger calorie deficit for faster-than-target loss, or a larger surplus for faster-than-target gain. Render loading, insufficient-data, errors, retry, continue, adherence guidance, specialist referral, explicit confirmation and saved-target states. Scope asynchronous client updates to the signed-in account.

Test no-data handling, timezone/day boundaries, trend aggregation, confidence and partial records, goal comparison, clinical gates, clamping, confirmation, stale proposals, retries, rollback, API ownership, Web/mobile parity and existing target/plan flows.

Reference: existing `weight_rate_policy.py` documents its engineering rate conversion as an initial control signal, not a real-world prediction. NIDDK's dynamic weight model similarly distinguishes energy-control assumptions from observed outcomes: https://www.niddk.nih.gov/-/media/Files/BWP/Hall_Lancet_Web_Appendix.pdf . No effectiveness guarantee is added.
