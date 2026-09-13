import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../../i18n";

const accessApi = vi.hoisted(() => ({ getAdminAuditEvents: vi.fn() }));
vi.mock("./adminAccessApi", () => accessApi);

import { AdminAccessAuditPage } from "./AdminAccessAuditPage";

const event = {
  id: "event-1",
  action: "access.grant.created",
  actor: {
    user_id: "admin-1",
    display_name: "مدیر فیتشو",
    email: "admin@example.com",
    phone_number: null,
  },
  target: {
    user_id: "member-1",
    display_name: "علی رضایی",
    email: "ali@example.com",
    phone_number: null,
  },
  resource_type: "access_grant",
  resource_key: "grant-1",
  reason: "customer support compensation",
  before_state: null,
  after_state: { package_code: "training_coach", source: "admin" },
  created_at: "2026-09-13T08:00:00Z",
};

beforeEach(() => {
  accessApi.getAdminAuditEvents.mockReset();
  accessApi.getAdminAuditEvents.mockResolvedValue([event]);
});

it("shows concise audit entries and expandable business state", async () => {
  render(<MemoryRouter><AdminAccessAuditPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "تاریخچه تغییرات" })).toBeInTheDocument();
  const row = screen.getByTestId("admin-audit-event-event-1");
  expect(within(row).getByText("مدیر فیتشو")).toBeInTheDocument();
  expect(within(row).getByText("دسترسی ایجاد کرد")).toBeInTheDocument();
  expect(within(row).getByText("علی رضایی")).toBeInTheDocument();
  expect(within(row).getByText("customer support compensation")).toBeInTheDocument();
  expect(within(row).getByText(/training_coach/)).not.toBeVisible();

  await userEvent.setup().click(within(row).getByText("جزئیات"));
  expect(within(row).getByText(/training_coach/)).toBeInTheDocument();
});

it("passes audit filters to the read-only API", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminAccessAuditPage /></MemoryRouter>);

  await screen.findByTestId("admin-audit-event-event-1");
  await user.selectOptions(screen.getByLabelText("عملیات"), "access.grant.created");
  await user.type(screen.getByLabelText("کاربر هدف"), "member-1");
  await user.click(screen.getByRole("button", { name: "اعمال فیلتر" }));

  expect(accessApi.getAdminAuditEvents).toHaveBeenLastCalledWith({
    action: "access.grant.created",
    target_user_id: "member-1",
  });
});
