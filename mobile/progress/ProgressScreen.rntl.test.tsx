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
  await screen.findByText("کالری و پایبندی تغذیه");
  expect(screen.getByText("برای این روز مصرفی ثبت نشده است.")).toBeTruthy();
  expect(screen.queryByText("پایبندی به جلسه‌های موعدرسیده")).toBeNull();
  fireEvent.press(screen.getByRole("button", { name: "پهنای سرشانه" }));
  expect(
    screen.getByText("هنوز اندازه‌ای برای پهنای سرشانه ثبت نشده است."),
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
  await screen.findByText("کالری و پایبندی تغذیه");
  fireEvent.press(screen.getByRole("button", { name: "English" }));
  expect(screen.getByText("Calories & nutrition adherence")).toBeTruthy();
  expect(screen.getByRole("header", { name: "My Progress" })).toHaveStyle({
    writingDirection: "ltr",
  });
});
