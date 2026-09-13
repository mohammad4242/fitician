import type {
  ProgramTimelineToday,
  TimelineNutrition,
  TimelineWorkout,
  TimelineWorkoutSession,
} from "@fitician/core/program-timeline";

export type ProgramTimelineWorkoutState =
  | "completed"
  | "legacy"
  | "none"
  | "overdue"
  | "ready"
  | "rest"
  | "scheduled"
  | "today";

export type ProgramTimelineNutritionState =
  | "active"
  | "none"
  | "pending_review"
  | "ready"
  | "scheduled";

export type ProgramTimelineWorkoutPresentation = {
  readonly focusedSession: TimelineWorkoutSession | null;
  readonly nextSession: TimelineWorkoutSession | null;
  readonly state: ProgramTimelineWorkoutState;
};

export type ProgramTimelineNutritionPresentation = {
  readonly absoluteDayNumber: number | null;
  readonly dayId: string | null;
  readonly nutrientTotals: Record<string, number>;
  readonly selectedDayIndex: number | null;
  readonly state: ProgramTimelineNutritionState;
};

export type ProgramTimelinePresentation = {
  readonly localDate: string | null;
  readonly nutrition: ProgramTimelineNutritionPresentation;
  readonly timezone: string | null;
  readonly workout: ProgramTimelineWorkoutPresentation;
};

const emptyWorkout: ProgramTimelineWorkoutPresentation = {
  focusedSession: null,
  nextSession: null,
  state: "none",
};

const emptyNutrition: ProgramTimelineNutritionPresentation = {
  absoluteDayNumber: null,
  dayId: null,
  nutrientTotals: {},
  selectedDayIndex: null,
  state: "none",
};

export function programTimelineWorkoutPresentation(
  workout: TimelineWorkout | null | undefined,
): ProgramTimelineWorkoutPresentation {
  if (workout === null || workout === undefined || workout.state === "no_plan") {
    return emptyWorkout;
  }

  const state = workoutState(workout.state);
  const focusedSession = workout.state === "overdue"
    ? workout.overdue_session ?? null
    : workout.state === "completed_today" || workout.state === "workout_today"
      ? workout.today_session ?? null
      : null;

  return {
    focusedSession,
    nextSession: workout.next_session ?? null,
    state,
  };
}

export function programTimelineNutritionPresentation(
  nutrition: TimelineNutrition | null | undefined,
): ProgramTimelineNutritionPresentation {
  if (nutrition === null || nutrition === undefined || nutrition.state === "no_plan") {
    return emptyNutrition;
  }

  return {
    absoluteDayNumber: nutrition.absolute_day_number ?? null,
    dayId: nutrition.day_id ?? null,
    nutrientTotals: nutrition.nutrient_totals ?? {},
    selectedDayIndex: nutrition.pattern_day_index ?? null,
    state: nutritionState(nutrition.state),
  };
}

export function programTimelinePresentation(
  timeline: ProgramTimelineToday | null | undefined,
): ProgramTimelinePresentation {
  if (timeline === null || timeline === undefined) {
    return {
      localDate: null,
      timezone: null,
      workout: emptyWorkout,
      nutrition: emptyNutrition,
    };
  }

  return {
    localDate: timeline.local_date,
    timezone: timeline.timezone,
    workout: programTimelineWorkoutPresentation(timeline.workout),
    nutrition: programTimelineNutritionPresentation(timeline.nutrition),
  };
}

function workoutState(state: TimelineWorkout["state"]): ProgramTimelineWorkoutState {
  switch (state) {
    case "ready_to_start":
      return "ready";
    case "scheduled_start":
      return "scheduled";
    case "workout_today":
      return "today";
    case "overdue":
      return "overdue";
    case "rest_day":
      return "rest";
    case "legacy_cycle":
      return "legacy";
    case "completed_today":
    case "cycle_completed":
      return "completed";
    case "no_plan":
      return "none";
  }
}

function nutritionState(state: TimelineNutrition["state"]): ProgramTimelineNutritionState {
  switch (state) {
    case "pending_review":
      return "pending_review";
    case "ready_to_start":
      return "ready";
    case "scheduled_start":
      return "scheduled";
    case "active":
      return "active";
    case "no_plan":
      return "none";
  }
}
