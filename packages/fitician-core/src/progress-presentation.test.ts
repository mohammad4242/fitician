import { expect, it } from "vitest";
import {
  overviewCards,
  calorieSeries,
  progressTabs,
} from "./progress-presentation.js";
import type { ProgressOverview } from "./progress.js";
const body = {
  unit: "kg",
  points: [],
  start_value: null,
  latest_value: null,
  delta: null,
};
const data = {
  context: {
    training_enabled: false,
    nutrition_enabled: true,
    timezone: "UTC",
    today: "2026-10-02",
  },
  training: null,
  nutrition: {
    logged_days: 1,
    elapsed_days: 2,
    series: [
      { date: "2026-10-01", target_kcal: 2200, actual_kcal: 2140 },
      { date: "2026-10-02", target_kcal: 2000, actual_kcal: null },
    ],
  },
  body_measurements: { weight: body },
  recovery: [],
  body_analysis: {},
} as unknown as ProgressOverview;
it("omits unrelated cards and disables unrelated categories", () => {
  expect(overviewCards(data, "en").map((c) => c.tab)).toEqual([
    "calories",
    "body",
    "analysis",
  ]);
  expect(
    progressTabs(data)
      .filter((t) => !t.disabled)
      .map((t) => t.id),
  ).toEqual(["overview", "calories", "body", "analysis"]);
});
it("preserves historical targets and intake gaps", () => {
  expect(calorieSeries(data.nutrition!)).toEqual([
    [
      { date: "2026-10-01", value: 2200 },
      { date: "2026-10-02", value: 2000 },
    ],
    [
      { date: "2026-10-01", value: 2140 },
      { date: "2026-10-02", value: null },
    ],
  ]);
});
it("never invents a change or sparkline from a single observation", () => {
  const single = {
    ...data,
    body_measurements: {
      ...data.body_measurements,
      weight: {
        ...body,
        points: [{ value: 99.5, recorded_at: "2026-10-01", source: "manual" }],
        latest_value: 99.5,
        start_value: 99.5,
        delta: null,
      },
    },
  } as ProgressOverview;
  const card = overviewCards(single, "en").find((c) => c.tab === "body")!;
  expect(card.value).toBe("99.5 kg");
  expect(card.support).toBe("Current weight");
  expect(card.extra).toContain("One more");
  expect(card.series).toEqual([]);
});
