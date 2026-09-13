import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../../i18n";

const accessApi = vi.hoisted(() => ({ searchAccessUsers: vi.fn() }));
vi.mock("./adminAccessApi", () => accessApi);

import { AdminUserAccessPage } from "./AdminUserAccessPage";

const member = {
  user_id: "member-1",
  display_name: "علی رضایی",
  email: "ali@example.com",
  phone_number: "+989123456789",
  created_at: "2026-09-13T08:00:00Z",
  primary_package: "complete" as const,
  active_packages: ["complete"] as const,
  trial_active: false,
  trial_ends_at: null,
  paid_access_end: "2026-11-13T08:00:00Z",
};

beforeEach(() => {
  accessApi.searchAccessUsers.mockReset();
  accessApi.searchAccessUsers.mockResolvedValue([member]);
});

it("searches members and links to an access detail route", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminUserAccessPage /></MemoryRouter>);

  const result = await screen.findByTestId("access-user-member-1");
  expect(within(result).getByText("علی رضایی")).toBeInTheDocument();
  expect(within(result).getByText("کامل هوشمند")).toBeInTheDocument();
  expect(within(result).getByRole("link", { name: "مشاهده دسترسی" })).toHaveAttribute(
    "href",
    "/admin/billing/users/member-1",
  );

  const search = screen.getByRole("searchbox", { name: "جست‌وجوی کاربران" });
  await user.type(search, "علی");
  await user.click(screen.getByRole("button", { name: "جست‌وجو" }));

  expect(accessApi.searchAccessUsers).toHaveBeenLastCalledWith({ q: "علی" });
});
