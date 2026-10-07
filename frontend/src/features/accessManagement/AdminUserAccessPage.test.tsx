import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import i18n from "../../i18n";

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

beforeEach(async () => {
  await i18n.changeLanguage("fa");
  accessApi.searchAccessUsers.mockReset();
  accessApi.searchAccessUsers.mockResolvedValue({ items: [member], total: 1, limit: 25, offset: 0 });
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

  expect(accessApi.searchAccessUsers).toHaveBeenLastCalledWith(expect.objectContaining({ q: "علی", limit: 25, offset: 0, signup_period: "all", sort: "newest" }));
  const searchedResult = await screen.findByTestId("access-user-member-1");
  const paidAccessEnd = within(searchedResult).getByText("پایان دسترسی").parentElement;
  expect(paidAccessEnd).toBeInTheDocument();
  expect(paidAccessEnd).not.toHaveTextContent("—");
});

it("applies signup filters and requests later pages from the backend", async () => {
  await i18n.changeLanguage("en");
  const user = userEvent.setup();
  accessApi.searchAccessUsers.mockResolvedValue({ items: [member], total: 26, limit: 25, offset: 0 });
  render(<MemoryRouter><AdminUserAccessPage /></MemoryRouter>);
  await screen.findByTestId("access-user-member-1");
  await user.selectOptions(screen.getByLabelText("Signup date"), "custom");
  expect(screen.getByLabelText("From date")).toBeInTheDocument();
  expect(screen.getByText("Enter both dates to search a custom range.")).toBeInTheDocument();
  expect(accessApi.searchAccessUsers).toHaveBeenCalledTimes(1);
  await user.type(screen.getByLabelText("From date"), "2026-10-01");
  expect(accessApi.searchAccessUsers).toHaveBeenCalledTimes(1);
  await user.type(screen.getByLabelText("To date"), "2026-10-07");
  expect(accessApi.searchAccessUsers).toHaveBeenLastCalledWith(expect.objectContaining({ signup_period: "custom", from_date: "2026-10-01", to_date: "2026-10-07", limit: 25, offset: 0 }));
  await user.click(screen.getByRole("button", { name: "Next" }));
  expect(accessApi.searchAccessUsers).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 25, limit: 25 }));
});

it("shows loading, empty, and error states", async () => {
  let resolveRequest!: (page: { items: typeof member[]; total: number; limit: number; offset: number }) => void;
  accessApi.searchAccessUsers.mockReturnValueOnce(new Promise((resolve) => { resolveRequest = resolve; }));
  const { rerender } = render(<MemoryRouter><AdminUserAccessPage /></MemoryRouter>);
  expect(screen.getByRole("status")).toHaveTextContent("در حال دریافت اطلاعات دسترسی");
  resolveRequest({ items: [], total: 0, limit: 25, offset: 0 });
  expect(await screen.findByText("کاربری با این مشخصات پیدا نشد.")).toBeInTheDocument();

  accessApi.searchAccessUsers.mockRejectedValueOnce(new Error("offline"));
  rerender(<MemoryRouter key="error-state" initialEntries={["/?q=missing"]}><AdminUserAccessPage /></MemoryRouter>);
  expect(await screen.findByRole("alert")).toBeInTheDocument();
});

it("normalizes invalid URL paging and filter values before requesting users", async () => {
  render(<MemoryRouter initialEntries={["/?offset=Infinity&signup_period=invalid&sort=unknown"]}><AdminUserAccessPage /></MemoryRouter>);
  await screen.findByTestId("access-user-member-1");
  expect(accessApi.searchAccessUsers).toHaveBeenCalledWith(expect.objectContaining({ offset: 0, signup_period: "all", sort: "newest", limit: 25 }));

  render(<MemoryRouter initialEntries={["/?offset=1.5"]}><AdminUserAccessPage /></MemoryRouter>);
  expect(accessApi.searchAccessUsers).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 0 }));
});

it("keeps the custom Persian date picker in Tehran calendar mode", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminUserAccessPage /></MemoryRouter>);
  await screen.findByTestId("access-user-member-1");
  await user.selectOptions(screen.getByLabelText("تاریخ ثبت‌نام"), "custom");
  expect(screen.getByRole("button", { name: "از تاریخ" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "تا تاریخ" })).toBeInTheDocument();
  expect(accessApi.searchAccessUsers).toHaveBeenCalledTimes(1);
});

it("rejects invalid custom dates locally and caps a huge URL offset", async () => {
  render(<MemoryRouter initialEntries={["/?offset=1000000000&signup_period=custom&from_date=2026-10-10&to_date=2026-10-01"]}><AdminUserAccessPage /></MemoryRouter>);
  expect(screen.getByRole("status")).toHaveTextContent("تاریخ شروع باید قبل از تاریخ پایان یا برابر با آن باشد.");
  expect(accessApi.searchAccessUsers).not.toHaveBeenCalled();

  render(<MemoryRouter initialEntries={["/?offset=1000000000"]}><AdminUserAccessPage /></MemoryRouter>);
  await screen.findByTestId("access-user-member-1");
  expect(accessApi.searchAccessUsers).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 1_000_000 }));
});
