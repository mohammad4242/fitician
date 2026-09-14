import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../../i18n";
import { ApiError } from "../../shared/apiClient";

const adminApi = vi.hoisted(() => ({ getAdminBillingOrder: vi.fn() }));
vi.mock("./adminApi", () => adminApi);

import { AdminBillingOrderDetailPage } from "./AdminBillingOrderDetailPage";

const order = {
  id: "order-1",
  user_id: "member-1",
  offer_code: "complete_care_8w" as const,
  package_code_snapshot: "complete_care" as const,
  duration_weeks_snapshot: 8 as const,
  amount_irr_snapshot: 1_200_000,
  currency_snapshot: "IRR",
  provider: "fake" as const,
  status: "paid" as const,
  created_at: "2026-09-13T08:00:00Z",
  updated_at: "2026-09-13T08:00:00Z",
  expires_at: null,
  paid_at: "2026-09-13T08:01:00Z",
  refunded_at: null,
  access_grant_id: "grant-1",
  transactions: [{
    id: "transaction-1",
    order_id: "order-1",
    provider: "fake" as const,
    provider_reference: "provider-ref-1",
    amount_irr: 1_200_000,
    currency: "IRR",
    status: "verified" as const,
    created_at: "2026-09-13T08:00:30Z",
    verified_at: "2026-09-13T08:01:00Z",
    failed_at: null,
    refunded_at: null,
  }],
};

beforeEach(() => {
  adminApi.getAdminBillingOrder.mockReset();
  adminApi.getAdminBillingOrder.mockResolvedValue(order);
});

it("shows the immutable order snapshot and safe transaction history", async () => {
  render(
    <MemoryRouter initialEntries={["/admin/billing/orders/order-1"]}>
      <Routes><Route path="/admin/billing/orders/:orderId" element={<AdminBillingOrderDetailPage />} /></Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "order-1" })).toBeInTheDocument();
  expect(screen.getByText("complete_care_8w")).toBeInTheDocument();
  expect(screen.getByText("provider-ref-1")).toBeInTheDocument();
  expect(screen.getByText("verified")).toBeInTheDocument();
  expect(screen.getByText("grant-1")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "مشاهده دسترسی کاربر" })).toHaveAttribute(
    "href",
    "/admin/billing/users/member-1",
  );
  expect(screen.queryByRole("button", { name: /Refund|بازپرداخت/ })).not.toBeInTheDocument();
  expect(within(screen.getByRole("region", { name: "تراکنش‌ها" })).getByText("provider-ref-1")).toBeInTheDocument();
});

it("shows safe admin diagnostics for a failed order lookup", async () => {
  adminApi.getAdminBillingOrder.mockRejectedValueOnce(new ApiError(
    404,
    "private payment details",
    null,
    "BILLING_ORDER_NOT_FOUND",
    { requestId: "admin-billing-request-1" },
  ));

  render(
    <MemoryRouter initialEntries={["/admin/billing/orders/order-missing"]}>
      <Routes><Route path="/admin/billing/orders/:orderId" element={<AdminBillingOrderDetailPage />} /></Routes>
    </MemoryRouter>,
  );

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("BILLING_ORDER_NOT_FOUND");
  expect(alert).toHaveTextContent("404");
  expect(alert).toHaveTextContent("admin-billing-request-1");
  expect(alert).not.toHaveTextContent("private payment details");
});
