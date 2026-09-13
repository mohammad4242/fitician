import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../../i18n";

const billingApi = vi.hoisted(() => ({
  getOrder: vi.fn(),
  verifyPayment: vi.fn(),
}));
const entitlementState = vi.hoisted(() => ({ refresh: vi.fn(async () => undefined) }));

vi.mock("./api", () => billingApi);
vi.mock("../entitlements/EntitlementContext", () => ({
  useEntitlements: () => ({
    snapshot: null,
    loading: false,
    error: null,
    refresh: entitlementState.refresh,
    retry: vi.fn(),
    hasEntitlement: () => false,
    quotaFor: () => null,
  }),
}));

import { CheckoutResultPage } from "./CheckoutResultPage";

beforeEach(() => {
  billingApi.verifyPayment.mockReset();
  billingApi.getOrder.mockReset();
  billingApi.getOrder.mockResolvedValue({ provider: "fake" });
  entitlementState.refresh.mockClear();
});

it("refreshes entitlements only after verified payment", async () => {
  billingApi.verifyPayment.mockResolvedValue({
    order_id: "order-1",
    transaction_id: "transaction-1",
    transaction_status: "verified",
    order_status: "paid",
    verified: true,
    access_grant_id: "grant-1",
  });

  render(<MemoryRouter initialEntries={["/billing/result?order_id=order-1&transaction_id=transaction-1&provider_reference=ref"]}><CheckoutResultPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "پرداخت موفق بود" })).toBeInTheDocument();
  await waitFor(() => expect(entitlementState.refresh).toHaveBeenCalledOnce());
  expect(billingApi.getOrder).toHaveBeenCalledWith("order-1");
  expect(billingApi.verifyPayment).toHaveBeenCalledWith("fake", {
    transaction_id: "transaction-1",
    provider_reference: "ref",
  });
});

it("does not refresh entitlements after a failed payment", async () => {
  billingApi.verifyPayment.mockResolvedValue({
    order_id: "order-1",
    transaction_id: "transaction-1",
    transaction_status: "failed",
    order_status: "failed",
    verified: false,
    access_grant_id: null,
  });

  render(<MemoryRouter initialEntries={["/billing/result?order_id=order-1&transaction_id=transaction-1"]}><CheckoutResultPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "پرداخت ناموفق بود" })).toBeInTheDocument();
  expect(billingApi.getOrder).toHaveBeenCalledWith("order-1");
  expect(entitlementState.refresh).not.toHaveBeenCalled();
});
