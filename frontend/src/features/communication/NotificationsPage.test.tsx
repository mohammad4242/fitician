import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";
import { NotificationsPage } from "./NotificationsPage";
import { request } from "../../shared/apiClient";
vi.mock("../auth/AuthContext", () => ({ useAuthIdentity: () => "member" }));
vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
it("keeps new reminders off and saves separate chosen times", async () => {
  const preferences = { enabled: true, messages: true, training_reminders: false, nutrition_reminders: false, return_reminders: false, training_time: null, nutrition_time: null, reminder_timezone: "UTC", approved_plans: true, required_reviews: true, body_analysis: true, cycle_reminders: true, physician_decisions: true, nutrition_updates: true, updated_at: "2026-09-29T00:00:00Z" };
  let saved: Record<string, unknown> = {};
  vi.mocked(request).mockImplementation(async (path, input) => {
    if (input?.method === "PUT") { saved = JSON.parse(String(input.body)); return saved as never; }
    return (path.endsWith("inbox") ? { items: [], unread_count: 0, older_cursor: null } : preferences) as never;
  });
  render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
  expect(await screen.findByLabelText("یادآوری روزهای تمرین")).not.toBeChecked();
  expect(screen.getByLabelText("یادآوری روزانه تغذیه")).not.toBeChecked();
  fireEvent.click(screen.getByLabelText("یادآوری روزهای تمرین"));
  fireEvent.change(screen.getByLabelText("ساعت تمرین"), { target: { value: "18:30" } });
  fireEvent.change(screen.getByLabelText("ساعت تغذیه"), { target: { value: "20:15" } });
  fireEvent.click(screen.getByText("ذخیره تنظیمات"));
  await waitFor(() => expect(saved.training_time).toBe("18:30"));
  expect(saved.nutrition_time).toBe("20:15");
  expect(saved.training_reminders).toBe(true);
  expect(saved.nutrition_reminders).toBe(false);
  expect(saved).not.toHaveProperty("updated_at");
});
