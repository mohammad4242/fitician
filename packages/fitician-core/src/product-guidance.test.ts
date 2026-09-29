import { expect, it } from "vitest";
import { workoutGuidance, cardioGuidance, weightTrendPoints } from "./product-guidance";
it("explains prescribed warmup, reserve reps and progression", () => {
  const lines = workoutGuidance({ warmup_sets: 2, rir: 3, load_guidance: "Select a load that preserves the target RIR.", progression_rule: "double_progression_v1" }, "fa");
  expect(lines.join(" ")).toContain("۲");
  expect(lines.join(" ")).toContain("۳ تکرار");
  expect(lines.join(" ")).toContain("دو جلسه");
});
it("does not invent legacy guidance", () => {
  expect(workoutGuidance({ rir: null, warmup_sets: 0, load_guidance: "", progression_rule: "legacy" }, "en")).toEqual([]);
});
it("preserves custom instructions", () => {
  expect(workoutGuidance({ load_guidance: "Use the coach's specified load" }, "en")).toContain("Use the coach's specified load");
});
it("renders actual cardio", () => {
  expect(cardioGuidance({ modality_name: "Stationary Bike", duration_minutes: 10, intensity: "moderate" }, "en")).toContain("10");
  expect(cardioGuidance(null, "fa")).toBeNull();
});
it("positions sorted measurements by elapsed time", () => {
  const points = weightTrendPoints([{ measured_at: "2026-09-10T00:00:00Z", weight_kg: 78 }, { measured_at: "2026-09-01T00:00:00Z", weight_kg: 80 }, { measured_at: "2026-09-02T00:00:00Z", weight_kg: 79 }]);
  expect(points.map(p => p.weight_kg)).toEqual([80, 79, 78]);
  expect(points[1]!.x).toBeCloseTo(100 / 9);
  expect(points[2]!.x).toBe(100);
});
it("handles empty, invalid and single measurements", () => {
  expect(weightTrendPoints([])).toEqual([]);
  expect(weightTrendPoints([{ measured_at: "invalid", weight_kg: 70 }])).toEqual([]);
  expect(weightTrendPoints([{ measured_at: "2026-09-01T00:00:00Z", weight_kg: 70 }])[0]!.y).toBe(50);
});
