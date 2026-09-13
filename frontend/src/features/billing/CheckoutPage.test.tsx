import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../../i18n";

const billingApi = vi.hoisted(() => ({
  createCheckout: vi.fn(),
  createOrder: vi.fn(),
  getOffers: vi.fn(),
}));

vi.mock("./api", () => billingApi);

import { CheckoutPage } from "./CheckoutPage";

beforeEach(() => {
  Object.values(billingApi).forEach((mock) => mock.mockReset());
  billingApi.getOffers.mockResolvedValue([{
    offer_code: "training_4w",
    package_code: "training",
    duration_weeks: 4,
    price_irr: 125000,
    currency: "IRR",
    is_available: true,
    entitlements: ["training.plan.generate"],
    quota_policies: [],
  }]);
  billingApi.createOrder.mockResolvedValue({
    id: "order-1",
    offer_code: "training_4w",
    package_code_snapshot: "training",
    duration_weeks_snapshot: 4,
    amount_irr_snapshot: 125000,
    currency_snapshot: "IRR",
    provider: "fake",
    status: "created",
    created_at: "2026-09-13T10:00:00Z",
    updated_at: "2026-09-13T10:00:00Z",
    expires_at: "2026-09-13T10:30:00Z",
    paid_at: null,
    refunded_at: null,
  });
  billingApi.createCheckout.mockResolvedValue({
    order_id: "order-1",
    transaction_id: "transaction-1",
    provider: "fake",
    checkout_kind: "redirect",
    checkout_url: "/billing/result?order_id=order-1&transaction_id=transaction-1&provider_reference=fake-payment%3Atransaction-1",
    provider_product_id: null,
    provider_reference: "fake-payment:transaction-1",
  });
});

it("creates an order from the selected offer and starts provider checkout", async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/billing/checkout/training_4w"]}>
      <Routes>
        <Route path="/billing/checkout/:offerCode" element={<CheckoutPage />} />
        <Route path="/billing/result" element={<span>checkout-placeholder</span>} />
      </Routes>
    </MemoryRouter>,
  );

  await user.click(await screen.findByRole("button", { name: "ادامه به پرداخت" }));

  expect(billingApi.createOrder).toHaveBeenCalledWith({
    offer_code: "training_4w",
    provider: "fake",
    client_idempotency_key: expect.any(String),
  });
  expect(billingApi.createOrder.mock.calls[0][0]).not.toHaveProperty("amount_irr");
  expect(billingApi.createCheckout).toHaveBeenCalledWith("order-1", { provider: "fake" });
  await waitFor(() => expect(screen.getByText("checkout-placeholder")).toBeInTheDocument());
});
