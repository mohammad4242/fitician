import { fireEvent, render, screen } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";
import { SafeAreaProvider } from "react-native-safe-area-context";

import type { MemberWorkoutReview } from "./workoutReviewApi";
import { MemberWorkoutReviewCard } from "./MemberWorkoutReviewCard";

const review = {
  id: "review-1",
  source_plan_id: "source-plan",
  status: "awaiting_member_acceptance",
  draft_revision: 3,
  coach_note: "برای شروع ایمن‌تر تنظیم شد",
  member_rejection_note: null,
  coach_display_name: "مربی سارا",
  difference_summary: [
    {
      change_type: "rir_changed",
      day_number: 1,
      order_index: 1,
      generated: 2,
      approved: 3,
    },
  ],
  source_plan: {
    id: "source-plan",
    status: "active",
    days: [{
      id: "source-day",
      day_number: 1,
      title_fa: "بالاتنه",
      title_en: "Upper body",
      exercises: [{
        id: "source-exercise",
        order_index: 1,
        exercise: { name_fa: "پرس سینه", name_en: "Bench press" },
        sets: 3,
        reps_min: 8,
        reps_max: 12,
        rir: 2,
        rest_seconds: 90,
      }],
    }],
  },
  proposed_plan: {
    id: "proposed-plan",
    status: "pending_review",
    days: [{
      id: "proposed-day",
      day_number: 1,
      title_fa: "بالاتنه اصلاح‌شده",
      title_en: "Updated upper body",
      exercises: [{
        id: "proposed-exercise",
        order_index: 1,
        exercise: { name_fa: "پرس سینه", name_en: "Bench press" },
        sets: 3,
        reps_min: 8,
        reps_max: 12,
        rir: 3,
        rest_seconds: 90,
      }],
    }],
  },
} as unknown as MemberWorkoutReview;

function renderCard(onAccept = jest.fn(), onReject = jest.fn()) {
  return render(
    <SafeAreaProvider initialMetrics={{
      frame: { height: 800, width: 390, x: 0, y: 0 },
      insets: { bottom: 0, left: 0, right: 0, top: 0 },
    }}>
      <MemberWorkoutReviewCard
        busy={false}
        onAccept={onAccept}
        onReject={onReject}
        review={review}
      />
    </SafeAreaProvider>,
  );
}

test("shows the proposed changes and requires an explanation before rejection", () => {
  const onReject = jest.fn();
  renderCard(jest.fn(), onReject);

  expect(screen.getByRole("header", { name: "تغییرات پیشنهادی مربی" })).toBeTruthy();
  expect(screen.getByText("برنامه فعلی تا زمانی که تأیید نکنی فعال می‌ماند.")).toBeTruthy();
  expect(screen.getByText("RIR")).toBeTruthy();
  expect(screen.getByText("پرس سینه")).toBeTruthy();
  expect(screen.getByRole("button", { name: "درخواست اصلاح" }).props.accessibilityState).toMatchObject({ disabled: true });

  fireEvent.changeText(screen.getByLabelText("دلیل درخواست اصلاح"), "حرکت روز اول را ساده‌تر می‌خواهم");
  fireEvent.press(screen.getByRole("button", { name: "درخواست اصلاح" }));

  expect(onReject).toHaveBeenCalledWith("حرکت روز اول را ساده‌تر می‌خواهم");
});

test("locks member actions after the correction request is sent", () => {
  renderCard();

  fireEvent.changeText(screen.getByLabelText("دلیل درخواست اصلاح"), "اصلاح لازم است");
  const requested = { ...review, status: "member_changes_requested" } as MemberWorkoutReview;

  render(
    <MemberWorkoutReviewCard
      busy={false}
      onAccept={jest.fn()}
      onReject={jest.fn()}
      review={requested}
    />,
  );

  expect(screen.getByText("درخواست اصلاح ثبت شد؛ پیشنهاد به مربی برگشت.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "تأیید تغییرات مربی" }).props.accessibilityState).toMatchObject({ disabled: true });
});
