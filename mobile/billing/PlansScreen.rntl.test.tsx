import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { SafeAreaProvider } from "react-native-safe-area-context";

jest.mock("expo-router", () => ({ useRouter: jest.fn() }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
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

const offers = [
  {
    currency: "IRR",
    duration_weeks: 4,
    entitlements: ["training.plan.generate"],
    is_available: true,
    offer_code: "training_4w",
    package_code: "training",
    price_irr: 125000,
    quota_policies: [],
  },
  {
    currency: "IRR",
    duration_weeks: 6,
    entitlements: ["training.plan.generate"],
    is_available: false,
    offer_code: "training_6w",
    package_code: "training",
    price_irr: 180000,
    quota_policies: [],
  },
  {
    currency: "IRR",
    duration_weeks: 8,
    entitlements: ["training.plan.generate"],
    is_available: true,
    offer_code: "training_8w",
    package_code: "training",
    price_irr: 240000,
    quota_policies: [],
  },
] as const;

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
    snapshot: { active_packages: ["launch_trial"], entitlements: { granted: [], quotas: [] }, primary_package: "launch_trial", trial: { active: true, ends_at: "2026-09-30T12:00:00Z" } },
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

test("loads API prices, shows 4/6/8 durations, and starts verified fake checkout", async () => {
  renderPlans();

  expect((await screen.findAllByText("تمرین هوشمند")).length).toBe(3);
  expect(screen.getByText("۱۲۵٬۰۰۰ IRR")).toBeTruthy();
  expect(screen.getByText("۲۴۰٬۰۰۰ IRR")).toBeTruthy();
  expect(screen.getByText("۴ هفته")).toBeTruthy();
  expect(screen.getByText("۶ هفته")).toBeTruthy();
  expect(screen.getByText("۸ هفته")).toBeTruthy();
  expect(screen.getByText(/دوره آزمایشی فعال/)).toBeTruthy();

  fireEvent.press(screen.getByRole("button", { name: "خرید ۴ هفته" }));

  await waitFor(() => expect(mockCreateOrder).toHaveBeenCalledWith(expect.objectContaining({
    offer_code: "training_4w",
    provider: "fake",
  })));
  expect(mockCreateOrder.mock.calls[0]?.[0]).not.toHaveProperty("amount_irr");
  expect(mockCreateCheckout).toHaveBeenCalledWith("order-1", { provider: "fake" });
  await waitFor(() => expect(mockRefresh).toHaveBeenCalled());
});
