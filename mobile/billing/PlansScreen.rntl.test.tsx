import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { ApiError } from "@fitician/core";

jest.mock("expo-router", () => ({ useRouter: jest.fn() }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("@expo/vector-icons", () => ({ MaterialCommunityIcons: () => null }));
jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../entitlements/EntitlementProvider", () => ({ useMobileEntitlements: jest.fn() }));
jest.mock("./billingApi", () => ({ createBillingApi: jest.fn() }));
jest.mock("./purchaseService", () => ({ createPurchaseService: jest.fn() }));

import { useRouter } from "expo-router";

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { useMobileEntitlements } from "../entitlements/EntitlementProvider";
import { createBillingApi } from "./billingApi";
import { createPurchaseService } from "./purchaseService";
import { PlansScreen } from "./PlansScreen";

const mockPush = jest.fn();
const mockUseRouter = jest.mocked(useRouter);
const mockUseAuth = jest.mocked(useMobileAuth);
const mockUseEntitlements = jest.mocked(useMobileEntitlements);
const mockCreateBillingApi = jest.mocked(createBillingApi);
const mockCreatePurchaseService = jest.mocked(createPurchaseService);
const mockGetOffers = jest.fn();
const mockCreateOrder = jest.fn();
const mockCreateCheckout = jest.fn();
const mockCompleteCheckout = jest.fn();
const mockRefresh = jest.fn();

const offer = (overrides: Record<string, unknown> = {}) => ({
    currency: "IRR",
    duration_weeks: 4,
    entitlements: ["training.plan.generate"],
    is_available: true,
    offer_code: "training_4w",
    package_code: "training",
    price_irr: 125000,
    quota_policies: [{ entitlement: "body_analysis.run", limit: 1, window_days: 7 }],
    ...overrides,
});

const packageCodes = ["training", "training_coach", "nutrition", "nutrition_physician", "complete", "complete_care"] as const;
const offers = packageCodes.flatMap((packageCode) => [4, 6, 8].map((duration) => offer({
  duration_weeks: duration,
  offer_code: `${packageCode}_${duration}w`,
  package_code: packageCode,
  price_irr: duration * 100_000,
})));

beforeEach(() => {
  mockPush.mockClear();
  mockRefresh.mockClear();
  mockGetOffers.mockReset();
  mockCreateOrder.mockReset();
  mockCreateCheckout.mockReset();
  mockCompleteCheckout.mockReset();
  mockUseRouter.mockReturnValue({ push: mockPush } as never);
  mockUseAuth.mockReturnValue({ request: jest.fn(), status: "signed_in", user: { id: "member-1" } } as never);
  mockUseEntitlements.mockReturnValue({
    error: null,
    hasEntitlement: () => true,
    loading: false,
    quotaFor: () => null,
    refresh: mockRefresh,
    retry: jest.fn(),
    snapshot: { active_packages: ["launch_trial"], entitlements: { granted: [], quotas: [] }, grants: [], primary_package: "launch_trial", trial: { active: true, ends_at: "2026-09-30T12:00:00Z" } },
  } as never);
  mockGetOffers.mockResolvedValue(offers as never);
  mockCreateOrder.mockResolvedValue({ id: "order-1", provider: "fake" } as never);
  mockCreateCheckout.mockResolvedValue({
    checkout_kind: "redirect",
    checkout_url: "/billing/checkout-result",
    order_id: "order-1",
    provider: "fake",
    provider_product_id: null,
    provider_reference: "fake-payment:transaction-1",
    transaction_id: "transaction-1",
  } as never);
  mockCompleteCheckout.mockResolvedValue({ verified: true } as never);
  mockCreateBillingApi.mockReturnValue({
    createCheckout: mockCreateCheckout,
    createOrder: mockCreateOrder,
    getOffer: jest.fn(),
    getOffers: mockGetOffers,
    getOrder: jest.fn(),
    getOrders: jest.fn(),
    verifyPayment: jest.fn(),
  } as never);
  mockCreatePurchaseService.mockReturnValue({ completeCheckout: mockCompleteCheckout } as never);
});

function renderPlans() {
  return render(
    <SafeAreaProvider
      initialMetrics={{
        frame: { height: 800, width: 400, x: 0, y: 0 },
        insets: { bottom: 0, left: 0, right: 0, top: 0 },
      }}
    >
      <PlansScreen />
    </SafeAreaProvider>,
  );
}

test("groups package cards by category and keeps three durations inside each card", async () => {
  renderPlans();

  expect(await screen.findByTestId("billing-package-training")).toBeTruthy();
  expect(screen.getByTestId("billing-package-training_coach")).toBeTruthy();
  expect(screen.getAllByText("۴ هفته")).toHaveLength(2);
  expect(screen.getAllByText("۶ هفته")).toHaveLength(2);
  expect(screen.getAllByText("۸ هفته")).toHaveLength(2);

  fireEvent.press(screen.getByRole("button", { name: "تغذیه" }));
  expect(screen.getByTestId("billing-package-nutrition")).toBeTruthy();
  expect(screen.getByTestId("billing-package-nutrition_physician")).toBeTruthy();

  fireEvent.press(screen.getByRole("button", { name: "کامل" }));
  expect(screen.getByTestId("billing-package-complete")).toBeTruthy();
  expect(screen.getByTestId("billing-package-complete_care")).toBeTruthy();
  expect(screen.getByText("کامل‌ترین بسته")).toBeTruthy();
});

test("changes selected duration price and quota before checkout", async () => {
  renderPlans();

  await screen.findByTestId("billing-package-training");
  expect(screen.getAllByText("۴۰۰٬۰۰۰ IRR").length).toBeGreaterThan(0);
  expect(screen.getAllByText("تا ۴ Body Analysis در طول دوره — هفته‌ای ۱ بار").length).toBeGreaterThan(0);
  fireEvent.press(screen.getByRole("button", { name: "مدت ۶ هفته برای تمرین هوشمند" }));
  expect(screen.getAllByText("۶۰۰٬۰۰۰ IRR").length).toBeGreaterThan(0);
  expect(screen.getAllByText("تا ۶ Body Analysis در طول دوره — هفته‌ای ۱ بار").length).toBeGreaterThan(0);
  expect(screen.getByText("دوره آزمایشی")).toBeTruthy();
  expect(screen.getByText(/پایان دوره آزمایشی/)).toBeTruthy();

  fireEvent.press(screen.getByRole("button", { name: "خرید تمرین هوشمند، ۶ هفته" }));

  await waitFor(() => expect(mockCreateOrder).toHaveBeenCalledWith(expect.objectContaining({
    offer_code: "training_6w",
    provider: "fake",
  })));
  expect(mockCreateOrder.mock.calls[0]?.[0]).not.toHaveProperty("amount_irr");
  expect(mockCreateCheckout).toHaveBeenCalledWith("order-1", { provider: "fake" });
  await waitFor(() => expect(mockRefresh).toHaveBeenCalled());
});

test("disables an unavailable selected offer and expands features inline", async () => {
  mockGetOffers.mockResolvedValue([
    offer(),
    offer({ duration_weeks: 6, is_available: false, offer_code: "training_6w", price_irr: 180000 }),
    offer({ duration_weeks: 8, offer_code: "training_8w", price_irr: 240000 }),
  ] as never);
  renderPlans();

  await screen.findByTestId("billing-package-training");
  expect(screen.queryByText("ویدئوی اجرای حرکات، نکات مهم و حرکات جایگزین")).toBeNull();
  fireEvent.press(screen.getByRole("button", { name: "مشاهده همه امکانات تمرین هوشمند" }));
  expect(screen.getByText("ویدئوی اجرای حرکات، نکات مهم و حرکات جایگزین")).toBeTruthy();
  fireEvent.press(screen.getByRole("button", { name: "مدت ۶ هفته برای تمرین هوشمند" }));
  expect(screen.getByRole("button", { name: "خرید تمرین هوشمند، ۶ هفته" })).toBeDisabled();
  expect(screen.getByText("این پیشنهاد در دسترس نیست")).toBeTruthy();
});

test("defaults to the current package category and marks its card active", async () => {
  mockUseEntitlements.mockReturnValue({
    error: null,
    hasEntitlement: () => true,
    loading: false,
    quotaFor: () => null,
    refresh: mockRefresh,
    retry: jest.fn(),
    snapshot: { active_packages: ["complete_care"], entitlements: { granted: [], quotas: [] }, grants: [], primary_package: "complete_care", trial: { active: false, ends_at: null } },
  } as never);

  renderPlans();

  expect(await screen.findByTestId("billing-package-complete_care")).toBeTruthy();
  expect(screen.getAllByText("کامل حرفه‌ای").length).toBeGreaterThan(0);
  expect(screen.getAllByText("فعال").length).toBeGreaterThan(0);
  expect(screen.queryByTestId("billing-package-training")).toBeNull();
});

test("shows the shared member billing error instead of a generic load message", async () => {
  mockGetOffers.mockImplementationOnce(() => Promise.reject(new ApiError(
    503,
    "provider secret",
    null,
    "BILLING_PROVIDER_UNAVAILABLE",
    { requestId: "billing-member-1" },
  )));

  renderPlans();

  expect(await screen.findByText("درگاه پرداخت فعلاً در دسترس نیست. بعداً دوباره تلاش کنید.")).toBeTruthy();
  expect(screen.queryByText("provider secret")).toBeNull();
  expect(screen.queryByText("billing-member-1")).toBeNull();
});
