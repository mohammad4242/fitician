import { readFileSync } from "node:fs";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { formatTehranDateTime } from "@fitician/core";
import { ApiError } from "@fitician/core";

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

const coachWorkoutReviewStyles = readFileSync("src/features/workoutReviews/coachWorkoutReview.css", "utf8");

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
  member_rejection_note: null,
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

async function openCoachSection(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(await screen.findByRole("tab", { name: new RegExp(`^${name}`) }));
}

async function startCoachReview(user: ReturnType<typeof userEvent.setup>) {
  await openCoachSection(user, "صف بررسی");
  await user.click(await screen.findByRole("button", { name: "شروع بازبینی" }));
}

async function openCoachWorkoutTab(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("tab", { name: "برنامه تمرینی" }));
}

async function openCoachNotesTab(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("tab", { name: "یادداشت مربی" }));
}

it("keeps final coach actions in normal flow with mobile safe-area spacing", () => {
  const actionRule = coachWorkoutReviewStyles.match(/\.coach-review-actions\s*\{[^}]*\}/)?.[0] ?? "";

  expect(actionRule).not.toMatch(/position:\s*(?:sticky|fixed)/);
  expect(actionRule).not.toContain("inset-block-end");
  expect(actionRule).toContain("padding-bottom: max(");
  expect(coachWorkoutReviewStyles).not.toMatch(/\.coach-review-actions[^}]*position:\s*(?:sticky|fixed)/);
});

it("opens on the dashboard and aggregates the three coach queues", async () => {
  const approvedItem = {
    ...queueItem,
    id: "review-approved",
    status: "approved" as const,
    approved_at: "2026-09-13T08:00:00Z",
  };
  const mineItem = {
    ...queueItem,
    id: "review-mine",
    status: "claimed" as const,
    claimed_by_user_id: "coach-1",
  };
  api.listWorkoutReviews.mockImplementation(async (view) => {
    if (view === "mine") return [mineItem];
    if (view === "approved") return [approvedItem];
    return [queueItem];
  });

  renderPage();

  expect(await screen.findByRole("tab", { name: /^داشبورد/ })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("heading", { name: "نیاز به اقدام" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "فعالیت اخیر" })).toBeVisible();
  expect(api.listWorkoutReviews).toHaveBeenCalledWith("pending");
  expect(api.listWorkoutReviews).toHaveBeenCalledWith("mine");
  expect(api.listWorkoutReviews).toHaveBeenCalledWith("approved");

  const stats = screen.getByTestId("specialist-stats-grid");
  expect(stats).toHaveTextContent("در انتظار بررسی");
  expect(stats).toHaveTextContent("در حال بررسی من");
  expect(stats).toHaveTextContent("تأییدشده امروز");
});

it("shows the queue, searches by member, and sorts newest or oldest", async () => {
  const user = userEvent.setup();
  const newer = { ...queueItem, id: "review-newer", member_display_name: "سارا", created_at: "2026-09-13T08:00:00Z" };
  const older = { ...queueItem, id: "review-older", member_display_name: "رضا", created_at: "2026-08-09T08:00:00Z" };
  api.listWorkoutReviews.mockResolvedValue([older, newer]);
  renderPage();

  await openCoachSection(user, "صف بررسی");

  const list = screen.getByRole("list");
  expect(within(list).getAllByRole("listitem")).toHaveLength(2);
  const search = screen.getByRole("searchbox", { name: "جست‌وجوی نام کاربر" });
  await user.type(search, "سارا");
  expect(within(screen.getByRole("list")).getAllByRole("listitem")).toHaveLength(1);
  expect(screen.getByText("سارا")).toBeVisible();

  await user.clear(search);
  await user.selectOptions(screen.getByRole("combobox", { name: "مرتب‌سازی" }), "oldest");
  const oldestRows = within(screen.getByRole("list")).getAllByRole("listitem");
  expect(oldestRows[0]).toHaveTextContent("رضا");
  await user.selectOptions(screen.getByRole("combobox", { name: "مرتب‌سازی" }), "newest");
  const newestRows = within(screen.getByRole("list")).getAllByRole("listitem");
  expect(newestRows[0]).toHaveTextContent("سارا");
});

it("switches between the four workbench sections and shows an empty queue state", async () => {
  const user = userEvent.setup();
  api.listWorkoutReviews.mockResolvedValue([]);
  renderPage();

  await openCoachSection(user, "صف بررسی");
  expect(screen.getByText("صف بررسی خالی است")).toBeVisible();
  await openCoachSection(user, "پرونده‌های من");
  expect(screen.getByRole("tab", { name: /^پرونده‌های من/ })).toHaveAttribute("aria-selected", "true");
  await openCoachSection(user, "تاریخچه");
  expect(screen.getByRole("tab", { name: /^تاریخچه/ })).toHaveAttribute("aria-selected", "true");
  await openCoachSection(user, "داشبورد");
  expect(screen.getByRole("heading", { name: "نیاز به اقدام" })).toBeVisible();
});

it("opens a separate case view with all coach case tabs", async () => {
  const user = userEvent.setup();
  renderPage();

  await startCoachReview(user);

  expect(screen.getByRole("button", { name: "بازگشت به صف" })).toBeVisible();
  expect(screen.getByRole("tab", { name: "خلاصه" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("heading", { name: "خلاصهٔ کاربر" })).toBeVisible();
  for (const tabName of ["پروفایل و محدودیت‌ها", "برنامه تمرینی", "بازخورد و سوابق", "یادداشت مربی"]) {
    await user.click(screen.getByRole("tab", { name: tabName }));
    expect(screen.getByRole("tab", { name: tabName })).toHaveAttribute("aria-selected", "true");
  }
});

it("shows the workbench navigation and claims a pending plan", async () => {
  const user = userEvent.setup();
  renderPage();

  expect(await screen.findByRole("tab", { name: /^داشبورد/ })).toBeVisible();
  expect(screen.getByRole("tab", { name: /^صف بررسی/ })).toBeVisible();
  expect(screen.getByRole("tab", { name: /^پرونده‌های من/ })).toBeVisible();
  expect(screen.getByRole("tab", { name: /^تاریخچه/ })).toBeVisible();

  await startCoachReview(user);

  expect(api.claimWorkoutReview).toHaveBeenCalledWith("review-1");
  expect(screen.getByRole("tab", { name: /^پرونده‌های من/ })).toHaveAttribute("aria-selected", "true");
  await openCoachWorkoutTab(user);
  await user.click(screen.getByText("روز ۱"));
  await user.click(screen.getByText("حرکت ۱ · پرس سینه"));
  expect(await screen.findByLabelText("تعداد ست روز ۱ حرکت ۱")).toBeEnabled();
});

it("shows compact queue rows with sent timestamps", async () => {
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

  await openCoachSection(user, "صف بررسی");
  expect(await screen.findByRole("heading", { name: "صف بررسی" })).toBeVisible();
  expect(screen.getByText(`ارسال‌شده: ${formatTehranDateTime("2026-09-13T08:00:00Z")}`)).toBeVisible();
  expect(screen.getAllByTestId("coach-review-case-row")).toHaveLength(2);
});

it("shows approval timestamps in history rows", async () => {
  const approvedItem = {
    ...queueItem,
    status: "approved" as const,
    created_at: "2026-08-09T08:00:00Z",
    approved_at: "2026-09-13T08:00:00Z",
  };
  api.listWorkoutReviews.mockImplementation(async (view) => view === "approved" ? [approvedItem] : []);
  const user = userEvent.setup();
  renderPage();

  await openCoachSection(user, "تاریخچه");

  expect(await screen.findByRole("heading", { name: "تاریخچه تأییدها" })).toBeVisible();
  expect(screen.getByText(`تأییدشده: ${formatTehranDateTime("2026-09-13T08:00:00Z")}`)).toBeVisible();
});

it("renders each queue case as a compact actionable row", async () => {
  const user = userEvent.setup();
  renderPage();

  await openCoachSection(user, "صف بررسی");
  const row = await screen.findByTestId("coach-review-case-row");
  expect(row).toHaveAttribute("data-case-id", "review-1");
  expect(row).toHaveTextContent("محمد");
  expect(row).toHaveTextContent("در انتظار بررسی");
});

it("keeps detailed profile sections closed until the coach opens one", async () => {
  const user = userEvent.setup();
  renderPage();

  await startCoachReview(user);

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

  await startCoachReview(user);
  await openCoachWorkoutTab(user);

  const daySummary = screen.getByText("روز ۱");
  expect(daySummary.closest("details")).not.toBeNull();
  expect(daySummary.closest("details")).not.toHaveAttribute("open");
  expect(screen.getByLabelText("تعداد ست روز ۱ حرکت ۱")).not.toBeVisible();

  await user.click(daySummary);

  expect(daySummary.closest("details")).toHaveAttribute("open");
  const exerciseTitle = screen.getByText("حرکت ۱ · پرس سینه");
  expect(exerciseTitle.closest("details")).not.toHaveAttribute("open");
});

it("keeps each workout exercise closed until the coach opens it", async () => {
  const user = userEvent.setup();
  renderPage();

  await startCoachReview(user);
  await openCoachWorkoutTab(user);
  await user.click(screen.getByText("روز ۱"));

  const exerciseDisclosure = document.querySelector<HTMLElement>("[data-review-disclosure='coach-workout-exercise']");
  expect(exerciseDisclosure).not.toBeNull();
  expect(exerciseDisclosure).not.toHaveAttribute("open");
  expect(screen.getByLabelText("RIR روز ۱ حرکت ۱")).not.toBeVisible();

  await user.click(exerciseDisclosure?.querySelector("summary") as HTMLElement);

  expect(screen.getByLabelText("RIR روز ۱ حرکت ۱")).toBeVisible();
});

it("lets the coach add, reorder, rename, and remove days and exercises", async () => {
  const user = userEvent.setup();
  renderPage();
  await startCoachReview(user);
  await openCoachWorkoutTab(user);

  await user.click(screen.getByRole("button", { name: "افزودن روز" }));
  expect(screen.getByText("روز ۲")).toBeVisible();

  await user.click(screen.getByText("روز ۱"));
  await user.click(screen.getByRole("button", { name: "افزودن حرکت به روز ۱" }));
  expect(screen.getByText("حرکت ۲ · پرس سینه")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "حرکت ۲ از روز ۱ را حذف کن" }));
  expect(screen.queryByText("حرکت ۲ · پرس سینه")).not.toBeInTheDocument();

  const title = screen.getByLabelText("عنوان فارسی روز ۱");
  await user.clear(title);
  await user.type(title, "قدرت بالاتنه");
  expect(title).toHaveValue("قدرت بالاتنه");

  await user.click(screen.getByRole("button", { name: "روز ۲ را بالا ببر" }));
  await user.click(screen.getByRole("button", { name: "حذف روز ۲" }));
  expect(screen.queryByText("روز ۲")).not.toBeInTheDocument();
});

it("switches to review detail mode on narrow layouts and returns to the queue", async () => {
  const user = userEvent.setup();
  renderPage();

  expect(screen.queryByTestId("coach-review-case")).not.toBeInTheDocument();

  await startCoachReview(user);

  expect(screen.getByTestId("coach-review-case")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "بازگشت به صف" }));
  expect(screen.queryByTestId("coach-review-case")).not.toBeInTheDocument();
});

it("shows the coach explanation and keeps score details collapsed", async () => {
  const user = userEvent.setup();
  renderPage();

  await startCoachReview(user);

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
  await startCoachReview(user);
  await openCoachWorkoutTab(user);
  await user.click(screen.getByText("روز ۱"));
  await user.click(screen.getByText("حرکت ۱ · پرس سینه"));
  const sets = await screen.findByLabelText("تعداد ست روز ۱ حرکت ۱");
  await user.clear(sets);
  await user.type(sets, "4");
  await openCoachNotesTab(user);
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
  await startCoachReview(user);
  await openCoachWorkoutTab(user);
  await user.click(screen.getByText("روز ۱"));
  await user.click(screen.getByText("حرکت ۱ · پرس سینه"));
  const rir = await screen.findByLabelText("RIR روز ۱ حرکت ۱");

  await user.clear(rir);
  await user.type(rir, "4");
  await openCoachNotesTab(user);
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

it("submits the saved coach version and refreshes the mine queue", async () => {
  const user = userEvent.setup();
  api.approveWorkoutReview.mockResolvedValueOnce({
    ...detail,
    status: "awaiting_member_acceptance",
  });
  renderPage();
  await startCoachReview(user);
  await openCoachNotesTab(user);

  await user.click(screen.getByRole("button", { name: "ارسال برای تأیید کاربر" }));

  expect(api.approveWorkoutReview).toHaveBeenCalledWith("review-1", 1);
  expect(api.listWorkoutReviews).toHaveBeenLastCalledWith("mine");
  expect(screen.getByRole("tab", { name: /^پرونده‌های من/ })).toHaveAttribute("aria-selected", "true");
});

it("requires an explanation before returning a plan for correction", async () => {
  const user = userEvent.setup();
  renderPage();
  await startCoachReview(user);
  await openCoachNotesTab(user);

  const reject = screen.getByRole("button", { name: "برگشت برای اصلاح" });
  expect(reject).toBeDisabled();

  await user.type(screen.getByLabelText("یادداشت مربی برای کاربر"), "فرم را کنترل کن");
  expect(reject).toBeEnabled();
  await user.click(reject);

  expect(api.rejectWorkoutReview).toHaveBeenCalledWith("review-1", 1, "فرم را کنترل کن");
  expect(api.listWorkoutReviews).toHaveBeenLastCalledWith("mine");
});

it("shows the member correction request when reopening a returned proposal", async () => {
  const user = userEvent.setup();
  const requestedItem = {
    ...queueItem,
    status: "member_changes_requested" as const,
    claimed_by_user_id: "coach-1",
  };
  api.listWorkoutReviews.mockResolvedValue([requestedItem]);
  api.getWorkoutReview.mockResolvedValue({
    ...detail,
    status: "member_changes_requested",
    member_rejection_note: "حرکت روز اول را ساده‌تر می‌خواهم",
  });
  renderPage();

  await openCoachSection(user, "پرونده‌های من");
  await user.click(await screen.findByRole("button", { name: "مشاهده پرونده" }));

  expect(await screen.findByText("درخواست اصلاح کاربر", { selector: ".coach-review-member-feedback strong" })).toBeVisible();
  expect(screen.getByText("حرکت روز اول را ساده‌تر می‌خواهم")).toBeVisible();
});

it("hides editing actions for an approved read-only review", async () => {
  const user = userEvent.setup();
  const approvedItem = {
    ...queueItem,
    status: "approved" as const,
    approved_at: "2026-09-13T08:00:00Z",
  };
  api.listWorkoutReviews.mockResolvedValue([approvedItem]);
  api.getWorkoutReview.mockResolvedValue({ ...detail, status: "approved", approved_at: approvedItem.approved_at });
  renderPage();

  await openCoachSection(user, "تاریخچه");
  await user.click(screen.getByRole("button", { name: "مشاهده پرونده" }));

  await openCoachWorkoutTab(user);
  expect(await screen.findByText("نسخه تأییدشده")).toBeVisible();
  expect(screen.queryByRole("button", { name: "ذخیره پیش‌نویس" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "برگشت برای اصلاح" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "ارسال برای تأیید کاربر" })).not.toBeInTheDocument();
});

it("shows shared coach workflow language for a specialist access error", async () => {
  api.listWorkoutReviews.mockRejectedValueOnce(new ApiError(
    403,
    "private relationship note",
    null,
    "SPECIALIST_RELATIONSHIP_REQUIRED",
  ));

  renderPage();

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("این متخصص به پرونده موردنظر دسترسی ندارد");
  expect(alert).not.toHaveTextContent("private relationship note");
});
