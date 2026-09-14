import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../../i18n";
import { ApiError } from "../../shared/apiClient";

const billingApi = vi.hoisted(() => ({
  getOrders: vi.fn(),
}));
vi.mock("./api", () => billingApi);

import { BillingHistoryPage } from "./BillingHistoryPage";

beforeEach(() => {
  billingApi.getOrders.mockReset();
  billingApi.getOrders.mockResolvedValue([{
    id: "order-1",
    offer_code: "training_4w",
    package_code_snapshot: "training",
    duration_weeks_snapshot: 4,
    amount_irr_snapshot: 125000,
    currency_snapshot: "IRR",
    provider: "fake",
    status: "paid",
    created_at: "2026-09-13T10:00:00Z",
    updated_at: "2026-09-13T10:00:00Z",
    expires_at: null,
    paid_at: "2026-09-13T10:05:00Z",
    refunded_at: null,
  }]);
});

it("shows safe order history fields without payment details", async () => {
  render(<MemoryRouter><BillingHistoryPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "تاریخچه خرید" })).toBeInTheDocument();
  expect(screen.getByText(/۱۲۵٬۰۰۰/)).toBeInTheDocument();
  expect(screen.getByText(/۴ هفته/)).toBeInTheDocument();
  expect(screen.getByText("پرداخت موفق بود")).toBeInTheDocument();
  expect(screen.queryByText(/card|بانک|شماره کارت/i)).not.toBeInTheDocument();
});

it("uses the shared billing resolver for a backend failure", async () => {
  billingApi.getOrders.mockRejectedValueOnce(new ApiError(
    503,
    "raw provider secret",
    null,
    "BILLING_PROVIDER_UNAVAILABLE",
    { requestId: "billing-request-1" },
  ));

  render(<MemoryRouter><BillingHistoryPage /></MemoryRouter>);

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("درگاه پرداخت فعلاً در دسترس نیست");
  expect(alert).not.toHaveTextContent("raw provider secret");
  expect(alert).not.toHaveTextContent("billing-request-1");
});
