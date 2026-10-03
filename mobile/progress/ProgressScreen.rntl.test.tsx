jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
}));
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react-native";
import { jest, test, expect } from "@jest/globals";
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
}));
jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../entitlements/EntitlementProvider", () => ({
  useMobileEntitlements: () => ({
    loading: false,
    hasEntitlement: () => true,
    quotaFor: () => null,
  }),
}));
jest.mock("../ui/layout", () => ({
  Screen: ({ children }: { children: React.ReactNode }) => children,
}));
jest.mock("../ui/useMemberFeatureLanguage", () => ({
  useMemberFeatureLanguage: () => require("react").useState("fa"),
}));
jest.mock("../ui/rtl", () => ({
  ...(jest.requireActual("../ui/rtl") as object),
  languageForDirection: () => "fa",
}));
jest.mock("../ui/components/AppIcon", () => ({ AppIcon: () => null }));
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { ProgressScreen } from "./ProgressScreen";
const body = {
  unit: "cm",
  points: [],
  start_value: null,
  latest_value: null,
  delta: null,
};
const data = {
  context: {
    preset: "week",
    timezone: "UTC",
    today: "2026-10-02",
    start_date: "2026-09-26",
    end_date: "2026-10-02",
    training_enabled: false,
    nutrition_enabled: true,
  },
  training: null,
  nutrition: {
    series: [
      {
        date: "2026-10-01",
        target_kcal: 2200,
        actual_kcal: null,
        logging_state: "missing",
        in_progress: false,
      },
    ],
    logged_days: 0,
    elapsed_days: 6,
    adherent_days: 0,
    comparable_days: 0,
    average_difference_kcal: null,
  },
  body_measurements: {
    weight: { ...body, unit: "kg" },
    waist: body,
    hip: body,
    shoulder_width: body,
  },
  body_analysis: {},
  recovery: [],
  insights: [],
};
test("shows nutrition-only progress, true gaps and body selector", async () => {
  const request = jest.fn(async () => data);
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ProgressScreen />);
  await screen.findByText("کالری و پایبندی");
  fireEvent.press(screen.getByRole("button", { name: /کالری و پایبندی/ }));
  expect(
    await screen.findByText("برای این روز مصرفی ثبت نشده است."),
  ).toBeTruthy();
  expect(screen.queryByText("پایبندی به جلسه‌های موعدرسیده")).toBeNull();
  fireEvent.press(screen.getByRole("tab", { name: "بدن" }));
  fireEvent.press(await screen.findByRole("button", { name: "پهنای سرشانه" }));
  expect(
    screen.getByText("با ثبت اندازه، روند تغییراتت اینجا نمایش داده می‌شود."),
  ).toBeTruthy();
});
test("shows a recoverable error", async () => {
  const request = jest
    .fn<() => Promise<never>>()
    .mockRejectedValue(new Error("offline"));
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ProgressScreen />);
  await waitFor(() =>
    expect(
      screen.getByText("دریافت پیشرفت ناموفق بود. دوباره تلاش کن."),
    ).toBeTruthy(),
  );
});
test("offers English presentation with LTR text", async () => {
  const request = jest.fn(async () => data);
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ProgressScreen />);
  await screen.findByText("کالری و پایبندی");
  fireEvent.press(screen.getByRole("button", { name: "English" }));
  expect(screen.getByText("Calories & adherence")).toBeTruthy();
  expect(screen.getByRole("header", { name: "My Progress" })).toHaveStyle({
    writingDirection: "ltr",
  });
});

test("opens Overview and drills into Calories without refetching", async () => {
  const request = jest.fn(async () => data);
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ProgressScreen />);
  expect(
    (await screen.findByRole("tab", { name: "نمای کلی" })).props
      .accessibilityState,
  ).toMatchObject({ selected: true });
  fireEvent.press(screen.getByRole("button", { name: /کالری و پایبندی/ }));
  expect(
    screen.getByRole("tab", { name: "کالری" }).props.accessibilityState,
  ).toMatchObject({ selected: true });
  expect(
    await screen.findByText("برای این روز مصرفی ثبت نشده است."),
  ).toBeTruthy();
  expect(request).toHaveBeenCalledTimes(1);
});

jest.mock("../bodyAnalysis/BodyAnalysisHistoryScreen", () => {
  const { Text } = require("react-native");
  return {
    BodyAnalysisHistoryScreen: () => <Text>analysis-history-mounted</Text>,
  };
});
const training = {
  planned_sessions: 4,
  due_sessions: 4,
  completed_sessions: 3,
  adherence_percent: 75,
  skipped_sessions: 1,
  rescheduled_sessions: 2,
  overdue_sessions: 0,
  weeks: [{ start_date: "2026-09-26", planned: 4, completed: 3 }],
};
test("loads Body Analysis only on selection", async () => {
  const request = jest.fn(async () => data);
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ProgressScreen />);
  await screen.findByText("کالری و پایبندی");
  expect(screen.queryByText("analysis-history-mounted")).toBeNull();
  fireEvent.press(screen.getByRole("tab", { name: "تحلیل بدن" }));
  expect(await screen.findByText("analysis-history-mounted")).toBeTruthy();
  expect(request).toHaveBeenCalledTimes(1);
});
test("renders training-only counts and weekly planned/completed bars", async () => {
  const request = jest.fn(async () => ({
    ...data,
    context: {
      ...data.context,
      training_enabled: true,
      nutrition_enabled: false,
    },
    training,
    nutrition: null,
  }));
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ProgressScreen />);
  fireEvent.press(await screen.findByRole("button", { name: /تمرین.*۳ از ۴/ }));
  expect(screen.getByText("۷۵%")).toBeTruthy();
  expect(screen.getByText("جابه‌جا شده ۲")).toBeTruthy();
  expect(screen.queryByText("کالری و پایبندی")).toBeNull();
});
test.each([0, 1, 2])(
  "shows %s body observations without an invented trend",
  async (count) => {
    const request = jest.fn(async () => ({
      ...data,
      body_measurements: {
        ...data.body_measurements,
        weight: {
          ...body,
          unit: "kg",
          points: Array.from({ length: count }, (_, i) => ({
            recorded_at: `2026-10-0${i + 1}T10:00:00Z`,
            value: 80 - i,
            source: "manual",
          })),
          start_value: count ? 80 : null,
          latest_value: count ? 81 - count : null,
          delta: count > 1 ? -1 : null,
        },
      },
    }));
    jest
      .mocked(useMobileAuth)
      .mockReturnValue({ user: { id: "member" }, request } as never);
    render(<ProgressScreen />);
    await screen.findByText("کالری و پایبندی");
    fireEvent.press(screen.getByRole("tab", { name: "بدن" }));
    expect(screen.queryAllByRole("button", { name: /وزن.*kg/ })).toHaveLength(
      count > 1 ? count : 0,
    );
    expect(screen.queryByText(/→/)).toBeNull();
    if (count === 1)
      expect(
        screen.getByText("برای نمایش روند، حداقل یک ثبت دیگر لازم است."),
      ).toBeTruthy();
    if (count > 1) expect(screen.getByText(/−۱ kg/)).toBeTruthy();
  },
);
test.each([0, 1, 2])(
  "shows %s recovery check-ins with truthful chart availability",
  async (count) => {
    const request = jest.fn(async () => ({
      ...data,
      context: { ...data.context, training_enabled: true },
      training,
      recovery: Array.from({ length: count }, (_, i) => ({
        recorded_at: `2026-10-0${i + 1}T10:00:00Z`,
        recovery: "good",
        difficulty: "appropriate",
        week_number: i + 1,
      })),
    }));
    jest
      .mocked(useMobileAuth)
      .mockReturnValue({ user: { id: "member" }, request } as never);
    render(<ProgressScreen />);
    await screen.findByText("کالری و پایبندی");
    fireEvent.press(screen.getByRole("tab", { name: "ریکاوری" }));
    expect(
      screen.queryAllByRole("button", { name: /ریکاوری.*خوب/ }),
    ).toHaveLength(count > 1 ? count : 0);
  },
);
test("selects calorie dates by tap and preserves missing intake", async () => {
  const request = jest.fn(async () => ({
    ...data,
    nutrition: {
      ...data.nutrition,
      series: [
        { date: "2026-10-01", target_kcal: 2200, actual_kcal: 2140 },
        {
          date: "2026-10-02",
          target_kcal: 2000,
          actual_kcal: null,
          logging_state: "missing",
        },
      ],
    },
  }));
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ProgressScreen />);
  fireEvent.press(
    await screen.findByRole("button", { name: /کالری و پایبندی/ }),
  );
  fireEvent.press(screen.getByTestId("progress-trend-plot"), {
    nativeEvent: { locationX: 48 },
  });
  expect(screen.getByText(/−۶۰ kcal/)).toBeTruthy();
  fireEvent(
    screen.getByRole("button", { name: /کالری هدف ۲٬۰۰۰.*—/ }),
    "accessibilityAction",
    { nativeEvent: { actionName: "activate" } },
  );
  expect(screen.getByText("برای این روز مصرفی ثبت نشده است.")).toBeTruthy();
  expect(screen.queryByText(/−۶۰ kcal/)).toBeNull();
});

test("horizontal navigation viewport follows the selected language", async () => {
  const request = jest.fn(async () => data);
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ProgressScreen />);
  await screen.findByText("کالری و پایبندی");
  expect(screen.getByTestId("progress-category-tabs")).toHaveStyle({ direction: "rtl" });
  expect(screen.getByTestId("progress-period-tabs")).toHaveStyle({ direction: "rtl" });
  fireEvent.press(screen.getByRole("button", { name: "English" }));
  expect(screen.getByTestId("progress-category-tabs")).toHaveStyle({ direction: "ltr" });
  expect(screen.getByTestId("progress-period-tabs")).toHaveStyle({ direction: "ltr" });
  expect(screen.getByRole("tab", { name: "Overview" }).props.accessibilityState.selected).toBe(true);
  expect(request).toHaveBeenCalledTimes(1);
});
