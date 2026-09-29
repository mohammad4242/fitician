import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { NutritionProgressReview } from "./NutritionProgressReview";
import { request } from "../../shared/apiClient";
const identity = vi.hoisted(() => ({ id: "member" }));
vi.mock("../auth/AuthContext", () => ({ useAuthIdentity: () => identity.id }));
beforeEach(() => { identity.id = "member"; });
vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
it("requires explicit confirmation and keeps the new-plan step visible", async () => {
  const posts: unknown[] = [];
  vi.mocked(request).mockImplementation(async (_path, input) => {
    if (input?.method === "POST") { posts.push(JSON.parse(String(input.body))); return { estimate_id: "estimate", targets_updated: true, needs_new_plan: true } as never; }
    return { status: "adjustment_available", can_confirm: true, plan_id: "plan", signature: "a".repeat(64), start: "2026-09-01", end: "2026-09-28", checked_in_days: 28, logged_days: 28, reliable_logged_days: 28, weighing_days: 4, average_logged_kcal: 2000, adherence_percent: 100, observed_kg_per_week: 0, target_kg_per_week: -.3, current_calories: 2000, proposed_calories: 1890, reason_codes: [] } as never;
  });
  render(<MemoryRouter><NutritionProgressReview /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "بازبینی روند تغذیه" }));
  const confirm = await screen.findByRole("button", { name: "تأیید اصلاح هدف" });
  expect(confirm).toBeDisabled();
  expect(posts).toHaveLength(0);
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(confirm);
  await waitFor(() => expect(posts).toHaveLength(1));
  expect(posts[0]).toMatchObject({ expected_plan_id: "plan", signature: "a".repeat(64), confirmed: true });
  expect(await screen.findByRole("link", { name: "دریافت برنامه با هدف جدید" })).toHaveAttribute("href", "/nutrition-estimate");
  expect(screen.getByText(/وعده‌های برنامهٔ فعلی تغییر نکرده‌اند/)).toBeInTheDocument();
});

it("does not offer target changes for insufficient data", async () => {
  vi.mocked(request).mockResolvedValue({ status: "insufficient_data", can_confirm: false, start: "2026-09-01", end: "2026-09-28", checked_in_days: 0, logged_days: 0, reliable_logged_days: 0, weighing_days: 0, average_logged_kcal: null, observed_kg_per_week: null, reason_codes: [] });
  render(<MemoryRouter><NutritionProgressReview /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "بازبینی روند تغذیه" }));
  await screen.findByText(/برای تصمیم‌گیری داده کافی نداریم/);
  expect(screen.queryByRole("checkbox")).toBeNull();
  expect(screen.queryByRole("button", { name: "تأیید اصلاح هدف" })).toBeNull();
});


it("ignores a delayed review after the signed-in account changes", async () => {
  let resolve: (value: unknown) => void = () => undefined;
  vi.mocked(request).mockReturnValue(new Promise(value => { resolve = value; }));
  const view = render(<MemoryRouter><NutritionProgressReview /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "بازبینی روند تغذیه" }));
  identity.id = "other-member";
  view.rerender(<MemoryRouter><NutritionProgressReview /></MemoryRouter>);
  await act(async () => resolve({ status: "adjustment_available", can_confirm: true, plan_id: "other-plan", signature: "a".repeat(64), start: "2026-09-01", end: "2026-09-28", proposed_calories: 1900, reason_codes: [] }));
  expect(screen.queryByRole("checkbox")).toBeNull();
  expect(screen.queryByText(/پیشنهاد جدید/)).toBeNull();
});
