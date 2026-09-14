import { render, screen } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { ApiError } from "@fitician/core";

jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("./billingApi", () => ({ createBillingApi: jest.fn() }));

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { createBillingApi } from "./billingApi";
import { BillingHistoryScreen } from "./BillingHistoryScreen";

const mockUseAuth = jest.mocked(useMobileAuth);
const mockCreateBillingApi = jest.mocked(createBillingApi);
const mockGetOrders = jest.fn();

beforeEach(() => {
  mockUseAuth.mockReturnValue({ request: jest.fn(), status: "signed_in", user: { id: "member-1" } } as never);
  mockGetOrders.mockReset();
  mockGetOrders.mockResolvedValue([{
    amount_irr_snapshot: 125000,
    created_at: "2026-09-13T10:00:00Z",
    currency_snapshot: "IRR",
    duration_weeks_snapshot: 4,
    expires_at: null,
    id: "order-1",
    offer_code: "training_4w",
    package_code_snapshot: "training",
    paid_at: "2026-09-13T10:05:00Z",
    provider: "fake",
    refunded_at: null,
    status: "paid",
    updated_at: "2026-09-13T10:00:00Z",
  }] as never);
  mockCreateBillingApi.mockReturnValue({
    createCheckout: jest.fn(),
    createOrder: jest.fn(),
    getOffer: jest.fn(),
    getOffers: jest.fn(),
    getOrder: jest.fn(),
    getOrders: mockGetOrders,
    verifyPayment: jest.fn(),
  } as never);
});

test("shows safe purchase history fields", async () => {
  render(
    <SafeAreaProvider
      initialMetrics={{
        frame: { height: 800, width: 400, x: 0, y: 0 },
        insets: { bottom: 0, left: 0, right: 0, top: 0 },
      }}
    >
      <BillingHistoryScreen />
    </SafeAreaProvider>,
  );

  expect(await screen.findByText("تاریخچه خرید")).toBeTruthy();
  expect(screen.getByText("۱۲۵٬۰۰۰ IRR")).toBeTruthy();
  expect(screen.getByText(/۴ هفته/)).toBeTruthy();
  expect(screen.getByText("پرداخت موفق بود")).toBeTruthy();
  expect(screen.queryByText(/شماره کارت|بانک|card/i)).toBeNull();
});

test("resolves a backend history error for the member", async () => {
  mockGetOrders.mockImplementationOnce(() => Promise.reject(new ApiError(
    500,
    "private billing detail",
    null,
    "INTERNAL_SERVER_ERROR",
    { requestId: "billing-history-member-1" },
  )));

  render(
    <SafeAreaProvider
      initialMetrics={{
        frame: { height: 800, width: 400, x: 0, y: 0 },
        insets: { bottom: 0, left: 0, right: 0, top: 0 },
      }}
    >
      <BillingHistoryScreen />
    </SafeAreaProvider>,
  );

  expect(await screen.findByText("انجام این عملیات با خطای غیرمنتظره روبه‌رو شد. دوباره تلاش کنید.")).toBeTruthy();
  expect(screen.queryByText("private billing detail")).toBeNull();
  expect(screen.queryByText("billing-history-member-1")).toBeNull();
});
