import { expect, it } from "vitest";

import type { components } from "@fitician/core";
import type { TimelineNutrition } from "@fitician/core/program-timeline";

import {
  classifyNutritionGenerationOutcome,
  canEditNutritionPlan,
  formatNutritionPlanMoney,
  getNutritionPlanStatus,
  isNutritionPlanExecutable,
  nutritionTimelinePresentation,
  preparedRecipePresentation,
  selectNutritionPlan,
  nutritionPlanPdfFilename,
} from "./nutritionPlanModel";

type NutritionPlan = components["schemas"]["WeeklyPlanResponse"];

function plan(overrides: Partial<NutritionPlan> = {}): NutritionPlan {
  return {
    budget_status: "within_budget",
    created_at: "2026-09-07T00:00:00Z",
    days: [],
    explanation_codes: [],
    food_data_manifest: {},
    formula_version: "formula-v1",
    id: "plan-1",
    input_snapshot: {},
    is_user_visible: true,
    lifecycle_status: "active",
    nutrients: {},
    physician_approved: true,
    physician_approved_at: "2026-09-07T00:00:00Z",
    physician_review_required: true,
    physician_change_summary: [],
    physician_display_name: null,
    physician_user_visible_notes: null,
    plan_role: "budget",
    planner_policy_version: "planner-policy-v1",
    planner_version: "planner-v1",
    price_snapshot: { references: [{ source: "backend-approved" }] },
    repair_actions: [],
    review_status: "approved",
    revision: 1,
    scientific_policy_version: "science-v1",
    start_date: "2026-09-07",
    supersedes_plan_id: null,
    warning_codes: [],
    weekly_budget_irr: 10_000_000,
    weekly_cost_irr: 9_000_000,
    ...overrides,
  };
}

it("keeps plan lifecycle and physician approval visible", () => {
  expect(getNutritionPlanStatus(plan())).toBe("active");
  expect(getNutritionPlanStatus(plan(), true)).toBe("historical");
  expect(getNutritionPlanStatus(plan({
    lifecycle_status: "pending_physician_review",
    physician_approved: false,
    review_status: "pending",
  }))).toBe("pending_review");
  expect(getNutritionPlanStatus(plan({
    lifecycle_status: "changes_requested",
    physician_approved: false,
    review_status: "changes_requested",
  }))).toBe("changes_requested");
});

it("never marks historical or unapproved plans executable", () => {
  expect(isNutritionPlanExecutable(plan())).toBe(true);
  expect(isNutritionPlanExecutable(plan(), true)).toBe(false);
  expect(isNutritionPlanExecutable(plan({ physician_approved: false }))).toBe(false);
  expect(isNutritionPlanExecutable(plan({ physician_review_required: false, physician_approved: false, review_status: "pending" }))).toBe(true);
  expect(isNutritionPlanExecutable(plan({ is_user_visible: false }))).toBe(false);
  expect(isNutritionPlanExecutable(plan({ lifecycle_status: "pending_physician_review" }))).toBe(false);
  expect(canEditNutritionPlan(plan(), false, false)).toBe(true);
  expect(canEditNutritionPlan(plan(), true, false)).toBe(false);
  expect(canEditNutritionPlan(plan(), false, true)).toBe(false);
});

it("prefers the latest revision while preserving the active plan fallback", () => {
  const active = plan({ id: "active-plan" });
  const latest = plan({
    id: "latest-plan",
    lifecycle_status: "pending_physician_review",
    physician_approved: false,
    review_status: "pending",
  });

  expect(selectNutritionPlan(active, latest)).toEqual({ isLatest: true, plan: latest });
  expect(selectNutritionPlan(active, null)).toEqual({ isLatest: false, plan: active });
  expect(selectNutritionPlan(null, null)).toEqual({ isLatest: false, plan: null });
});

it("classifies backend generation outcomes and keeps money display rounding local", () => {
  expect(classifyNutritionGenerationOutcome("success")).toBe("success");
  expect(classifyNutritionGenerationOutcome("safety_blocked")).toBe("safety_blocked");
  expect(classifyNutritionGenerationOutcome("live_price_unavailable")).toBe("price_unavailable");
  expect(classifyNutritionGenerationOutcome("unknown_backend_value")).toBe("failed");
  expect(formatNutritionPlanMoney(1_234_567)).toBe("۱۲۰٬۰۰۰ تومان");
  expect(nutritionPlanPdfFilename("plan/id")).toBe("fitician-nutrition-plan-plan-id.pdf");
});

it("shows only public prepared-recipe nutrients and marks missing summaries estimated", () => {
  expect(preparedRecipePresentation({
    cost_irr: 120_000,
    food_id: null,
    grams: 250,
    item_kind: "prepared_recipe",
    name_en: "Prepared meal",
    name_fa: "غذای آماده",
    nutrients: { private_snapshot_value: 99 },
    slug: "prepared-meal",
  })).toEqual({
    costIrrPer100g: null,
    nutrients: [],
    status: "estimated",
  });

  expect(preparedRecipePresentation({
    cost_irr: 120_000,
    food_id: null,
    grams: 250,
    item_kind: "prepared_recipe",
    name_en: "Prepared meal",
    name_fa: "غذای آماده",
    nutrients: {},
    prepared_recipe: {
      cost_irr_per_100g: 345_678,
      nutrients_per_100g: {
        carbohydrate_g: 20.5,
        energy_kcal: 180,
        private_snapshot_value: 99,
        protein_g: 12,
      },
      status: "verified",
    },
    slug: "prepared-meal",
  })).toEqual({
    costIrrPer100g: 345_678,
    nutrients: [
      { code: "energy_kcal", value: 180 },
      { code: "protein_g", value: 12 },
      { code: "carbohydrate_g", value: 20.5 },
    ],
    status: "verified",
  });
});

it("anchors the nutrition view to the recurring template day from the timeline", () => {
  const presentation = nutritionTimelinePresentation({
    absolute_day_number: 9,
    day_id: "day-2",
    nutrient_totals: { energy_kcal: 2_100 },
    pattern_day_index: 1,
    plan_id: "plan-1",
    start_date: "2026-09-05",
    state: "active",
  } satisfies TimelineNutrition);

  expect(presentation).toEqual({
    absoluteDayNumber: 9,
    selectedDayIndex: 1,
    state: "active",
  });
});

it("preserves non-active nutrition timeline states for presentation", () => {
  expect(nutritionTimelinePresentation({ state: "no_plan" })).toEqual({
    absoluteDayNumber: null,
    selectedDayIndex: null,
    state: "none",
  });
  expect(nutritionTimelinePresentation({ state: "ready_to_start" })).toEqual({
    absoluteDayNumber: null,
    selectedDayIndex: null,
    state: "ready",
  });
  expect(nutritionTimelinePresentation({ state: "scheduled_start" })).toEqual({
    absoluteDayNumber: null,
    selectedDayIndex: null,
    state: "scheduled",
  });
});
