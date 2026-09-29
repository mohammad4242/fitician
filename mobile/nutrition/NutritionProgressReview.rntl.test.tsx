import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";
jest.mock("expo-router", () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock("@expo/vector-icons", () => ({ MaterialCommunityIcons: () => null }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("@tanstack/react-query", () => ({ useQueryClient: () => ({ invalidateQueries: jest.fn() }) }));
jest.mock("../ui/rtl", () => ({ ...(jest.requireActual("../ui/rtl") as Record<string, unknown>), languageForDirection: () => "fa" }));
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { NutritionProgressReview } from "./NutritionProgressReview";
const proposal = { status: "adjustment_available", can_confirm: true, plan_id: "plan", signature: "a".repeat(64), start: "2026-09-01", end: "2026-09-28", checked_in_days: 28, logged_days: 28, reliable_logged_days: 28, weighing_days: 4, adherence_percent: 100, average_logged_kcal: 2000, observed_kg_per_week: 0, target_kg_per_week: -.3, current_calories: 2000, proposed_calories: 1890, reason_codes: [] };
test("requires confirmation and explains that meals still need a new plan", async () => {
  const posts: unknown[] = [];
  const request = jest.fn(async (input: { method?: string; body?: unknown }) => {
    if (input.method === "POST") { posts.push(input.body); return { estimate_id: "estimate", targets_updated: true, needs_new_plan: true }; }
    return proposal;
  });
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request } as never);
  render(<NutritionProgressReview />);
  fireEvent.press(screen.getByText("بازبینی روند تغذیه"));
  const confirm = await screen.findByRole("button", { name: "تأیید اصلاح هدف" });
  expect(confirm).toBeDisabled();
  fireEvent.press(confirm);
  expect(posts).toHaveLength(0);
  fireEvent(screen.getByLabelText("تأیید تغییر هدف"), "valueChange", true);
  fireEvent.press(confirm);
  await waitFor(() => expect(posts).toHaveLength(1));
  expect(posts[0]).toMatchObject({ expected_plan_id: "plan", signature: "a".repeat(64), confirmed: true });
  expect(await screen.findByText(/وعده‌های برنامهٔ فعلی تغییر نکرده‌اند/)).toBeTruthy();
  expect(screen.getByText("دریافت برنامه با هدف جدید")).toBeTruthy();
});
test("does not expose another account's loaded review", async () => {
  const request = jest.fn(async () => proposal);
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request } as never);
  const view = render(<NutritionProgressReview />);
  fireEvent.press(screen.getByText("بازبینی روند تغذیه"));
  await screen.findByLabelText("تأیید تغییر هدف");
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "other-member" }, request } as never);
  view.rerender(<NutritionProgressReview />);
  expect(screen.queryByLabelText("تأیید تغییر هدف")).toBeNull();
});
