import { expect, it } from "vitest";

import type { TimelineNutrition, TimelineWorkout } from "@fitician/core/program-timeline";

import { homeWorkoutSummary, nutritionSummary } from "./homeModel";

it("uses the exact timeline session instead of the first workout day", () => {
  const summary = homeWorkoutSummary({
    completed_sessions: 1,
    current_week: 1,
    cycle_id: "cycle-1",
    duration_weeks: 8,
    next_session: {
      day_number: 3,
      estimated_duration_minutes: 45,
      id: "session-2",
      scheduled_date: "2026-09-14",
      session_number: 2,
      status: "scheduled",
      title_en: "Lower body",
      title_fa: "پایین‌تنه",
      week_number: 1,
      workout_day_id: "day-2",
    },
    state: "rest_day",
    total_sessions: 16,
  } satisfies TimelineWorkout);

  expect(summary.state).toBe("rest");
  expect(summary.focusedSession).toBeNull();
  expect(summary.nextSession?.workout_day_id).toBe("day-2");
});

it("prefers daily plan totals and calculates progress from logged intake versus daily target", () => {
  const summary = nutritionSummary(
    {
      days: [{
        day_index: 0,
        meals: [],
        nutrient_totals: {
          energy_kcal: 2200,
          protein_g: 150,
          carbohydrate_g: 240,
          total_fat_g: 70,
        },
        plan_date: "2026-09-09",
      }],
      physician_approved: true,
    } as never,
    {
      targets: {
        goal_calories: { preferred: 2300, minimum: 2000 },
        tdee: { preferred: 2557, minimum: 2400 },
        protein: { preferred: 145, minimum: 120 },
        carbohydrate: { preferred: 240, minimum: 200 },
        total_fat: { preferred: 70, minimum: 50 },
      },
    } as never,
    {
      actual_totals: { energy_kcal: 880, protein_g: 64, carbohydrate_g: 90, total_fat_g: 22 },
      check_in_status: "on_plan",
      data_status: "sufficient",
      entries: [{ id: "entry-1" }],
    } as never,
    "2026-09-09",
  );

  expect(summary.targetCalories).toBe(2200);
  expect(summary.estimatedDailyExpenditureCalories).toBe(2557);
  expect(summary.consumedCalories).toBe(880);
  expect(summary.progress).toBeCloseTo(880 / 2200);
  expect(summary.protein).toBe(64);
  expect(summary.carbohydrate).toBe(90);
  expect(summary.fat).toBe(22);
  expect(summary.status).toBe("on_plan");
});

it("uses estimate metric names when the daily plan has no nutrient totals", () => {
  const summary = nutritionSummary(
    { days: [], physician_approved: true } as never,
    {
      targets: {
        goal_calories: { preferred: 2778, minimum: 2500 },
        tdee: { preferred: 2557, minimum: 2400 },
        protein: { preferred: 145, minimum: 120 },
        carbohydrate: { preferred: 240, minimum: 200 },
        total_fat: { preferred: 70, minimum: 50 },
      },
    } as never,
    null,
    "2026-09-09",
  );

  expect(summary.targetCalories).toBe(2778);
  expect(summary.estimatedDailyExpenditureCalories).toBe(2557);
  expect(summary.protein).toBeNull();
  expect(summary.carbohydrate).toBeNull();
  expect(summary.fat).toBeNull();
});

it("uses the recurring timeline target on nutrition day eight", () => {
  const summary = nutritionSummary(
    {
      days: [{ nutrient_totals: { energy_kcal: 999 }, plan_date: "2026-01-01" }],
      physician_approved: true,
    } as never,
    {
      targets: {
        goal_calories: { preferred: 2778, minimum: 2500 },
        tdee: { preferred: 2557, minimum: 2400 },
        protein: { preferred: 145, minimum: 120 },
        carbohydrate: { preferred: 240, minimum: 200 },
        total_fat: { preferred: 70, minimum: 50 },
      },
    } as never,
    null,
    "2026-09-13",
    {
      absolute_day_number: 8,
      nutrient_totals: { energy_kcal: 2_100, protein_g: 140 },
      pattern_day_index: 0,
      plan_id: "plan-1",
      start_date: "2026-09-06",
      state: "active",
    } satisfies TimelineNutrition,
  );

  expect(summary.targetCalories).toBe(2_100);
  expect(summary.protein).toBeNull();
});

it("uses effective today totals instead of the selected future plan during a handoff", () => {
  const summary = nutritionSummary(
    {
      days: [{ nutrient_totals: { energy_kcal: 3_000 }, plan_date: "2026-09-17" }],
      physician_approved: true,
    } as never,
    null,
    null,
    "2026-09-14",
    {
      state: "scheduled_start",
      plan_id: "future-plan",
      start_date: "2026-09-17",
      nutrient_totals: { energy_kcal: 3_000 },
      effective_today: {
        plan_id: "old-plan",
        start_date: "2026-09-01",
        absolute_day_number: 14,
        pattern_day_index: 6,
        day_id: "old-day",
        nutrient_totals: { energy_kcal: 2_200, protein_g: 150 },
      },
    } satisfies TimelineNutrition,
  );

  expect(summary.targetCalories).toBe(2_200);
  expect(summary.protein).toBeNull();
});

it("returns an empty nutrition state when neither plan nor estimate exists", () => {
  expect(nutritionSummary(null, null, null, "2026-09-09")).toMatchObject({
    status: "empty",
    estimatedDailyExpenditureCalories: null,
    targetCalories: null,
    progress: 0,
  });
});

it("uses actual intake for both gain and loss nutrition targets", () => {
  const estimate = {
    targets: {
      tdee: { preferred: 2400 },
      protein: { preferred: 145 },
      carbohydrate: { preferred: 240 },
      total_fat: { preferred: 70 },
    },
  } as never;
  const gainSummary = nutritionSummary(
    {
      days: [{ nutrient_totals: { energy_kcal: 3_000 }, plan_date: "2026-09-09" }],
      physician_approved: true,
    } as never,
    estimate,
    {
      actual_totals: { energy_kcal: 1_800 },
      check_in_status: null,
      data_status: "sufficient",
      entries: [],
    } as never,
    "2026-09-09",
  );
  const lossSummary = nutritionSummary(
    {
      days: [{ nutrient_totals: { energy_kcal: 1_800 }, plan_date: "2026-09-09" }],
      physician_approved: true,
    } as never,
    estimate,
    {
      actual_totals: { energy_kcal: 2_000 },
      check_in_status: null,
      data_status: "sufficient",
      entries: [],
    } as never,
    "2026-09-09",
  );

  expect(gainSummary.progress).toBeCloseTo(1800 / 3000);
  expect(lossSummary.progress).toBeCloseTo(2000 / 1800);
});

it("does not invent consumed calories when intake is unrecorded", () => {
  const summary = nutritionSummary(null, { targets: { goal_calories: { preferred: 2000 } } } as never, null, "2026-09-09");
  expect(summary.consumedCalories).toBeNull();
  expect(summary.progress).toBe(0);
});
it("preserves intake above target instead of hiding excess", () => {
  const summary = nutritionSummary(null, { targets: { goal_calories: { preferred: 2000 } } } as never,
    { actual_totals: { energy_kcal: 2400 }, entries: [{}], check_in_status: null, data_status: "sufficient" } as never, "2026-09-09");
  expect(summary.progress).toBe(1.2);
});
