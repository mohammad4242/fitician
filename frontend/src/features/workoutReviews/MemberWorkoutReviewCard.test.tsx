import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import type { WorkoutPlan } from "../workouts/types";
import type { WorkoutReviewMemberDetail } from "./types";
import { MemberWorkoutReviewCard } from "./MemberWorkoutReviewCard";

const currentPlan = makePlan("current-plan", "حرکت فعلی", 3);
const proposedPlan = makePlan("proposed-plan", "حرکت پیشنهادی", 4);

const review: WorkoutReviewMemberDetail = {
  id: "review-1",
  source_plan_id: currentPlan.id,
  status: "awaiting_member_acceptance",
  draft_revision: 3,
  coach_note: "فشار جلسه اول را کمی بیشتر کردم.",
  member_rejection_note: null,
  source_plan: currentPlan,
  proposed_plan: proposedPlan,
  difference_summary: [{
    change_type: "sets_changed",
    day_number: 1,
    order_index: 1,
    generated: 3,
    approved: 4,
    generated_exercise_id: "exercise-current",
    approved_exercise_id: "exercise-proposed",
    provenance: {},
  }],
  coach_display_name: "مربی سارا",
};

it("shows the coach proposal, structured before/after values, and requires a rejection explanation", async () => {
  const user = userEvent.setup();
  const onAccept = vi.fn();
  const onReject = vi.fn();

  render(<MemberWorkoutReviewCard review={review} busy={false} onAccept={onAccept} onReject={onReject} />);

  expect(screen.getByRole("heading", { name: "تغییرات پیشنهادی مربی" })).toBeInTheDocument();
  expect(screen.getByText("فشار جلسه اول را کمی بیشتر کردم.")).toBeInTheDocument();
  expect(screen.getByText("۳", { selector: "b" })).toBeInTheDocument();
  expect(screen.getByText("۴", { selector: "b" })).toBeInTheDocument();
  expect(screen.getByText("حرکت فعلی")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "تأیید تغییرات مربی" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "درخواست اصلاح" })).toBeDisabled();

  await user.click(screen.getByRole("button", { name: "تأیید تغییرات مربی" }));
  expect(onAccept).toHaveBeenCalledOnce();

  const explanation = screen.getByRole("textbox", { name: "دلیل درخواست اصلاح" });
  await user.type(explanation, "حرکت جدید برای زانویم مناسب نیست.");
  await user.click(screen.getByRole("button", { name: "درخواست اصلاح" }));
  expect(onReject).toHaveBeenCalledWith("حرکت جدید برای زانویم مناسب نیست.");
});

it("keeps the proposal visible and locks actions after the member requests changes", () => {
  render(
    <MemberWorkoutReviewCard
      review={{ ...review, status: "member_changes_requested", member_rejection_note: "لطفاً شدت روز اول کمتر شود." }}
      busy={false}
      onAccept={vi.fn()}
      onReject={vi.fn()}
    />,
  );

  expect(screen.getByText("درخواست اصلاح ثبت شد؛ پیشنهاد به مربی برگشت.")).toBeInTheDocument();
  expect(screen.getByText("لطفاً شدت روز اول کمتر شود.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "تأیید تغییرات مربی" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "درخواست اصلاح" })).toBeDisabled();
});

function makePlan(id: string, exerciseName: string, sets: number): WorkoutPlan {
  return {
    id,
    status: id === "current-plan" ? "active" : "pending_review",
    created_at: "2026-09-15T08:00:00Z",
    activated_at: id === "current-plan" ? "2026-09-15T08:00:00Z" : null,
    plan_duration_weeks: 4,
    generation_source: "internal_engine",
    is_stale: false,
    days: [{
      id: `${id}-day-1`,
      day_number: 1,
      title_en: "Full body",
      title_fa: "تمام بدن",
      estimated_duration_minutes: 45,
      exercises: [{
        id: `${id}-exercise-1`,
        order_index: 1,
        sets,
        reps_min: 8,
        reps_max: 12,
        rest_seconds: 90,
        rir: 2,
        estimated_minutes: 6,
        notes_en: null,
        notes_fa: null,
        alternatives: [],
        exercise: {
          id: id === "current-plan" ? "exercise-current" : "exercise-proposed",
          slug: `${id}-exercise`,
          name_en: exerciseName,
          name_fa: exerciseName,
          content_type: "exercise",
          body_region: "upper_body",
          primary_muscle: "chest",
          muscle_focus: "mid_chest",
          labels: [],
          secondary_muscles: [],
          equipment: [],
          difficulty: "beginner",
          media_path: "/placeholder.svg",
          media_type: "placeholder",
        },
      }],
    }],
  };
}
