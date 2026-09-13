import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { afterEach, beforeEach, expect, jest, test } from "@jest/globals";
import { Linking, StyleSheet } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import type { ReactTestInstance } from "react-test-renderer";

jest.mock("@tanstack/react-query", () => ({
  useMutation: jest.fn(),
  useQuery: jest.fn(),
  useQueryClient: jest.fn(),
}));
jest.mock("expo-file-system", () => ({ Directory: class {}, File: class {}, Paths: { document: "document" } }));
jest.mock("expo-crypto", () => ({ randomUUID: jest.fn(() => "uuid") }));
jest.mock("expo-router", () => ({ useRouter: jest.fn() }));
jest.mock("@expo/vector-icons", () => ({ MaterialCommunityIcons: () => null }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../entitlements/EntitlementProvider", () => ({ useMobileEntitlements: jest.fn() }));
jest.mock("../programTimeline/programTimelineApi", () => ({ createProgramTimelineApi: jest.fn() }));

let mockConnectivityStatus: "online" | "offline" = "online";
jest.mock("../platform/connectivity", () => ({
  connectivityMonitor: {
    getSnapshot: () => ({ status: mockConnectivityStatus }),
    subscribe: jest.fn(() => jest.fn()),
  },
}));
jest.mock("./nutritionPlanApi", () => ({ createNutritionPlanApi: jest.fn() }));
jest.mock("./nutritionPlanActionsApi", () => ({ createNutritionPlanActionsApi: jest.fn() }));
jest.mock("./nutritionPlanPdfStore", () => ({ ExpoNutritionPlanPdfStore: jest.fn() }));

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { useMobileEntitlements } from "../entitlements/EntitlementProvider";
import { createProgramTimelineApi } from "../programTimeline/programTimelineApi";
import { fiticianTokens } from "../ui/tokens";
import { createNutritionPlanActionsApi } from "./nutritionPlanActionsApi";
import { NutritionPlanSection } from "./NutritionPlanSection";
import { createNutritionPlanApi, type WeeklyPlan } from "./nutritionPlanApi";
import { ExpoNutritionPlanPdfStore, type StoredNutritionPlanPdf } from "./nutritionPlanPdfStore";

const mockUseQuery = jest.mocked(useQuery);
const mockUseMutation = jest.mocked(useMutation);
const mockUseQueryClient = jest.mocked(useQueryClient);
const mockUseMobileAuth = jest.mocked(useMobileAuth);
const mockUseMobileEntitlements = jest.mocked(useMobileEntitlements);
const mockCreatePlanApi = jest.mocked(createNutritionPlanApi);
const mockCreateActionsApi = jest.mocked(createNutritionPlanActionsApi);
const mockCreateProgramTimelineApi = jest.mocked(createProgramTimelineApi);
const mockPdfStoreConstructor = jest.mocked(ExpoNutritionPlanPdfStore);

const mockDownloadPdf = jest.fn<(planId: string) => Promise<unknown>>();
const mockPdfGet = jest.fn<() => Promise<StoredNutritionPlanPdf | null>>();
const mockPdfSave = jest.fn<(planId: string, result: unknown) => Promise<StoredNutritionPlanPdf>>();
const mockShoppingRefetch = jest.fn<() => Promise<unknown>>();
const mockSetMealLock = jest.fn<(planId: string, mealId: string, locked: boolean) => Promise<{ meal_id: string; is_locked: boolean }>>();
const mockPartialRegenerate = jest.fn<(planId: string, dayIndexes: readonly number[]) => Promise<WeeklyPlan>>();
const mockInvalidateQueries = jest.fn<() => Promise<void>>().mockResolvedValue(undefined);
const mockSetQueryData = jest.fn();

const storedPdf = {
  byteSize: 4,
  fileName: "fitician-nutrition-plan-plan-1.pdf",
  planId: "plan-1",
  uri: "file:///document/fitician-nutrition-plans/fitician-nutrition-plan-plan-1.pdf",
};

function planDay(index: number): WeeklyPlan["days"][number] {
  const day = String(7 + index).padStart(2, "0");
  return {
    cost_irr: 2_000_000,
    day_index: index,
    meals: [{
      catalogue_meal_category: "lunch",
      catalogue_meal_id: "catalogue-meal-1",
      cost_irr: 300_000,
      foods: [{
        cost_irr: 120_000,
        food_id: "food-1",
        grams: 150,
        name_en: "Lentils",
        name_fa: "عدس",
        nutrients: { energy_kcal: 300, protein_g: 24 },
        item_kind: "food",
        slug: "lentils",
      }],
      id: `meal-${index}`,
      image_url: "/media/meal-catalogue/lu01.png",
      is_locked: false,
      meal_code: "LU01",
      name_en: "Chicken kebab, rice, and grilled tomato",
      name_fa: "جوجه کباب + برنج + گوجه کبابی",
      nutrient_totals: { carbohydrate_g: 220, energy_kcal: 700, protein_g: 40 },
      slot_index: 0,
      slot_role: "main_meal",
      target_distribution: { goal_calories: 700 },
    }],
    nutrient_totals: { carbohydrate_g: 220, energy_kcal: 2_100, protein_g: 140 },
    plan_date: `2026-09-${day}`,
  };
}

const activePlan: WeeklyPlan = {
  budget_status: "within_budget",
  created_at: "2026-09-07T00:00:00Z",
  days: Array.from({ length: 7 }, (_, index) => planDay(index)),
  explanation_codes: [],
  food_data_manifest: {},
  formula_version: "formula-v1",
  id: "plan-1",
  input_snapshot: { main_meals_per_day: 3, snacks_per_day: 1 },
  is_user_visible: true,
  lifecycle_status: "active",
  nutrients: {
    goal_calories: { data_confidence: "high", difference_from_limit: null, difference_from_preferred: 0, explanation_codes: [], minimum_or_maximum: null, nutrient_code: "goal_calories", planned: 2_100, preferred: 2_100, reason_codes: [], reference_kind: "target", status: "within_target", unit: "kcal/day" },
    protein: { data_confidence: "high", difference_from_limit: null, difference_from_preferred: 0, explanation_codes: [], minimum_or_maximum: null, nutrient_code: "protein", planned: 140, preferred: 140, reason_codes: [], reference_kind: "target", status: "within_target", unit: "g/day" },
    carbohydrate: { data_confidence: "high", difference_from_limit: null, difference_from_preferred: 0, explanation_codes: [], minimum_or_maximum: null, nutrient_code: "carbohydrate", planned: 220, preferred: 220, reason_codes: [], reference_kind: "target", status: "within_target", unit: "g/day" },
    total_fat: { data_confidence: "high", difference_from_limit: null, difference_from_preferred: 0, explanation_codes: [], minimum_or_maximum: null, nutrient_code: "total_fat", planned: 65, preferred: 65, reason_codes: [], reference_kind: "target", status: "within_target", unit: "g/day" },
  },
  physician_approved: true,
  physician_approved_at: "2026-09-07T00:00:00Z",
  physician_review_required: true,
  physician_change_summary: [],
  physician_display_name: null,
  physician_user_visible_notes: null,
  plan_role: "budget",
  planner_policy_version: "planner-policy-v1",
  planner_version: "planner-v1",
  price_snapshot: { references: [{ source: "approved" }] },
  repair_actions: [],
  review_status: "approved",
  revision: 2,
  scientific_policy_version: "science-v1",
  start_date: "2026-09-07",
  supersedes_plan_id: null,
  warning_codes: [],
  weekly_budget_irr: 10_000_000,
  weekly_cost_irr: 9_000_000,
};

const pendingPlan = {
  ...activePlan,
  id: "pending-plan",
  lifecycle_status: "pending_physician_review",
  physician_approved: false,
  physician_approved_at: null,
  physician_change_summary: [{ operation: "کاهش هزینه هفتگی" }],
  physician_user_visible_notes: "پروتئین این نسخه بررسی شود.",
  review_status: "pending",
};

const readyPlan = {
  ...activePlan,
  id: "ready-plan",
  lifecycle_status: "ready_to_start" as const,
};

const historicalPlan = {
  ...activePlan,
  id: "history-1",
  lifecycle_status: "archived",
  physician_approved: false,
  physician_approved_at: null,
  review_status: "archived",
  revision: 1,
};

const shoppingList = {
  approval_status: "approved",
  items: [{
    canonical_unit: "گرم",
    cost_irr: 120_000,
    food_id: "food-1",
    name_en: "Lentils",
    name_fa: "عدس",
    nutrients: {},
    required_quantity: 500,
    slug: "lentils",
  }],
  plan_id: "plan-1",
  plan_revision: 2,
  total_cost_irr: 120_000,
  warning_codes: [],
};

const historyVersion = {
  created_at: "2026-09-06T00:00:00Z",
  id: "history-1",
  lifecycle_status: "archived",
  revision: 1,
};

const activeHistoryVersion = {
  created_at: "2026-09-07T00:00:00Z",
  id: "plan-1",
  lifecycle_status: "active",
  revision: 2,
};

let mockDisplayedPlan: typeof activePlan = activePlan;
let mockLatestPlan: typeof activePlan | null = null;
let mockSelectedPlan: typeof historicalPlan | undefined;
let mockHistory: readonly typeof historyVersion[] = [historyVersion, activeHistoryVersion];
let mockBundle: unknown = null;
let mockShoppingLoading = false;
let mockShoppingError = false;
let mockTimeline: {
  readonly local_date: string;
  readonly nutrition: {
    readonly absolute_day_number?: number | null;
    readonly day_id?: string | null;
    readonly nutrient_totals?: Record<string, number>;
    readonly pattern_day_index?: number | null;
    readonly plan_id?: string | null;
    readonly start_date?: string | null;
    readonly state: "no_plan" | "pending_review" | "ready_to_start" | "scheduled_start" | "active";
  };
} | null = null;

function findAncestorStyle(node: ReactTestInstance, key: string): Record<string, unknown> {
  let current = node.parent;
  while (current !== null) {
    const style = StyleSheet.flatten(current.props.style) as Record<string, unknown> | undefined;
    if (style?.[key] !== undefined) return style;
    current = current.parent;
  }
  throw new Error(`Ancestor style ${key} not found`);
}

function queryResult<TData>(data: TData, overrides: Record<string, unknown> = {}) {
  return {
    data,
    error: null,
    isError: false,
    isFetching: false,
    isPending: false,
    isStale: false,
    refetch: jest.fn(),
    ...overrides,
  } as never;
}

function renderPlan() {
  return render(
    <SafeAreaProvider initialMetrics={{ frame: { height: 800, width: 390, x: 0, y: 0 }, insets: { bottom: 0, left: 0, right: 0, top: 0 } }}>
      <NutritionPlanSection safety={{ can_continue_onboarding: true } as never} />
    </SafeAreaProvider>,
  );
}

function openNutritionPlan() {
  fireEvent.press(screen.getByRole("button", { name: "برنامه تغذیه" }));
}

async function settlePdf() {
  await waitFor(() => expect(screen.queryByRole("progressbar", { name: "در حال بارگذاری" })).toBeNull());
}

beforeEach(() => {
  mockConnectivityStatus = "online";
  mockDisplayedPlan = activePlan;
  mockLatestPlan = null;
  mockSelectedPlan = historicalPlan;
  mockHistory = [historyVersion, activeHistoryVersion];
  mockBundle = null;
  mockShoppingLoading = false;
  mockShoppingError = false;
  mockTimeline = null;
  mockUseMobileAuth.mockReturnValue({ download: jest.fn(), request: jest.fn() } as never);
  mockUseMobileEntitlements.mockReturnValue({
    error: null,
    hasEntitlement: (entitlement: string) => entitlement === "nutrition.plan.generate" || entitlement === "nutrition.plan.manage",
    loading: false,
    quotaFor: () => null,
    refresh: jest.fn(),
    retry: jest.fn(),
    snapshot: {} as never,
  } as never);
  mockPdfGet.mockReset();
  mockPdfSave.mockReset();
  mockPdfGet.mockResolvedValue(null);
  mockPdfSave.mockResolvedValue(storedPdf);
  mockPdfStoreConstructor.mockImplementation(() => ({ get: mockPdfGet, save: mockPdfSave } as never));
  mockDownloadPdf.mockReset();
  mockDownloadPdf.mockResolvedValue({ bytes: Uint8Array.from([37, 80, 68, 70]), contentType: "application/pdf" });
  mockShoppingRefetch.mockReset();
  mockSetMealLock.mockReset();
  mockSetMealLock.mockResolvedValue({ meal_id: "meal-0", is_locked: true });
  mockPartialRegenerate.mockReset();
  mockPartialRegenerate.mockResolvedValue(activePlan);
  mockInvalidateQueries.mockClear();
  mockSetQueryData.mockClear();
  mockUseQueryClient.mockReturnValue({
    invalidateQueries: mockInvalidateQueries,
    setQueryData: mockSetQueryData,
  } as never);
  mockUseMutation.mockImplementation(() => ({ isPending: false, mutate: jest.fn() }) as never);
  mockCreatePlanApi.mockReturnValue({
    downloadPdf: mockDownloadPdf,
    generate: jest.fn(),
    get: jest.fn(),
    getActive: jest.fn(),
    getHistory: jest.fn(),
    getLatest: jest.fn(),
    getLatestBundle: jest.fn(),
    getShoppingList: jest.fn(),
    partialRegenerate: mockPartialRegenerate,
    selectBundle: jest.fn(),
    startPlan: jest.fn(),
  } as never);
  mockCreateProgramTimelineApi.mockReturnValue({ getToday: jest.fn() } as never);
  mockCreateActionsApi.mockReturnValue({
    confirmRemoveMeal: jest.fn(),
    confirmReplaceFood: jest.fn(),
    confirmReplaceMeal: jest.fn(),
    getFeedback: jest.fn(),
    getFoodReplacementOptions: jest.fn(),
    getMealReplacementOptions: jest.fn(),
    previewRemoveMeal: jest.fn(),
    previewReplaceFood: jest.fn(),
    previewReplaceMeal: jest.fn(),
    setMealFeedback: jest.fn(),
    setMealLock: mockSetMealLock,
  } as never);
  mockUseQuery.mockImplementation(({ queryKey }) => {
    const key = queryKey as readonly unknown[];
    if (key[0] === "program-timeline") return queryResult(mockTimeline);
    if (key[1] === "plan" && key[2] === "active") return queryResult(mockDisplayedPlan);
    if (key[1] === "plan" && key[2] === "latest") return queryResult(mockLatestPlan);
    if (key[1] === "plan-bundle") return queryResult(mockBundle);
    if (key[1] === "plans") return queryResult(mockHistory);
    if (key[1] === "meal-feedback") return queryResult({ feedback: {} });
    if (key[1] === "shopping-list") {
      if (mockShoppingLoading) return queryResult(undefined, { data: undefined, isPending: true });
      if (mockShoppingError) return queryResult(undefined, { data: undefined, error: new Error("shopping request failed"), isError: true, refetch: mockShoppingRefetch });
      return queryResult(shoppingList, { refetch: mockShoppingRefetch });
    }
    if (key[1] === "plan" && key[2] === "history-1") return queryResult(mockSelectedPlan);
    return queryResult(undefined);
  });
});

afterEach(async () => {
  cleanup();
  await act(async () => {
    await Promise.resolve();
  });
  jest.clearAllMocks();
});

test("renders the web heading, physician review, and compact metadata chips", async () => {
  renderPlan();
  await settlePdf();

  expect(screen.getByText("برنامه هفتگی")).toBeTruthy();
  expect(screen.getByText("برنامه غذایی تو")).toBeTruthy();
  expect(screen.getByText("تأییدشده توسط پزشک")).toBeTruthy();
  expect(screen.getByText("📋")).toBeTruthy();
  expect(screen.getByText("فعال")).toBeTruthy();
  expect(screen.getByText("قیمت‌ها به‌روز و معتبر")).toBeTruthy();
  expect(screen.getByText("چیدمان: ۳ وعده اصلی + ۱ میان‌وعده")).toBeTruthy();
  expect(screen.queryByText("برنامه غذایی هفتگی")).toBeNull();
  expect(screen.queryByText("نسخه فعال و تاریخچه برنامه‌ها")).toBeNull();

  expect(findAncestorStyle(screen.getByText("برنامه غذایی تو"), "alignItems")).toMatchObject({ alignItems: "stretch" });
  expect(findAncestorStyle(screen.getByText("قیمت‌ها به‌روز و معتبر"), "borderRadius")).toMatchObject({ borderRadius: 999 });
  expect(StyleSheet.flatten(screen.getByText("برنامه هفتگی").props.style)).toMatchObject({
    textAlign: "auto",
    writingDirection: "rtl",
  });
  expect(StyleSheet.flatten(screen.getByText("برنامه غذایی تو").props.style)).toMatchObject({
    textAlign: "auto",
    writingDirection: "rtl",
  });
});

test("shows the approved physician card with the green visual state", async () => {
  renderPlan();
  await settlePdf();

  const reviewText = screen.getByText("تأییدشده توسط پزشک");
  expect(screen.getByText(/تاریخ تأیید:/)).toBeTruthy();
  expect(findAncestorStyle(reviewText, "borderColor")).toMatchObject({ borderColor: fiticianTokens.colors.success });
  expect(findAncestorStyle(reviewText, "backgroundColor")).toMatchObject({ backgroundColor: fiticianTokens.colors.successSurface });
  expect(StyleSheet.flatten(reviewText.props.style)).toMatchObject({ color: fiticianTokens.colors.success });
  expect(findAncestorStyle(screen.getByText("🧑‍⚕️"), "backgroundColor")).toMatchObject({
    backgroundColor: fiticianTokens.colors.successSurface,
  });
});

test("shows the pending physician card, notes, and change summary", async () => {
  mockDisplayedPlan = pendingPlan;
  mockHistory = [];
  renderPlan();
  await settlePdf();

  const reviewText = screen.getByText("در انتظار بررسی پزشک");
  expect(screen.getByText("پیش‌نویس موقت؛ نیازمند بررسی پزشک")).toBeTruthy();
  expect(screen.getByText("پروتئین این نسخه بررسی شود.")).toBeTruthy();
  expect(screen.getByText("کاهش هزینه هفتگی")).toBeTruthy();
  expect(findAncestorStyle(reviewText, "borderColor")).toMatchObject({ borderColor: fiticianTokens.colors.amber });
  expect(findAncestorStyle(reviewText, "backgroundColor")).toMatchObject({ backgroundColor: fiticianTokens.colors.warningSurface });
});

test("shows an explicit start control for a ready nutrition plan", async () => {
  mockDisplayedPlan = readyPlan;
  mockHistory = [];
  mockTimeline = {
    local_date: "2026-09-13",
    nutrition: { plan_id: "ready-plan", state: "ready_to_start" },
  };

  renderPlan();
  await settlePdf();

  expect(screen.getByText("برنامه تغذیه آماده شروع است")).toBeTruthy();
  expect(screen.getByRole("button", { name: "شروع برنامه غذایی" })).toBeTruthy();
  expect(screen.getByLabelText("تاریخ شروع برنامه غذایی")).toBeTruthy();
});

test("opens the recurring nutrition template on the timeline pattern day", async () => {
  mockTimeline = {
    local_date: "2026-09-13",
    nutrition: {
      absolute_day_number: 9,
      day_id: "day-2",
      nutrient_totals: { energy_kcal: 2_100 },
      pattern_day_index: 1,
      plan_id: "plan-1",
      start_date: "2026-09-05",
      state: "active",
    },
  };

  renderPlan();
  await settlePdf();
  openNutritionPlan();

  const tabs = screen.getAllByRole("tab");
  expect(tabs[1]?.props.accessibilityState).toMatchObject({ selected: true });
  expect(screen.getByText(/امروز · روز ۹ برنامه/u)).toBeTruthy();
});

test("selecting a ready plan refreshes timeline without caching it as active", async () => {
  mockBundle = {
    bundle_id: "bundle-1",
    budget_plan: activePlan,
    comparison: { monthly_cost_gap_irr: 100_000, show_ideal_plan: true },
    ideal_plan: readyPlan,
    selected_plan_id: activePlan.id,
    selected_plan_role: "budget",
  };
  const selectBundle = jest.fn(async () => ({
    bundle_id: "bundle-1",
    plan: readyPlan,
    selected_plan_id: readyPlan.id,
    selected_plan_role: "ideal",
    selected_at: "2026-09-14T00:00:00Z",
  }));
  mockCreatePlanApi.mockReturnValue({
    downloadPdf: mockDownloadPdf,
    generate: jest.fn(),
    get: jest.fn(),
    getActive: jest.fn(),
    getHistory: jest.fn(),
    getLatest: jest.fn(),
    getLatestBundle: jest.fn(),
    getShoppingList: jest.fn(),
    partialRegenerate: mockPartialRegenerate,
    selectBundle,
    startPlan: jest.fn(),
  } as never);
  mockUseMutation.mockImplementation(((options: {
    mutationFn: (variables: unknown) => Promise<unknown>;
    onSuccess?: (result: unknown) => void | Promise<void>;
  }) => ({
    isPending: false,
    mutate: (variables: unknown) => {
      void options.mutationFn(variables).then((result) => options.onSuccess?.(result));
    },
  })) as never);

  renderPlan();
  fireEvent.press(screen.getByRole("radio", { name: "نسخه ایده‌آل" }));

  await waitFor(() => expect(selectBundle).toHaveBeenCalled());
  await waitFor(() => expect(mockInvalidateQueries).toHaveBeenCalledWith({
    queryKey: ["program-timeline"],
  }));
  expect(mockSetQueryData).not.toHaveBeenCalledWith(
    ["nutrition", "plan", "active"],
    readyPlan,
  );
});

test("does not present a standard nutrition plan as waiting for a physician", async () => {
  mockDisplayedPlan = {
    ...activePlan,
    lifecycle_status: "active",
    physician_approved: false,
    physician_approved_at: null,
    physician_review_required: false,
    review_status: "pending",
  };
  renderPlan();
  await settlePdf();

  expect(screen.getByText("بررسی پزشک لازم نیست")).toBeTruthy();
  expect(screen.queryByText("در انتظار بررسی پزشک")).toBeNull();
  expect(screen.queryByText("پیش‌نویس موقت؛ نیازمند بررسی پزشک")).toBeNull();
});

test("starts all three web sections collapsed and reveals their content independently", async () => {
  renderPlan();
  await settlePdf();

  expect(screen.getByRole("button", { name: "برنامه تغذیه" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "هدف در برابر مقدار برنامه" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "لیست خرید دقیق" })).toBeTruthy();
  expect(screen.queryByText("هزینه برآوردی هفته")).toBeNull();
  expect(screen.queryByText("هدف روزانه")).toBeNull();
  expect(screen.queryByText("عدس")).toBeNull();

  openNutritionPlan();
  expect(screen.getByText("هزینه برآوردی هفته")).toBeTruthy();
  expect(screen.getByText("بودجه هفتگی")).toBeTruthy();
  expect(screen.getByText("وضعیت بودجه")).toBeTruthy();
  expect(screen.getAllByRole("tab")).toHaveLength(7);
  for (const label of ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]) {
    expect(screen.getAllByText(label).length).toBeGreaterThan(0);
  }
  expect(screen.getByText("جمع روز")).toBeTruthy();
  expect(screen.getByText("تاریخچه نسخه‌ها")).toBeTruthy();

  fireEvent.press(screen.getByRole("button", { name: "هدف در برابر مقدار برنامه" }));
  expect(screen.getByText("انرژی")).toBeTruthy();
  expect(screen.getByText("۲٬۱۰۰ kcal/day")).toBeTruthy();
  expect(screen.getAllByText("در محدوده").length).toBeGreaterThan(0);

  fireEvent.press(screen.getByRole("button", { name: "لیست خرید دقیق" }));
  expect(screen.getByText("عدس")).toBeTruthy();
  expect(screen.getByText("۵۰۰ گرم")).toBeTruthy();
  expect(screen.getByText("جمع هزینه مرجع تأییدشده")).toBeTruthy();
});

test("keeps revision history inside the nutrition disclosure and selects a historical plan", async () => {
  renderPlan();
  await settlePdf();
  openNutritionPlan();

  fireEvent.press(screen.getByText("نسخه ۱"));
  await settlePdf();

  expect(screen.getAllByText("نسخه قبلی").length).toBeGreaterThan(0);
  expect(screen.getByText("این نسخه فقط برای مشاهده تاریخچه است و برنامه فعال تو نیست.")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "لیست خرید دقیق" })).toBeNull();
});

test("keeps meal editing controls available inside the selected day", async () => {
  renderPlan();
  await settlePdf();
  openNutritionPlan();
  fireEvent.press(screen.getByRole("button", { name: "LU01 — جوجه کباب + برنج + گوجه کبابی" }));

  expect(screen.getByText("۷۰۰ kcal")).toBeTruthy();
  expect(screen.getByRole("button", { name: "قفل وعده" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "پسندیدم" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "کمتر پیشنهاد بده" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "تعویض وعده" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "تعویض ماده غذایی" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "حذف وعده" })).toBeTruthy();

  fireEvent.press(screen.getByRole("button", { name: "قفل وعده" }));
  await waitFor(() => expect(mockSetMealLock).toHaveBeenCalledWith("plan-1", "meal-0", true));
});

test("keeps the unlocked-meal regeneration action inside the selected day", async () => {
  renderPlan();
  await settlePdf();
  openNutritionPlan();

  fireEvent.press(screen.getByRole("button", { name: "بازسازی وعده‌های باز این روز" }));

  await waitFor(() => expect(mockPartialRegenerate).toHaveBeenCalledWith("plan-1", [0]));
});

test("uses the web-style PDF CTA for download and storage", async () => {
  renderPlan();
  await settlePdf();

  const button = screen.getByRole("button", { name: "دانلود نسخه PDF برنامه غذایی" });
  expect(screen.getByText("دریافت فایل چاپی کامل با روزها، عکس غذاها و جدول ماکروها")).toBeTruthy();
  fireEvent.press(button);

  await waitFor(() => {
    expect(mockDownloadPdf).toHaveBeenCalledWith("plan-1");
    expect(mockPdfSave).toHaveBeenCalledWith("plan-1", expect.anything());
  });
  expect(findAncestorStyle(button, "borderColor")).toMatchObject({ borderColor: fiticianTokens.colors.aqua });
});

test("opens an already stored PDF from the same CTA", async () => {
  mockPdfGet.mockResolvedValue(storedPdf);
  const openUrl = jest.spyOn(Linking, "openURL").mockResolvedValue(true);
  renderPlan();
  await settlePdf();

  fireEvent.press(screen.getByRole("button", { name: "دانلود نسخه PDF برنامه غذایی" }));

  await waitFor(() => expect(openUrl).toHaveBeenCalledWith(storedPdf.uri));
  openUrl.mockRestore();
});

test("keeps PDF loading, offline, and error states actionable", async () => {
  mockPdfGet.mockReturnValue(new Promise<null>(() => undefined));
  const loadingView = renderPlan();
  expect(screen.getByRole("progressbar", { name: "در حال بارگذاری" })).toBeTruthy();
  loadingView.unmount();

  mockConnectivityStatus = "offline";
  mockPdfGet.mockResolvedValue(null);
  const offlineView = renderPlan();
  await settlePdf();
  const offlineButton = screen.getByRole("button", { name: "دانلود نسخه PDF برنامه غذایی" });
  expect(offlineButton.props.accessibilityState.disabled).toBe(true);
  expect(screen.getByText("برای دریافت PDF به اینترنت وصل شو.")).toBeTruthy();
  offlineView.unmount();

  mockConnectivityStatus = "online";
  mockPdfGet.mockResolvedValue(null);
  mockDownloadPdf.mockRejectedValue(new Error("PDF failed"));
  renderPlan();
  await settlePdf();
  fireEvent.press(screen.getByRole("button", { name: "دانلود نسخه PDF برنامه غذایی" }));
  await waitFor(() => expect(screen.getByText("دریافت یا باز کردن PDF انجام نشد؛ دوباره تلاش کن.")).toBeTruthy());
});

test("keeps shopping loading and retryable error states inside its disclosure", async () => {
  mockShoppingLoading = true;
  const loadingView = renderPlan();
  await settlePdf();
  fireEvent.press(screen.getByRole("button", { name: "لیست خرید دقیق" }));
  expect(screen.getAllByRole("progressbar", { name: "در حال بارگذاری" }).length).toBeGreaterThan(0);
  loadingView.unmount();

  mockShoppingLoading = false;
  mockShoppingError = true;
  renderPlan();
  await settlePdf();
  fireEvent.press(screen.getAllByRole("button", { name: "لیست خرید دقیق" }).at(-1)!);
  expect(screen.getByText("لیست خرید برنامه دریافت نشد.")).toBeTruthy();
  fireEvent.press(screen.getByRole("button", { name: "تلاش دوباره" }));
  expect(mockShoppingRefetch).toHaveBeenCalled();
});
