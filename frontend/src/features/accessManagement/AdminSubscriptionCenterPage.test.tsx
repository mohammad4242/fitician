import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { expect, it } from "vitest";

import "../../i18n";

import { AdminSubscriptionCenterPage } from "./AdminSubscriptionCenterPage";

it("renders the central workspace and keeps the five sections in URL tabs", () => {
  render(
    <MemoryRouter initialEntries={["/admin/billing/offers"]}>
      <Routes>
        <Route path="/admin/billing" element={<AdminSubscriptionCenterPage />}>
          <Route path="offers" element={<p>Offers pane</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: "اشتراک و دسترسی‌ها" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "پلن‌ها و قیمت‌ها" })).toHaveAttribute(
    "href",
    "/admin/billing/offers",
  );
  expect(screen.getByRole("link", { name: "کمپین‌ها و Trialها" })).toHaveAttribute(
    "href",
    "/admin/billing/campaigns",
  );
  expect(screen.getByRole("link", { name: "کاربران و دسترسی‌ها" })).toHaveAttribute(
    "href",
    "/admin/billing/users",
  );
  expect(screen.getByRole("link", { name: "سفارش‌ها و پرداخت‌ها" })).toHaveAttribute(
    "href",
    "/admin/billing/orders",
  );
  expect(screen.getByRole("link", { name: "تاریخچه تغییرات" })).toHaveAttribute(
    "href",
    "/admin/billing/audit",
  );
  expect(screen.getByText("Offers pane")).toBeInTheDocument();
});
