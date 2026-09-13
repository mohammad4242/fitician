import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { localIsoDate, resolvedIanaTimeZone } from "@fitician/core/local-date";

const auth = vi.hoisted(() => ({
  user: {
    id: "1",
    email: "member@example.com",
    created_at: "2026-07-24T00:00:00Z",
    is_admin: false,
  },
}));
const profile = vi.hoisted(() => ({
  profile: { display_name: "محمد", plan_duration_weeks: 4 },
  productMode: "training" as "training" | "nutrition" | "both",
}));
const workoutApi = vi.hoisted(() => ({
  getActiveWorkoutPlan: vi.fn(),
  generateWorkoutPlan: vi.fn(),
  getProgramTimelineToday: vi.fn(),
}));
const nutritionApi = vi.hoisted(() => ({
  getLatestWeeklyNutritionPlan: vi.fn(),
  getDailyTracking: vi.fn(),
  getCurrentNutritionEstimate: vi.fn(),
}));
const entitlements = vi.hoisted(() => ({
  value: {
    snapshot: null,
    loading: false,
    error: null,
    retry: vi.fn(),
    hasEntitlement: vi.fn(() => true),
    quotaFor: vi.fn(() => null),
  },
}));

vi.mock("../features/auth/AuthContext", () => ({ useAuth: () => auth }));
vi.mock("../features/profile/ProfileContext", () => ({ useProfile: () => profile }));
vi.mock("../features/workouts/api", () => workoutApi);
vi.mock("../features/programTimeline/api", () => ({
  getProgramTimelineToday: workoutApi.getProgramTimelineToday,
}));
vi.mock("../features/nutrition/api", () => nutritionApi);
vi.mock("../features/entitlements/EntitlementContext", () => ({
  useEntitlements: () => entitlements.value,
}));
vi.mock("../shared/AuthenticatedHeader", () => ({ AuthenticatedHeader: () => null }));

import "../i18n";
import { DashboardPage } from "./DashboardPage";

beforeEach(() => {
  workoutApi.getActiveWorkoutPlan.mockReset();
  workoutApi.generateWorkoutPlan.mockReset();
  workoutApi.getProgramTimelineToday.mockReset();
  nutritionApi.getLatestWeeklyNutritionPlan.mockReset();
  nutritionApi.getDailyTracking.mockReset();
  nutritionApi.getCurrentNutritionEstimate.mockReset();
  entitlements.value.hasEntitlement.mockReset();
  entitlements.value.hasEntitlement.mockReturnValue(true);
  nutritionApi.getLatestWeeklyNutritionPlan.mockResolvedValue(null);
  nutritionApi.getDailyTracking.mockRejectedValue(new Error("not tracked"));
  nutritionApi.getCurrentNutritionEstimate.mockResolvedValue(null);
  workoutApi.getProgramTimelineToday.mockResolvedValue(undefined);
  profile.productMode = "training";
});

const timelineSession = (overrides: Record<string, unknown> = {}) => ({
  id: "session-1",
  workout_day_id: "day-1",
  week_number: 1,
  session_number: 1,
  scheduled_date: localIsoDate(),
  status: "scheduled",
  day_number: 1,
  title_fa: "روز اول",
  title_en: "Day one",
  estimated_duration_minutes: 52,
  ...overrides,
});

function workoutTimeline(workout: Record<string, unknown>, nutrition: Record<string, unknown> = { state: "no_plan" }) {
  return {
    local_date: localIsoDate(),
    timezone: resolvedIanaTimeZone(),
    workout,
    nutrition,
  };
}

it("surfaces the real next session instead of generic workout copy", async () => {
  workoutApi.getActiveWorkoutPlan.mockResolvedValue({
    id: "plan-1",
    days: [{ id: "day-1", day_number: 1, title_fa: "فشار بالاتنه", title_en: "Upper push", estimated_duration_minutes: 52, exercises: [] }],
  });
  workoutApi.getProgramTimelineToday.mockResolvedValue(workoutTimeline({
    state: "workout_today",
    workout_plan_id: "plan-1",
    today_session: timelineSession(),
  }));

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "فشار بالاتنه" })).toBeInTheDocument();
  expect(screen.getByText(/۵۲ دقیقه/)).toBeInTheDocument();
});

it("shows a rest day and the next real session without using the first plan day", async () => {
  workoutApi.getActiveWorkoutPlan.mockResolvedValue({
    id: "plan-1",
    days: [
      { id: "day-1", day_number: 1, title_fa: "روز اول", title_en: "Day one", estimated_duration_minutes: 45, exercises: [] },
      { id: "day-2", day_number: 2, title_fa: "روز دوم", title_en: "Day two", estimated_duration_minutes: 52, exercises: [] },
    ],
  });
  workoutApi.getProgramTimelineToday.mockResolvedValue(workoutTimeline({
    state: "rest_day",
    workout_plan_id: "plan-1",
    next_session: timelineSession({
      id: "session-2",
      workout_day_id: "day-2",
      session_number: 2,
      scheduled_date: "2026-09-15",
    }),
  }));

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  const workout = await screen.findByRole("region", { name: "روز استراحت" });
  expect(workout).toHaveTextContent("جلسه بعد");
  expect(workout).not.toHaveTextContent("روز اول");
});

it("uses the next workout's first real exercise media in the hero", async () => {
  workoutApi.getActiveWorkoutPlan.mockResolvedValue({
    id: "plan-1",
    days: [{
      id: "day-1",
      day_number: 1,
      title_fa: "فشار بالاتنه",
      title_en: "Upper push",
      estimated_duration_minutes: 52,
      exercises: [{
        order_index: 1,
        exercise: {
          id: "exercise-1",
          slug: "bench-press",
          name_fa: "پرس سینه",
          name_en: "Bench press",
          media_path: "/media/bench.webp",
          media_type: "image",
        },
      }],
    }],
  });
  workoutApi.getProgramTimelineToday.mockResolvedValue(workoutTimeline({
    state: "workout_today",
    workout_plan_id: "plan-1",
    today_session: timelineSession(),
  }));

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  expect(await screen.findByRole("img", { name: "نمایش حرکت پرس سینه" })).toHaveAttribute(
    "src",
    "/media/bench.webp",
  );
});

it("uses the current scientific estimate when no weekly plan exists", async () => {
  profile.productMode = "both";
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);
  nutritionApi.getCurrentNutritionEstimate.mockResolvedValue({
    confidence: "high",
    targets: {
      goal_calories: { preferred: 2200 },
      tdee: { preferred: 2557 },
      protein: { preferred: 130 },
      carbohydrate: { preferred: 280 },
      total_fat: { preferred: 68 },
    },
  });
  nutritionApi.getDailyTracking.mockResolvedValue({
    data_status: "sufficient",
    actual_totals: { energy_kcal: 1100, protein_g: 65, carbohydrate_g: 140, total_fat_g: 34 },
    entries: [{}],
  });

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  expect(await screen.findByText("۲٬۲۰۰")).toBeInTheDocument();
  expect(screen.getByText("هدف روزانه")).toBeInTheDocument();
  expect(screen.queryByText("۱٬۱۰۰")).not.toBeInTheDocument();
  expect(screen.getByRole("progressbar", { name: "پیشرفت کالری امروز" })).toHaveAttribute(
    "aria-valuenow",
    "2200",
  );
  expect(screen.getByRole("progressbar", { name: "پیشرفت کالری امروز" })).toHaveAttribute(
    "aria-valuemax",
    "2557",
  );
});

it("shows the target calories while retaining tracked macro totals", async () => {
  profile.productMode = "both";
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);
  nutritionApi.getLatestWeeklyNutritionPlan.mockResolvedValue({
    physician_approved: true,
    days: [{ plan_date: localIsoDate(), nutrient_totals: { energy_kcal: 2400, protein_g: 160, carbohydrate_g: 250, total_fat_g: 70 }, meals: [] }],
  });
  nutritionApi.getCurrentNutritionEstimate.mockResolvedValue({
    confidence: "high",
    targets: { tdee: { preferred: 2800 } },
  });
  nutritionApi.getDailyTracking.mockResolvedValue({ actual_totals: { energy_kcal: 1200, protein_g: 80, carbohydrate_g: 125, total_fat_g: 35 } });

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  expect(await screen.findByText("۲٬۴۰۰")).toBeInTheDocument();
  expect(screen.queryByText("۱٬۲۰۰")).not.toBeInTheDocument();
  expect(screen.getByText("۸۰g")).toBeInTheDocument();
  expect(screen.getByRole("progressbar", { name: "پیشرفت کالری امروز" })).toHaveAttribute("aria-valuemax", "2800");
});

it("shows nutrition targets and skips workout loading for nutrition-only members", async () => {
  profile.productMode = "nutrition";
  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  expect(await screen.findByRole("link", { name: /هدف روزانه تغذیه/ })).toHaveAttribute(
    "href",
    "/nutrition-estimate",
  );
  expect(workoutApi.getActiveWorkoutPlan).not.toHaveBeenCalled();
  expect(screen.queryByRole("link", { name: "برنامه تمرینی" })).not.toBeInTheDocument();
});

it("starts generating a plan when the member has no active plan", async () => {
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);
  workoutApi.generateWorkoutPlan.mockResolvedValue({ plan: {}, reused: false });
  const user = userEvent.setup();

  render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );

  await user.click(await screen.findByRole("button", { name: "شروع کن" }));

  expect(workoutApi.generateWorkoutPlan).toHaveBeenCalledOnce();
});

it("does not start workout generation without the entitlement", async () => {
  entitlements.value.hasEntitlement.mockReturnValue(false);
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  expect(await screen.findByText("این قابلیت در دسترسی فعلی تو نیست.")).toBeInTheDocument();
  expect(workoutApi.generateWorkoutPlan).not.toHaveBeenCalled();
});

it("links the primary CTA to the active workout plan", async () => {
  workoutApi.getActiveWorkoutPlan.mockResolvedValue({ id: "plan-1" });

  render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("link", { name: "شروع برنامه" })).toHaveAttribute(
    "href",
    "/workout-plan",
  );
});

it("presents a focused command center without cinematic media", async () => {
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);

  render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );

  await screen.findByRole("heading", { name: "سلام، محمد" });
  expect(screen.getByRole("region", { name: "وضعیت امروز" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "تمرین امروز" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "تمرین امروز" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "body analys" })).toHaveAttribute(
    "href",
    "/body-progress",
  );
  expect(document.querySelector("video")).not.toBeInTheDocument();
});

it("shows real profile context in the workout status", async () => {
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);

  render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );

  await screen.findByRole("heading", { name: "سلام، محمد" });
  expect(screen.getByText("دوره ۴ هفته‌ای")).toBeInTheDocument();
});

it("keeps workout, nutrition, and quick actions in the required priority", async () => {
  profile.productMode = "both";
  workoutApi.getActiveWorkoutPlan.mockResolvedValue({
    id: "plan-1",
    days: [{ id: "day-1", day_number: 1, title_fa: "فشار بالاتنه", title_en: "Upper push", estimated_duration_minutes: 52, exercises: [] }],
  });
  nutritionApi.getCurrentNutritionEstimate.mockResolvedValue({
    confidence: "high",
    targets: {
      goal_calories: { preferred: 2200 },
      protein: { preferred: 130 },
      carbohydrate: { preferred: 280 },
      total_fat: { preferred: 68 },
    },
  });

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  const workout = await screen.findByRole("region", { name: "تمرین امروز" });
  const nutrition = await screen.findByRole("link", { name: "هدف روزانه تغذیه" });
  const quickActions = screen.getByRole("navigation", { name: "دسترسی سریع" });

  expect(workout.compareDocumentPosition(nutrition) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(nutrition.compareDocumentPosition(quickActions) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("uses target-to-TDEE progress before and after food is tracked", async () => {
  profile.productMode = "both";
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);
  nutritionApi.getCurrentNutritionEstimate.mockResolvedValue({
    confidence: "high",
    targets: {
      goal_calories: { preferred: 2200 },
      tdee: { preferred: 2600 },
      protein: { preferred: 130 },
      carbohydrate: { preferred: 280 },
      total_fat: { preferred: 68 },
    },
  });

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  expect(await screen.findByRole("progressbar", { name: "پیشرفت کالری امروز" })).toHaveAttribute(
    "aria-valuenow",
    "2200",
  );
  expect(screen.getByRole("progressbar", { name: "پیشرفت کالری امروز" })).toHaveAttribute(
    "aria-valuemax",
    "2600",
  );
});

it("uses the blue tone at the exact 60 percent boundary and animates Home entry", async () => {
  profile.productMode = "both";
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);
  nutritionApi.getCurrentNutritionEstimate.mockResolvedValue({
    confidence: "high",
    targets: {
      goal_calories: { preferred: 1800 },
      tdee: { preferred: 3000 },
      protein: { preferred: 130 },
      carbohydrate: { preferred: 280 },
      total_fat: { preferred: 68 },
    },
  });
  nutritionApi.getDailyTracking.mockResolvedValue({
    data_status: "sufficient",
    actual_totals: { energy_kcal: 1200, protein_g: 65, carbohydrate_g: 140, total_fat_g: 34 },
    entries: [{ id: "entry-1" }],
  });

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  const ring = await screen.findByRole("progressbar", { name: "پیشرفت کالری امروز" });
  expect(ring).toHaveClass("fitician-progress-ring--mount-animated");
  expect(ring.style.getPropertyValue("--ring-color")).toBe("var(--fitician-blue)");
  expect(ring).toHaveAttribute("aria-valuenow", "1800");
  expect(ring).toHaveAttribute("aria-valuemax", "3000");
});

it("caps a gain target ring while showing the target above estimated expenditure", async () => {
  profile.productMode = "both";
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);
  nutritionApi.getCurrentNutritionEstimate.mockResolvedValue({
    confidence: "high",
    targets: {
      goal_calories: { preferred: 3000 },
      tdee: { preferred: 2400 },
      protein: { preferred: 130 },
      carbohydrate: { preferred: 280 },
      total_fat: { preferred: 68 },
    },
  });
  nutritionApi.getDailyTracking.mockResolvedValue({
    data_status: "sufficient",
    actual_totals: { energy_kcal: 2200, protein_g: 145, carbohydrate_g: 300, total_fat_g: 76 },
    entries: [{ id: "entry-1" }],
  });

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  const ring = await screen.findByRole("progressbar", { name: "پیشرفت کالری امروز" });
  expect(ring).toHaveTextContent("100%");
  expect(ring).toHaveAttribute("aria-valuenow", "3000");
  expect(ring).toHaveAttribute("aria-valuemax", "2400");
  expect(ring.style.getPropertyValue("--ring-color")).toBe("var(--fitician-danger)");
  expect(screen.getByText("۶۰۰ کیلوکالری بالاتر از مصرف تقریبی روزانه")).toBeInTheDocument();
});

it("shows estimated daily expenditure beside the calorie goal", async () => {
  profile.productMode = "both";
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);
  nutritionApi.getCurrentNutritionEstimate.mockResolvedValue({
    confidence: "high",
    targets: {
      goal_calories: { preferred: 2567 },
      tdee: { preferred: 2834 },
      protein: { preferred: 130 },
      carbohydrate: { preferred: 280 },
      total_fat: { preferred: 68 },
    },
  });

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  expect(await screen.findByText("۲٬۸۳۴")).toBeInTheDocument();
  expect(screen.getByText("مصرف تقریبی روزانه")).toBeInTheDocument();
  expect(screen.getByRole("progressbar", { name: "پیشرفت کالری امروز" })).toHaveAttribute("aria-valuenow", "2567");
  expect(screen.getByRole("progressbar", { name: "پیشرفت کالری امروز" })).toHaveAttribute("aria-valuemax", "2834");
});

it("hides estimated daily expenditure when TDEE is unavailable", async () => {
  profile.productMode = "both";
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);
  nutritionApi.getCurrentNutritionEstimate.mockResolvedValue({
    confidence: "high",
    targets: {
      goal_calories: { preferred: 2567 },
      protein: { preferred: 130 },
      carbohydrate: { preferred: 280 },
      total_fat: { preferred: 68 },
    },
  });

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  expect(await screen.findByText("۲٬۵۶۷")).toBeInTheDocument();
  expect(screen.queryByText("مصرف تقریبی روزانه")).not.toBeInTheDocument();
});

it("routes the minimal body and food analysis shortcuts to their real flows", async () => {
  profile.productMode = "both";
  workoutApi.getActiveWorkoutPlan.mockResolvedValue(null);

  render(<MemoryRouter><DashboardPage /></MemoryRouter>);

  const body = await screen.findByRole("link", { name: "body analys" });
  const food = screen.getByRole("link", { name: "food analys" });

  expect(body).toHaveAttribute("href", "/body-progress");
  expect(food).toHaveAttribute("href", "/nutrition-tracking");
  expect(body.textContent).toBe("body analys");
  expect(food.textContent).toBe("food analys");
  expect(body.querySelector("img")).not.toBeNull();
  expect(food.querySelector("img")).not.toBeNull();
});
