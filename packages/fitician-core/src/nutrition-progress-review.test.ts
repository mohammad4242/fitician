import { expect, it } from "vitest";
import { createNutritionProgressApi } from "./nutrition-progress-review";
import type { NutritionProgressReview } from "./nutrition-progress-review";
import type { TransportRequest } from "./transport";
it("confirms only the displayed proposal and carries its plan and fingerprint", async () => {
  const calls: TransportRequest[] = [];
  const api = createNutritionProgressApi(async <T>(input: TransportRequest) => { calls.push(input); return { estimate_id: "estimate", targets_updated: true } as T; });
  const proposal = { can_confirm: true, plan_id: "plan", signature: "a".repeat(64) } as NutritionProgressReview;
  await api.confirm(proposal);
  expect(calls[0]?.body).toEqual({ expected_plan_id: "plan", signature: proposal.signature, confirmed: true });
  expect(calls[0]?.path).toBe("/api/v1/nutrition/progress-review/confirm");
});
it("cannot submit a review without a server proposal", async () => {
  const api = createNutritionProgressApi(async <T>() => ({} as T));
  await expect(api.confirm({ can_confirm: false } as NutritionProgressReview)).rejects.toThrow(/proposal/i);
});

it("rejects an incomplete response before a date or proposal can render", async () => {
  const api = createNutritionProgressApi(async <T>() => ({ status: "continue", reason_codes: [] } as T));
  await expect(api.review()).rejects.toThrow(/Invalid progress/);
});
