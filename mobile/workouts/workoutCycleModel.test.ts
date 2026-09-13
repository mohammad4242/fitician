import { expect, it } from "vitest";
import type { TimelineWorkout, TimelineWorkoutSession } from "@fitician/core/program-timeline";

import {
  completionFeedbackFormFromResponse,
  emptyCompletionFeedbackForm,
  emptyWeeklyCheckInForm,
  toCompletionFeedbackInput,
  toWeeklyCheckInInput,
  weeklyCheckInFormFromResponse,
  workoutTimelinePresentation,
} from "./workoutCycleModel";

const session: TimelineWorkoutSession = {
  day_number: 2,
  estimated_duration_minutes: 45,
  id: "session-2",
  scheduled_date: "2026-09-14",
  session_number: 2,
  status: "scheduled",
  title_en: "Pull",
  title_fa: "پول",
  week_number: 1,
  workout_day_id: "day-2",
};

function workout(overrides: Partial<TimelineWorkout> = {}): TimelineWorkout {
  return {
    completed_sessions: 0,
    state: "rest_day",
    total_sessions: 4,
    ...overrides,
  };
}

it("maps a saved weekly check-in into an editable native form", () => {
  expect(weeklyCheckInFormFromResponse({
    cycle_id: "cycle-1",
    created_at: "2026-09-01T00:00:00Z",
    has_pain_or_limitation: true,
    id: "check-in-1",
    note_optional: null,
    pain_follow_up: {
      created_at: "2026-09-01T00:00:00Z",
      id: "pain-1",
      note_optional: "زانو",
      workout_plan_exercise_id: "exercise-1",
    },
    perceived_difficulty: "hard",
    recovery_rating: "average",
    sessions_completed: 3,
    submitted_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
    user_id: "member-1",
    week_number: 2,
  })).toEqual({
    affectedExerciseId: "exercise-1",
    hasPainOrLimitation: true,
    painNote: "زانو",
    perceivedDifficulty: "hard",
    recoveryRating: "average",
    sessionsCompleted: 3,
  });
  expect(weeklyCheckInFormFromResponse(null)).toEqual(emptyWeeklyCheckInForm);
});

it("builds the exact weekly check-in request and clears irrelevant pain data", () => {
  expect(toWeeklyCheckInInput({
    affectedExerciseId: "exercise-1",
    hasPainOrLimitation: false,
    painNote: "ignored",
    perceivedDifficulty: "appropriate",
    recoveryRating: "good",
    sessionsCompleted: 2,
  })).toEqual({
    has_pain_or_limitation: false,
    note_optional: null,
    pain_follow_up: null,
    perceived_difficulty: "appropriate",
    recovery_rating: "good",
    sessions_completed: 2,
  });
});

it("maps end-cycle feedback defaults and preserves submitted values", () => {
  expect(completionFeedbackFormFromResponse(null)).toEqual(emptyCompletionFeedbackForm);
  const form = {
    ...emptyCompletionFeedbackForm,
    overallSatisfaction: "satisfied" as const,
    performanceChanges: "قدرت بیشتر شد",
  };
  expect(toCompletionFeedbackInput(form)).toEqual({
    energy_progress: "unchanged",
    endurance_progress: "unchanged",
    muscle_progress: "unchanged",
    note_optional: null,
    overall_difficulty: "appropriate",
    overall_recovery: "good",
    overall_satisfaction: "satisfied",
    pain_or_limitation_feedback: null,
    performance_changes: "قدرت بیشتر شد",
    strength_progress: "unchanged",
  });
});

it("maps timeline precedence to one focused session without choosing the first day", () => {
  expect(workoutTimelinePresentation(workout({
    next_session: session,
    overdue_session: { ...session, id: "session-1", session_number: 1 },
    state: "overdue",
    today_session: { ...session, id: "session-3", session_number: 3 },
  }))).toEqual({
    focusedSession: { ...session, id: "session-1", session_number: 1 },
    nextSession: session,
    state: "overdue",
  });

  expect(workoutTimelinePresentation(workout({
    next_session: session,
    state: "rest_day",
  }))).toEqual({
    focusedSession: null,
    nextSession: session,
    state: "rest",
  });

  expect(workoutTimelinePresentation(workout({
    state: "completed_today",
    today_session: { ...session, status: "completed" },
  }))).toEqual({
    focusedSession: { ...session, status: "completed" },
    nextSession: null,
    state: "completed",
  });
});
