import { expect, it } from "vitest";
import { workoutExecutionGuidance, cardioGuidance, weightTrendPoints } from "./product-guidance";

it("merges general guidance once for the entire program in both languages", () => {
  const item = { exercise: { name_fa: "اسکوات", name_en: "Squat" }, warmup_sets: 2, rir: 3, load_guidance: "Select a load that preserves the target RIR.", progression_rule: "double_progression_v1" };
  for (const locale of ["fa", "en"] as const) {
    const lines = workoutExecutionGuidance([item, item], locale);
    expect(lines).toEqual(workoutExecutionGuidance([item], locale));
    expect(lines.filter(line => line.includes("RIR 1"))).toHaveLength(1);
    expect(lines.join(" ")).toContain(locale === "fa" ? "دو جلسه" : "two sessions");
    expect(lines.join(" ")).toContain(locale === "fa" ? "اسکوات: ۲" : "Squat: 2");
  }
});
it("keeps legacy guidance general and preserves distinct custom instructions with their exercise", () => {
  const items = [
    { exercise: { name_fa: "اسکوات", name_en: "Squat" }, progression_rule: "legacy", load_guidance: "  Coach load  " },
    { exercise: { name_fa: "پرس", name_en: "Press" }, progression_rule: "Pause progression", load_guidance: "Coach load" },
  ];
  const lines = workoutExecutionGuidance(items, "en");
  expect(lines.join(" ")).not.toContain("legacy");
  expect(lines.filter(line => line.includes("Coach load"))).toEqual(["Squat, Press: Coach load"]);
  expect(lines).toContain("Press: Pause progression");
});
it("localizes bodyweight rules once without exposing internal identifiers", () => {
  const item = { progression_rule: "bodyweight_double_progression_v1", load_guidance: "Use a bodyweight variation that preserves the target RIR." };
  const lines = workoutExecutionGuidance([item, item], "fa");
  expect(lines.join(" ")).toContain("وزن بدن");
  expect(lines.join(" ")).not.toContain("bodyweight_double_progression_v1");
  expect(lines).toEqual(workoutExecutionGuidance([item], "fa"));
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
