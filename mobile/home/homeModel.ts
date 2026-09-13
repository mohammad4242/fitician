import { nutritionTargetToExpenditureRatio } from "@fitician/core";
import type { TimelineNutrition, TimelineWorkout, TimelineWorkoutSession } from "@fitician/core/program-timeline";
import type { NutritionDailyTracking } from "../nutrition/nutritionTrackingApi";
import type { NutritionEstimate } from "../nutrition/nutritionApi";
import type { WeeklyPlan } from "../nutrition/nutritionPlanApi";

export type HomeNutritionStatus = "empty" | "pending" | "ready" | "on_plan" | "off_plan";

export type HomeNutritionSummary = {
  readonly carbohydrate: number | null;
  readonly consumedCalories: number | null;
  readonly fat: number | null;
  readonly protein: number | null;
  readonly progress: number;
  readonly status: HomeNutritionStatus;
  readonly targetCalories: number | null;
  readonly estimatedDailyExpenditureCalories: number | null;
};

export type HomeWorkoutTimelineState =
  | "completed"
  | "legacy"
  | "none"
  | "overdue"
  | "ready"
  | "rest"
  | "scheduled"
  | "today";

export type HomeWorkoutSummary = {
  readonly focusedSession: TimelineWorkoutSession | null;
  readonly nextSession: TimelineWorkoutSession | null;
  readonly state: HomeWorkoutTimelineState;
};

export function homeWorkoutSummary(
  timeline: TimelineWorkout | null | undefined,
): HomeWorkoutSummary {
  if (timeline === null || timeline === undefined || timeline.state === "no_plan") {
    return { focusedSession: null, nextSession: null, state: "none" };
  }
  if (timeline.state === "ready_to_start") {
    return { focusedSession: null, nextSession: timeline.next_session ?? null, state: "ready" };
  }
  if (timeline.state === "scheduled_start") {
    return { focusedSession: null, nextSession: timeline.next_session ?? null, state: "scheduled" };
  }
  if (timeline.state === "workout_today") {
    return { focusedSession: timeline.today_session ?? null, nextSession: timeline.next_session ?? null, state: "today" };
  }
  if (timeline.state === "overdue") {
    return { focusedSession: timeline.overdue_session ?? null, nextSession: timeline.next_session ?? null, state: "overdue" };
  }
  if (timeline.state === "completed_today") {
    return { focusedSession: timeline.today_session ?? null, nextSession: timeline.next_session ?? null, state: "completed" };
  }
  if (timeline.state === "legacy_cycle") {
    return { focusedSession: null, nextSession: null, state: "legacy" };
  }
  if (timeline.state === "rest_day") {
    return { focusedSession: null, nextSession: timeline.next_session ?? null, state: "rest" };
  }
  return { focusedSession: null, nextSession: timeline.next_session ?? null, state: "completed" };
}

export function nutritionSummary(
  plan: Pick<WeeklyPlan, "days" | "physician_approved"> & Partial<Pick<WeeklyPlan, "physician_review_required">> | null | undefined,
  estimate: Pick<NutritionEstimate, "targets"> | null | undefined,
  tracking: Pick<NutritionDailyTracking, "actual_totals" | "check_in_status" | "data_status" | "entries"> | null | undefined,
  date: string,
  timeline?: TimelineNutrition | null,
): HomeNutritionSummary {
  const day = plan?.days.find((item) => item.plan_date === date);
  const planned = timeline?.nutrient_totals ?? day?.nutrient_totals ?? {};
  const targets = estimate?.targets ?? {};
  const targetCalories = numberValue(planned.energy_kcal) ?? firstTarget(targets.goal_calories);
  const targetProtein = numberValue(planned.protein_g) ?? firstTarget(targets.protein);
  const targetCarbohydrate = numberValue(planned.carbohydrate_g) ?? firstTarget(targets.carbohydrate);
  const targetFat = numberValue(planned.total_fat_g) ?? firstTarget(targets.total_fat);
  const estimatedDailyExpenditureCalories = firstTarget(targets.tdee);
  const hasActual = tracking != null && (
    tracking.data_status === "sufficient"
    || tracking.entries.length > 0
    || Object.values(tracking.actual_totals).some((value) => value > 0)
  );
  const actual = hasActual ? tracking?.actual_totals : null;
  const consumedCalories = numberValue(actual?.energy_kcal);
  const status = plan !== null && plan !== undefined && plan.physician_review_required === true && !plan.physician_approved
    ? "pending"
    : targetCalories === null
      ? "empty"
      : tracking?.check_in_status === "on_plan"
        ? "on_plan"
        : tracking?.check_in_status === "off_plan"
          ? "off_plan"
          : "ready";

  return {
    carbohydrate: numberValue(actual?.carbohydrate_g) ?? targetCarbohydrate,
    consumedCalories,
    fat: numberValue(actual?.total_fat_g) ?? targetFat,
    protein: numberValue(actual?.protein_g) ?? targetProtein,
    progress: nutritionTargetToExpenditureRatio(targetCalories, estimatedDailyExpenditureCalories),
    status,
    targetCalories,
    estimatedDailyExpenditureCalories,
  };
}

function firstTarget(target: NutritionEstimate["targets"][string] | undefined): number | null {
  for (const value of [target?.preferred, target?.minimum, target?.preferred_maximum, target?.maximum]) {
    const normalized = numberValue(value);
    if (normalized !== null) return normalized;
  }
  return null;
}

function numberValue(value: number | undefined | null): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
