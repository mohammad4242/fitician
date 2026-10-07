import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import "../../i18n";

const api = vi.hoisted(() => ({ getAccessOverview: vi.fn() }));
vi.mock("./adminAccessApi", () => api);
import { AdminAccessOverviewPage } from "./AdminAccessOverviewPage";

const overview = {
  timezone: "Asia/Tehran", generated_at: "2026-10-07T10:00:00Z", today_start: "2026-10-06T20:30:00Z", week_start: "2026-10-03T20:30:00Z", month_start: "2026-09-22T20:30:00Z",
  total_users: 41, registrations_today: 2, registrations_week: 7, registrations_month: 19, active_users_24h: 8, active_users_7d: 16, active_users_30d: 30, active_paid_users: 9,
  purchases_today: 1, purchases_week: 4, purchases_month: 10, workout_plans: 24, nutrition_plans: 20, body_analyses_completed: 5,
  daily_signups: [{ date: "2026-10-06", count: 2 }, { date: "2026-10-07", count: 1 }],
  recent_users: [{ user_id: "member-1", display_name: "علی رضایی", email: "ali@example.com", phone_number: null, created_at: "2026-10-07T08:00:00Z", primary_package: "complete", active_packages: ["complete"], trial_active: false, trial_ends_at: null, paid_access_end: null, last_activity_at: null, usage_status: "no_recorded_activity" }],
};

beforeEach(() => { api.getAccessOverview.mockReset(); api.getAccessOverview.mockResolvedValue(overview); });

it("shows metric totals, daily signup chart, and recent users", async () => {
  render(<MemoryRouter><AdminAccessOverviewPage /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "نمای کلی دسترسی" })).toBeInTheDocument();
  expect(screen.getByText("۴۱")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "ثبت‌نام روزانه در ۳۰ روز گذشته" })).toBeInTheDocument();
  expect(screen.getByText("علی رضایی")).toBeInTheDocument();
});

it("shows a loading state and an error state", async () => {
  let rejectRequest!: (reason: Error) => void;
  api.getAccessOverview.mockReturnValue(new Promise((_resolve, reject) => { rejectRequest = reject; }));
  render(<MemoryRouter><AdminAccessOverviewPage /></MemoryRouter>);
  expect(screen.getByRole("status")).toHaveTextContent("در حال دریافت اطلاعات دسترسی");
  rejectRequest(new Error("offline"));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
});
