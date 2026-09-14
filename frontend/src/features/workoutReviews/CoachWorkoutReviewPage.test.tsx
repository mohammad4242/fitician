import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { formatTehranDateTime } from "@fitician/core";

import type { ReviewProfileSummary, WorkoutReviewDetail, WorkoutReviewQueueItem } from "./types";

const api = vi.hoisted(() => ({
  listWorkoutReviews: vi.fn(),
  getWorkoutReview: vi.fn(),
  claimWorkoutReview: vi.fn(),
  renewWorkoutReview: vi.fn(),
  saveWorkoutReviewDraft: vi.fn(),
  approveWorkoutReview: vi.fn(),
  rejectWorkoutReview: vi.fn(),
}));

vi.mock("./api", () => api);
vi.mock("../../shared/AuthenticatedHeader", () => ({
  AuthenticatedHeader: () => <header>Fitician</header>,
}));

import { CoachWorkoutReviewPage } from "./CoachWorkoutReviewPage";

const queueItem: WorkoutReviewQueueItem = {
  id: "review-1",
  source_plan_id: "plan-1",
  user_id: "member-1",
  member_display_name: "محمد",
  fitness_goal: "build_muscle",
  experience_level: "beginner",
  status: "pending",
  claimed_by_user_id: null,
  lease_expires_at: null,
  draft_revision: 1,
  created_at: "2026-08-09T08:00:00Z",
  approved_at: null,
};

const profileSummary = {
  user_id: "member-1",
  display_name: "محمد",
  birth_date: "1995-04-12",
  age: 31,
  sex: "male",
  product_mode: "both",
  timezone: "Asia/Tehran",
  height_cm: 178,
  weight_kg: "76.50",
  weight_measured_at: "2026-09-13T08:00:00Z",
  shoulder_circumference_cm: "110",
  waist_circumference_cm: "84",
  hip_circumference_cm: "98",
  measurements_measured_at: "2026-09-13T08:00:00Z",
  fitness_goal: "build_muscle",
  experience_level: "beginner",
  training_age_months: 12,
  preferred_weekdays: [1, 3, 5],
  priority_muscles: ["chest"],
  training_days_per_week: 3,
  training_location: "gym",
  home_training_setup: null,
  available_equipment: null,
  session_duration_minutes: 45,
  training_intensity: "moderate",
  physical_limitations: "زانو درد خفیف",
  plan_duration_weeks: 4,
  workout_generation_method: "fitician_coach",
  training_cautions: ["knee"],
  profile_created_at: "2026-08-01T08:00:00Z",
  profile_updated_at: "2026-09-13T08:00:00Z",
  nutrition: {
    food_items: [{ kind: "favourite", name: "مرغ", details: null }],
  },
  medical: {
    flags: { complex_medication_food_interaction: true },
    conditions: [{ code: "controlled_hypertension", details: null }],
    medications: [{ name: "داروی فشار خون", dosage: "روزانه", notes: null }],
  },
} as unknown as ReviewProfileSummary;

const detail: WorkoutReviewDetail = {
  ...queueItem,
  status: "claimed",
  claimed_by_user_id: "coach-1",
  lease_expires_at: "2026-08-09T10:00:00Z",
  coach_note: null,
  profile_summary: profileSummary,
  draft: {
    days: [
      {
        day_number: 1,
        exercises: [
          {
            order_index: 1,
            exercise_id: "exercise-1",
            sets: 3,
            reps_min: 8,
            reps_max: 12,
            rir: 2,
            rest_seconds: 90,
            notes_en: null,
            notes_fa: null,
          },
        ],
      },
    ],
  },
  source_plan: {
    id: "plan-1",
    status: "active",
    created_at: "2026-08-09T08:00:00Z",
    activated_at: "2026-08-09T08:00:00Z",
    plan_duration_weeks: 4,
    generation_source: "ai",
    is_stale: false,
    days: [
      {
        day_number: 1,
        title_en: "Upper body",
        title_fa: "بالاتنه",
        estimated_duration_minutes: 45,
        exercises: [
          {
            id: "workout-plan-exercise-1",
            order_index: 1,
            sets: 3,
            reps_min: 8,
            reps_max: 12,
            rest_seconds: 90,
            rir: 2,
            estimated_minutes: 5,
            notes_en: null,
            notes_fa: null,
            alternatives: [],
            exercise: {
              id: "exercise-1",
              slug: "bench-press",
              name_en: "Bench Press",
              name_fa: "پرس سینه",
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
          },
        ],
      },
    ],
    coach_review: {
      state: "pending_coach_review",
      coach_display_name: null,
      coach_note: null,
      approved_at: null,
    },
  },
  exercise_options: [
    { id: "exercise-1", name_en: "Bench Press", name_fa: "پرس سینه" },
    { id: "exercise-2", name_en: "Push-Up", name_fa: "شنا سوئدی" },
  ],
  template_selection: {
    selected_template: "four-day-chest-priority",
    explanation_fa: "این ساختار به‌دلیل اولویت عضلانی صریح انتخاب شد.",
    explanation_en: "This structure was selected because of an explicit muscle priority.",
    score: {
      priority: 100,
      body_analysis: 20,
      goal: 10,
      sex: 0,
      fallback: 0,
      total: 130,
    },
  },
};

beforeEach(() => {
  Object.values(api).forEach((mock) => mock.mockReset());
  api.listWorkoutReviews.mockResolvedValue([queueItem]);
  api.claimWorkoutReview.mockResolvedValue(detail);
  api.getWorkoutReview.mockResolvedValue(detail);
  api.renewWorkoutReview.mockResolvedValue(detail);
  api.saveWorkoutReviewDraft.mockResolvedValue({ ...detail, draft_revision: 2 });
  api.approveWorkoutReview.mockResolvedValue({ ...detail, status: "approved" });
  api.rejectWorkoutReview.mockResolvedValue({ ...detail, status: "rejected", coach_note: "فرم را کنترل کن" });
});

function renderPage() {
  return render(
    <MemoryRouter>
      <CoachWorkoutReviewPage />
    </MemoryRouter>,
  );
}

it("shows the three review queues and claims a pending plan", async () => {
  const user = userEvent.setup();
  renderPage();

  expect(await screen.findByRole("tab", { name: "در انتظار بررسی" })).toBeVisible();
  expect(screen.getByRole("tab", { name: "در حال بررسی من" })).toBeVisible();
  expect(screen.getByRole("tab", { name: "تأییدشده" })).toBeVisible();

  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));

  expect(api.claimWorkoutReview).toHaveBeenCalledWith("review-1");
  expect(screen.getByRole("tab", { name: "در حال بررسی من" })).toHaveAttribute("aria-selected", "true");
  expect(await screen.findByLabelText("تعداد ست روز ۱ حرکت ۱")).toBeEnabled();
});

it("groups queue items by sent date and shows the sent timestamp", async () => {
  const user = userEvent.setup();
  api.listWorkoutReviews.mockResolvedValue([
    queueItem,
    {
      ...queueItem,
      id: "review-2",
      member_display_name: "سارا",
      created_at: "2026-09-13T08:00:00Z",
    },
  ]);
  renderPage();

  expect(await screen.findByRole("heading", { name: "این هفته" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "۵ هفته قبل" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "این هفته" }).closest("details")).not.toHaveAttribute("open");
  await user.click(screen.getByRole("heading", { name: "این هفته" }));
  expect(screen.getByText(`ارسال‌شده: ${formatTehranDateTime("2026-09-13T08:00:00Z")}`)).toBeVisible();

  const groups = [...document.querySelectorAll<HTMLElement>("[data-queue-group-key]")];
  expect(groups.map((group) => group.dataset.queueGroupKey)).toEqual(["week-0", "week-5"]);
});

it("groups approved cases by approval date and shows the approval timestamp", async () => {
  const approvedItem = {
    ...queueItem,
    status: "approved" as const,
    created_at: "2026-08-09T08:00:00Z",
    approved_at: "2026-09-13T08:00:00Z",
  };
  api.listWorkoutReviews.mockImplementation(async (view) => view === "approved" ? [approvedItem] : []);
  const user = userEvent.setup();
  renderPage();

  await user.click(await screen.findByRole("tab", { name: "تأییدشده" }));

  expect(await screen.findByRole("heading", { name: "این هفته" })).toBeVisible();
  await user.click(screen.getByRole("heading", { name: "این هفته" }));
  expect(screen.getByText(`تاریخ تأیید: ${formatTehranDateTime("2026-09-13T08:00:00Z")}`)).toBeVisible();
});

it("keeps each coach queue group collapsed until its header opens", async () => {
  const user = userEvent.setup();
  renderPage();

  const heading = await screen.findByRole("heading", { name: "۵ هفته قبل" });
  const group = heading.closest("details");
  const card = screen.getByRole("article");
  expect(group).not.toBeNull();
  expect(group).not.toHaveAttribute("open");
  expect(card).not.toBeVisible();

  await user.click(heading);

  expect(group).toHaveAttribute("open");
  expect(card).toBeVisible();
});

it("keeps detailed profile sections closed until the coach opens one", async () => {
  const user = userEvent.setup();
  renderPage();

  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));

  expect(await screen.findByRole("heading", { name: "خلاصهٔ کاربر" })).toBeVisible();
  expect(screen.getByText("۱۷۸ سانتی‌متر")).toBeVisible();
  expect(screen.getByText("۷۶٫۵ کیلوگرم")).toBeVisible();
  expect(screen.getByText("زانو درد خفیف")).toBeVisible();

  const bodySummary = screen.getByText("مشخصات بدنی و تمرین");
  expect(bodySummary.closest("details")).not.toHaveAttribute("open");
  expect(screen.getByText("باشگاه")).not.toBeVisible();
  await user.click(bodySummary);
  expect(screen.getByText("باشگاه")).toBeVisible();

  const nutritionSummary = screen.getByText("تغذیه و ترجیحات غذایی");
  expect(nutritionSummary.closest("details")).not.toHaveAttribute("open");
  await user.click(nutritionSummary);
  expect(screen.getByText("مرغ")).toBeVisible();

  const medicalSummary = screen.getByText("اطلاعات پزشکی و ایمنی");
  expect(medicalSummary.closest("details")).not.toHaveAttribute("open");
  await user.click(medicalSummary);
  expect(screen.getByText(/داروی فشار خون/)).toBeVisible();
});

it("keeps each workout day closed until the coach opens it", async () => {
  const user = userEvent.setup();
  renderPage();

  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));

  const daySummary = screen.getByText("روز ۱");
  expect(daySummary.closest("details")).not.toBeNull();
  expect(daySummary.closest("details")).not.toHaveAttribute("open");
  expect(screen.getByLabelText("تعداد ست روز ۱ حرکت ۱")).not.toBeVisible();

  await user.click(daySummary);

  expect(screen.getByLabelText("تعداد ست روز ۱ حرکت ۱")).toBeVisible();
});

it("switches to review detail mode on narrow layouts and returns to the queue", async () => {
  const user = userEvent.setup();
  renderPage();

  const workspace = document.querySelector(".coach-review-workspace");
  expect(workspace).not.toHaveClass("has-selected");

  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));

  expect(workspace).toHaveClass("has-selected");
  await user.click(screen.getByRole("button", { name: "بازگشت به صف" }));
  expect(workspace).not.toHaveClass("has-selected");
});

it("shows the coach explanation and keeps score details collapsed", async () => {
  const user = userEvent.setup();
  renderPage();

  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));

  const rationaleSummary = await screen.findByText("علت انتخاب برنامه");
  expect(rationaleSummary).toBeVisible();
  expect(rationaleSummary.closest("details")).not.toHaveAttribute("open");
  expect(screen.getByText(detail.template_selection!.explanation_fa)).toBeVisible();
  expect(screen.getByText("four-day-chest-priority")).not.toBeVisible();

  await user.click(rationaleSummary);
  await user.click(screen.getByText("جزئیات امتیازدهی"));

  expect(screen.getByText("four-day-chest-priority")).toBeVisible();
  expect(screen.getByText("۱۳۰")).toBeVisible();
  expect(screen.queryByText("DAYS_MISMATCH")).not.toBeInTheDocument();
});

it("saves permitted edits with the current revision", async () => {
  const user = userEvent.setup();
  renderPage();
  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));
  await user.click(screen.getByText("روز ۱"));
  const sets = await screen.findByLabelText("تعداد ست روز ۱ حرکت ۱");
  await user.clear(sets);
  await user.type(sets, "4");
  await user.type(screen.getByLabelText("یادداشت مربی برای کاربر"), "فرم را کنترل کن");

  await user.click(screen.getByRole("button", { name: "ذخیره پیش‌نویس" }));

  expect(api.saveWorkoutReviewDraft).toHaveBeenCalledWith(
    "review-1",
    expect.objectContaining({
      expected_revision: 1,
      coach_note: "فرم را کنترل کن",
      days: expect.arrayContaining([
        expect.objectContaining({
          exercises: expect.arrayContaining([expect.objectContaining({ sets: 4 })]),
        }),
      ]),
    }),
  );
});

it("allows the coach to edit RIR and sends it with the draft", async () => {
  const user = userEvent.setup();
  renderPage();
  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));
  await user.click(screen.getByText("روز ۱"));
  const rir = await screen.findByLabelText("RIR روز ۱ حرکت ۱");

  await user.clear(rir);
  await user.type(rir, "4");
  await user.click(screen.getByRole("button", { name: "ذخیره پیش‌نویس" }));

  expect(api.saveWorkoutReviewDraft).toHaveBeenCalledWith(
    "review-1",
    expect.objectContaining({
      days: expect.arrayContaining([
        expect.objectContaining({
          exercises: expect.arrayContaining([expect.objectContaining({ rir: 4 })]),
        }),
      ]),
    }),
  );
});

it("approves the saved coach version and refreshes the approved queue", async () => {
  const user = userEvent.setup();
  renderPage();
  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));

  await user.click(screen.getByRole("button", { name: "تأیید و ارسال برای کاربر" }));

  expect(api.approveWorkoutReview).toHaveBeenCalledWith("review-1", 1);
  expect(api.listWorkoutReviews).toHaveBeenLastCalledWith("approved");
});

it("requires an explanation before returning a plan for correction", async () => {
  const user = userEvent.setup();
  renderPage();
  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));

  const reject = screen.getByRole("button", { name: "برگشت برای اصلاح" });
  expect(reject).toBeDisabled();

  await user.type(screen.getByLabelText("یادداشت مربی برای کاربر"), "فرم را کنترل کن");
  expect(reject).toBeEnabled();
  await user.click(reject);

  expect(api.rejectWorkoutReview).toHaveBeenCalledWith("review-1", 1, "فرم را کنترل کن");
  expect(api.listWorkoutReviews).toHaveBeenLastCalledWith("mine");
});
