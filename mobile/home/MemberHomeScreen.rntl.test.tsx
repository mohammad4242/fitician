import { fireEvent, render, screen } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { SafeAreaProvider } from "react-native-safe-area-context";

jest.mock("@tanstack/react-query", () => ({ useQuery: jest.fn() }));
jest.mock("expo-router", () => ({ useRouter: jest.fn() }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("@expo/vector-icons", () => ({ MaterialCommunityIcons: () => null }));
jest.mock("../exercises/ExerciseMedia", () => ({
  ExerciseMedia: (props: Record<string, unknown>) => {
    const ReactRuntime = require("react") as typeof import("react");
    const ReactNative = require("react-native") as typeof import("react-native");
    return ReactRuntime.createElement(ReactNative.View, props);
  },
}));
jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../entitlements/EntitlementProvider", () => ({ useMobileEntitlements: jest.fn() }));
jest.mock("../ui/navigation/RouteGuards", () => ({ useMobileRouteSnapshot: jest.fn() }));
jest.mock("../platform/connectivity", () => ({
  connectivityMonitor: {
    getSnapshot: () => ({ status: "online" }),
    subscribe: jest.fn(() => jest.fn()),
  },
}));
jest.mock("../profile/profileApi", () => ({ createProfileApi: jest.fn() }));
jest.mock("../workouts/workoutApi", () => ({ createWorkoutPlanApi: jest.fn() }));
jest.mock("../nutrition/nutritionApi", () => ({ createNutritionApi: jest.fn() }));
jest.mock("../nutrition/nutritionPlanApi", () => ({ createNutritionPlanApi: jest.fn() }));
jest.mock("../nutrition/nutritionTrackingApi", () => ({ createNutritionTrackingApi: jest.fn() }));
jest.mock("../programTimeline/programTimelineApi", () => ({ createProgramTimelineApi: jest.fn() }));

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { formatPersianDateWithWeekday } from "@fitician/core";

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { useMobileEntitlements } from "../entitlements/EntitlementProvider";
import { createNutritionApi } from "../nutrition/nutritionApi";
import { createNutritionPlanApi } from "../nutrition/nutritionPlanApi";
import { createNutritionTrackingApi } from "../nutrition/nutritionTrackingApi";
import { createProfileApi } from "../profile/profileApi";
import { createProgramTimelineApi } from "../programTimeline/programTimelineApi";
import { useMobileRouteSnapshot } from "../ui/navigation/RouteGuards";
import { createWorkoutPlanApi } from "../workouts/workoutApi";
import { MemberHomeScreen } from "./MemberHomeScreen";

const mockPush = jest.fn();
const mockUseQuery = jest.mocked(useQuery);
const mockUseRouter = jest.mocked(useRouter);
const mockUseMobileAuth = jest.mocked(useMobileAuth);
const mockUseMobileEntitlements = jest.mocked(useMobileEntitlements);
const mockUseRouteSnapshot = jest.mocked(useMobileRouteSnapshot);
const mockCreateProfileApi = jest.mocked(createProfileApi);
const mockCreateWorkoutApi = jest.mocked(createWorkoutPlanApi);
const mockCreateNutritionApi = jest.mocked(createNutritionApi);
const mockCreateNutritionPlanApi = jest.mocked(createNutritionPlanApi);
const mockCreateNutritionTrackingApi = jest.mocked(createNutritionTrackingApi);
const mockCreateProgramTimelineApi = jest.mocked(createProgramTimelineApi);

let productMode: "both" | "training" = "both";
let workoutEntitled = true;
let bodyAnalysisEntitled = true;

const dailyTracking = {
  actual_totals: {
    carbohydrate_g: 70,
    energy_kcal: 750,
    protein_g: 52,
    total_fat_g: 24,
  },
  check_in_status: "on_plan",
  data_status: "sufficient",
  entries: [],
  entry_date: "2026-09-09",
  plan_revision_id: null,
};

const nutritionPlan = {
  days: [{
    nutrient_totals: {
      carbohydrate_g: 220,
      energy_kcal: 2000,
      protein_g: 140,
      total_fat_g: 65,
    },
    plan_date: "2026-09-09",
  }],
  physician_approved: true,
};

const activeWorkoutPlan = {
  days: [{
    day_number: 1,
    estimated_duration_minutes: 45,
    exercises: [],
    id: "workout-day-1",
    title_en: "First plan day",
    title_fa: "روز اول برنامه",
  }],
  id: "workout-plan-1",
  plan_duration_weeks: 4,
  status: "active",
};

const timelineSession = {
  day_number: 1,
  estimated_duration_minutes: 45,
  id: "session-1",
  scheduled_date: "2026-09-13",
  session_number: 1,
  status: "scheduled",
  title_en: "First plan day",
  title_fa: "روز اول برنامه",
  week_number: 1,
  workout_day_id: "workout-day-1",
};

let mockTimeline: {
  readonly local_date: string;
  readonly nutrition: {
    readonly absolute_day_number?: number | null;
    readonly effective_today?: {
      readonly absolute_day_number: number;
      readonly day_id: string;
      readonly nutrient_totals: Record<string, number>;
      readonly pattern_day_index: number;
      readonly plan_id: string;
      readonly start_date: string;
    } | null;
    readonly nutrient_totals?: Record<string, number>;
    readonly pattern_day_index?: number | null;
    readonly plan_id?: string | null;
    readonly start_date?: string | null;
    readonly state: "no_plan" | "pending_review" | "ready_to_start" | "scheduled_start" | "active";
  };
  readonly workout: Record<string, unknown>;
} | null = null;

function queryResult<T>(data: T) {
  return {
    data,
    error: null,
    isError: false,
    isFetching: false,
    isPending: false,
    isStale: false,
  } as never;
}

function resolved<T>(value: T) {
  return jest.fn<() => Promise<T>>().mockResolvedValue(value);
}

function renderHome() {
  return render(
    <SafeAreaProvider initialMetrics={{
      frame: { height: 800, width: 400, x: 0, y: 0 },
      insets: { bottom: 0, left: 0, right: 0, top: 0 },
    }}>
      <MemberHomeScreen />
    </SafeAreaProvider>,
  );
}

beforeEach(() => {
  productMode = "both";
  workoutEntitled = true;
  bodyAnalysisEntitled = true;
  mockTimeline = null;
  mockPush.mockClear();
  mockUseMobileAuth.mockReturnValue({
    download: jest.fn(),
    request: jest.fn(),
    status: "signed_in",
    user: { email: "mary@example.com", id: "user-1" },
  } as never);
  mockUseMobileEntitlements.mockReturnValue({
    error: null,
    hasEntitlement: (entitlement: string) => entitlement === "training.plan.generate" ? workoutEntitled : bodyAnalysisEntitled,
    loading: false,
    quotaFor: () => null,
    refresh: jest.fn(),
    retry: jest.fn(),
    snapshot: {} as never,
  } as never);
  mockUseRouteSnapshot.mockImplementation(() => ({
    profile: { completionState: "complete", productMode, status: "resolved" },
    session: { status: "signed_in", user: { email: "mary@example.com", id: "user-1" } },
    specialistAccess: { coach: "denied", physician: "denied" },
  } as never));
  mockUseRouter.mockReturnValue({ push: mockPush } as never);
  mockCreateProfileApi.mockReturnValue({ getSharedProfile: resolved({ display_name: "مریم" }) } as never);
  mockCreateWorkoutApi.mockReturnValue({
    get: resolved(null),
    getActive: resolved(null),
    getHistory: resolved([]),
  } as never);
  mockCreateNutritionApi.mockReturnValue({ getCurrentEstimate: resolved(null) } as never);
  mockCreateNutritionPlanApi.mockReturnValue({ getLatest: resolved(nutritionPlan) } as never);
  mockCreateNutritionTrackingApi.mockReturnValue({ getDailyTracking: resolved(dailyTracking) } as never);
  mockCreateProgramTimelineApi.mockReturnValue({ getToday: jest.fn() } as never);
  mockUseQuery.mockImplementation(({ queryKey }) => {
    const key = queryKey as readonly unknown[];
    if (key[0] === "profile") return queryResult({ display_name: "مریم" });
    if (key[0] === "program-timeline") return queryResult(mockTimeline);
    if (key[0] === "workouts") return queryResult(null);
    if (key[1] === "plan") return queryResult(nutritionPlan);
    if (key[1] === "estimate") return queryResult(null);
    return queryResult(dailyTracking);
  });
});

test("routes from the home dashboard to profile and feature destinations", () => {
  renderHome();

  expect(screen.getByRole("header", { name: "سلام، مریم" })).toBeTruthy();
  fireEvent.press(screen.getByLabelText("باز کردن پروفایل"));
  fireEvent.press(screen.getByRole("button", { name: "تحلیل بدن" }));
  fireEvent.press(screen.getByRole("button", { name: "ثبت غذا" }));
  fireEvent.press(screen.getByRole("button", { name: "نمایش جزئیات تغذیه" }));
  fireEvent.press(screen.getByRole("button", { name: "مشاهده برنامه" }));

  expect(mockPush.mock.calls).toEqual([
    ["/member/profile"],
    [{
      pathname: "/member/body-analysis-capture",
      params: { fresh: "1" },
    }],
    ["/member/nutrition-tracking"],
    ["/member/nutrition"],
    ["/member/workouts"],
  ]);
});

test("hides nutrition dashboard content when the member selects training only", () => {
  productMode = "training";
  renderHome();

  expect(screen.getByRole("button", { name: "تحلیل بدن" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "ثبت غذا" })).toBeNull();
  expect(screen.queryByRole("button", { name: "نمایش جزئیات تغذیه" })).toBeNull();
});

test("shows the next real workout on a rest day instead of the first plan day", () => {
  mockTimeline = {
    local_date: "2026-09-13",
    nutrition: { state: "no_plan" },
    workout: {
      completed_sessions: 0,
      current_week: 1,
      cycle_id: "cycle-1",
      duration_weeks: 4,
      next_session: { ...timelineSession, scheduled_date: "2026-09-14", session_number: 1 },
      state: "rest_day",
      total_sessions: 4,
      workout_plan_id: "workout-plan-1",
    },
  };
  mockUseQuery.mockImplementation(({ queryKey }) => {
    const key = queryKey as readonly unknown[];
    if (key[0] === "profile") return queryResult({ display_name: "مریم" });
    if (key[0] === "program-timeline") return queryResult(mockTimeline);
    if (key[0] === "workouts" && key[1] === "plan" && key[2] === "active") return queryResult(activeWorkoutPlan);
    if (key[0] === "workouts") return queryResult(null);
    if (key[1] === "plan") return queryResult(nutritionPlan);
    if (key[1] === "estimate") return queryResult(null);
    return queryResult(dailyTracking);
  });

  renderHome();

  expect(screen.getAllByText("روز استراحت").length).toBeGreaterThan(0);
  expect(screen.getByText(`تمرین بعدی: ${formatPersianDateWithWeekday("2026-09-14")}`)).toBeTruthy();
  expect(screen.queryByText("روز اول برنامه")).toBeNull();
});

test("shows a ready-to-start workout program on Home", () => {
  mockTimeline = {
    local_date: "2026-09-13",
    nutrition: { state: "no_plan" },
    workout: {
      completed_sessions: 0,
      duration_weeks: 4,
      next_session: timelineSession,
      state: "ready_to_start",
      total_sessions: 4,
      workout_plan_id: "workout-plan-1",
    },
  };
  mockUseQuery.mockImplementation(({ queryKey }) => {
    const key = queryKey as readonly unknown[];
    if (key[0] === "profile") return queryResult({ display_name: "مریم" });
    if (key[0] === "program-timeline") return queryResult(mockTimeline);
    if (key[0] === "workouts" && key[1] === "plan" && key[2] === "active") return queryResult(activeWorkoutPlan);
    if (key[0] === "workouts") return queryResult(null);
    if (key[1] === "plan") return queryResult(nutritionPlan);
    if (key[1] === "estimate") return queryResult(null);
    return queryResult(dailyTracking);
  });

  renderHome();

  expect(screen.getByText("برنامه آماده شروع است")).toBeTruthy();
  expect(screen.getByRole("button", { name: "شروع برنامه" })).toBeTruthy();
});

test("uses timeline targets and absolute nutrition day eight on Home", () => {
  mockTimeline = {
    local_date: "2026-09-13",
    nutrition: {
      absolute_day_number: 8,
      nutrient_totals: { energy_kcal: 2_100, protein_g: 140, total_fat_g: 65 },
      pattern_day_index: 0,
      plan_id: "nutrition-plan-1",
      start_date: "2026-09-06",
      state: "active",
    },
    workout: { completed_sessions: 0, state: "no_plan", total_sessions: 0 },
  };
  mockUseQuery.mockImplementation(({ queryKey }) => {
    const key = queryKey as readonly unknown[];
    if (key[0] === "profile") return queryResult({ display_name: "مریم" });
    if (key[0] === "program-timeline") return queryResult(mockTimeline);
    if (key[0] === "workouts") return queryResult(null);
    if (key[1] === "plan") return queryResult({ ...nutritionPlan, id: "nutrition-plan-1" });
    if (key[1] === "estimate") return queryResult(null);
    return queryResult(dailyTracking);
  });

  renderHome();

  expect(screen.getByText("۲٬۱۰۰")).toBeTruthy();
  expect(screen.getByText("امروز · روز ۸ برنامه")).toBeTruthy();
});

test("keeps Home targets on the effective plan during a future nutrition handoff", () => {
  mockTimeline = {
    local_date: "2026-09-14",
    nutrition: {
      state: "scheduled_start",
      plan_id: "future-plan",
      start_date: "2026-09-17",
      nutrient_totals: { energy_kcal: 3_000, protein_g: 180 },
      effective_today: {
        plan_id: "old-plan",
        start_date: "2026-09-01",
        absolute_day_number: 14,
        pattern_day_index: 6,
        day_id: "old-day",
        nutrient_totals: { energy_kcal: 2_200, protein_g: 150 },
      },
    },
    workout: { completed_sessions: 0, state: "no_plan", total_sessions: 0 },
  };
  mockUseQuery.mockImplementation(({ queryKey }) => {
    const key = queryKey as readonly unknown[];
    if (key[0] === "profile") return queryResult({ display_name: "مریم" });
    if (key[0] === "program-timeline") return queryResult(mockTimeline);
    if (key[0] === "workouts") return queryResult(null);
    if (key[1] === "plan") return queryResult({
      ...nutritionPlan,
      days: [{ nutrient_totals: { energy_kcal: 3_000, protein_g: 180 }, plan_date: "2026-09-17" }],
    });
    if (key[1] === "estimate") return queryResult(null);
    return queryResult({
      ...dailyTracking,
      actual_totals: {},
      data_status: "insufficient_data",
      entries: [],
      check_in_status: null,
    });
  });

  renderHome();

  expect(screen.getByText("۲٬۲۰۰")).toBeTruthy();
  expect(screen.getByText("۱۵۰g")).toBeTruthy();
  expect(screen.queryByText("۳٬۰۰۰")).toBeNull();
});

test("previews a pending workout when no active plan exists", () => {
  const pendingPlan = {
    days: [{
      day_number: 1,
      estimated_duration_minutes: 52,
      exercises: [{
        exercise: {
          media_path: "/media/exercises/pull-up.mp4",
          media_type: "video",
          name_en: "Close-grip pull-up",
          name_fa: "بارفیکس دست جمع",
        },
      }],
      title_en: "Upper body",
      title_fa: "زیربغل + سینه + سرشانه",
    }],
    id: "pending-plan",
    status: "pending_review",
  };
  mockUseQuery.mockImplementation(({ queryKey }) => {
    const key = queryKey as readonly unknown[];
    if (key[0] === "profile") return queryResult({ display_name: "مریم" });
    if (key[0] === "program-timeline") return queryResult(mockTimeline);
    if (key[0] === "workouts" && key[1] === "plan" && key[2] === "active") {
      return queryResult(null);
    }
    if (key[0] === "workouts" && key[1] === "plans") {
      return queryResult([{ id: "pending-plan", status: "pending_review" }]);
    }
    if (key[0] === "workouts" && key[1] === "plan" && key[2] === "pending-plan") {
      return queryResult(pendingPlan);
    }
    if (key[0] === "nutrition" && key[1] === "plan") return queryResult(nutritionPlan);
    if (key[0] === "nutrition" && key[1] === "estimate") return queryResult(null);
    return queryResult(dailyTracking);
  });

  renderHome();

  expect(screen.getByText("زیربغل + سینه + سرشانه")).toBeTruthy();
  expect(screen.getByLabelText("رسانه تمرین بارفیکس دست جمع")).toBeTruthy();
  expect(screen.getByText("در انتظار تأیید")).toBeTruthy();
  expect(screen.getByRole("button", { name: "مشاهده برنامه" })).toBeTruthy();
});

test("shows a locked workout card instead of implying generation is available to free members", () => {
  workoutEntitled = false;
  mockUseQuery.mockImplementation(({ queryKey }) => {
    const key = queryKey as readonly unknown[];
    if (key[0] === "profile") return queryResult({ display_name: "مریم" });
    if (key[0] === "program-timeline") return queryResult(mockTimeline);
    if (key[0] === "workouts") return queryResult(null);
    if (key[1] === "plan") return queryResult(nutritionPlan);
    if (key[1] === "estimate") return queryResult(null);
    return queryResult(dailyTracking);
  });

  renderHome();

  expect(screen.getByText("دسترسی لازم است")).toBeTruthy();
  expect(screen.getByText("برنامه‌ای وجود ندارد؛ ساخت برنامه با دسترسی فعلی ممکن نیست.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "مشاهده وضعیت دسترسی" })).toBeTruthy();
});

test("locks the body analysis quick action while keeping the action visible", () => {
  bodyAnalysisEntitled = false;
  renderHome();

  const bodyAction = screen.getByRole("button", { name: "تحلیل بدن" });
  expect(bodyAction.props.accessibilityState.disabled).toBe(true);
  expect(screen.getByText("برای شروع تحلیل بدن، دسترسی فعال لازم است.")).toBeTruthy();
});
