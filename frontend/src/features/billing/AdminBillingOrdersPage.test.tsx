import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../../i18n";

const adminApi = vi.hoisted(() => ({ getAdminBillingOrders: vi.fn() }));
vi.mock("./adminApi", () => adminApi);

import { AdminBillingOrdersPage } from "./AdminBillingOrdersPage";

const paidOrder = {
  id: "order-paid",
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
  transactions: [],
};

const pendingOrder = {
  ...paidOrder,
  id: "order-pending",
  status: "pending" as const,
  paid_at: null,
  access_grant_id: null,
};

beforeEach(() => {
  adminApi.getAdminBillingOrders.mockReset();
  adminApi.getAdminBillingOrders.mockResolvedValue([paidOrder, pendingOrder]);
});

it("lists orders and keeps the page read-only", async () => {
  render(<MemoryRouter><AdminBillingOrdersPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "سفارش‌ها و پرداخت‌ها" })).toBeInTheDocument();
  const order = screen.getByTestId("admin-order-order-paid");
  expect(within(order).getByText("complete_care_8w")).toBeInTheDocument();
  expect(within(order).getByText(/مراقبت کامل/)).toBeInTheDocument();
  expect(within(order).getByText("paid")).toBeInTheDocument();
  expect(within(order).getByRole("link", { name: "جزئیات سفارش" })).toHaveAttribute(
    "href",
    "/admin/billing/orders/order-paid",
  );
  expect(screen.queryByRole("button", { name: /Refund|بازپرداخت/ })).not.toBeInTheDocument();
});

it("filters the existing admin order API", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOrdersPage /></MemoryRouter>);

  await screen.findByTestId("admin-order-order-paid");
  await user.selectOptions(screen.getByLabelText("وضعیت"), "paid");
  await user.type(screen.getByLabelText("کاربر"), "member-1");
  await user.click(screen.getByRole("button", { name: "اعمال فیلتر" }));

  expect(adminApi.getAdminBillingOrders).toHaveBeenLastCalledWith({
    status: "paid",
    user_id: "member-1",
  });
});
