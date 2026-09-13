import { describe, expect, it } from "vitest";

import type {
  ProgramTimelineToday,
  TimelineNutrition,
  TimelineWorkout,
  TimelineWorkoutSession,
} from "@fitician/core/program-timeline";

import {
  programTimelineNutritionPresentation,
  programTimelinePresentation,
  programTimelineWorkoutPresentation,
} from "./programTimelineModel";

const session = {
  id: "session-1",
  workout_day_id: "day-1",
  week_number: 1,
  session_number: 1,
  scheduled_date: "2026-09-14",
  status: "scheduled",
  day_number: 1,
  title_fa: "تمرین اول",
  title_en: "First workout",
  estimated_duration_minutes: 45,
} as TimelineWorkoutSession;

function workout(
  state: TimelineWorkout["state"],
  extra: Partial<TimelineWorkout> = {},
): TimelineWorkout {
  return { state, ...extra } as TimelineWorkout;
}

function nutrition(
  state: TimelineNutrition["state"],
  extra: Partial<TimelineNutrition> = {},
): TimelineNutrition {
  return { state, ...extra } as TimelineNutrition;
}

describe("program timeline presentation", () => {
  it("focuses the overdue session and keeps the next future session", () => {
    const next = { ...session, id: "session-2", session_number: 2 };
    const result = programTimelineWorkoutPresentation(
      workout("overdue", {
        overdue_session: session,
        next_session: next,
      }),
    );

    expect(result).toEqual({
      state: "overdue",
      focusedSession: session,
      nextSession: next,
    });
  });

  it("does not focus a plan day on a rest day", () => {
    const result = programTimelineWorkoutPresentation(
      workout("rest_day", { next_session: session }),
    );

    expect(result).toEqual({
      state: "rest",
      focusedSession: null,
      nextSession: session,
    });
  });

  it("maps the recurring nutrition day without changing the absolute day", () => {
    const result = programTimelineNutritionPresentation(
      nutrition("active", {
        absolute_day_number: 9,
        pattern_day_index: 1,
        day_id: "nutrition-day-2",
        nutrient_totals: { energy_kcal: 2200 },
      }),
    );

    expect(result).toEqual({
      state: "active",
      absoluteDayNumber: 9,
      selectedDayIndex: 1,
      dayId: "nutrition-day-2",
      nutrientTotals: { energy_kcal: 2200 },
    });
  });

  it("returns neutral states when the timeline is unavailable", () => {
    expect(programTimelinePresentation(null)).toEqual({
      localDate: null,
      timezone: null,
      workout: {
        state: "none",
        focusedSession: null,
        nextSession: null,
      },
      nutrition: {
        state: "none",
        absoluteDayNumber: null,
        selectedDayIndex: null,
        dayId: null,
        nutrientTotals: {},
      },
    });
  });

  it("preserves the backend local date and timezone", () => {
    const result = programTimelinePresentation({
      local_date: "2026-09-13",
      timezone: "Asia/Tehran",
      workout: workout("ready_to_start"),
      nutrition: nutrition("ready_to_start"),
    } as ProgramTimelineToday);

    expect(result.localDate).toBe("2026-09-13");
    expect(result.timezone).toBe("Asia/Tehran");
    expect(result.workout.state).toBe("ready");
    expect(result.nutrition.state).toBe("ready");
  });
});
