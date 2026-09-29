import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";
import { SafeAreaProvider } from "react-native-safe-area-context";
jest.mock("expo-router", () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("@expo/vector-icons", () => ({ MaterialCommunityIcons: () => null }));
jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../notifications/notificationPermission", () => ({ prepareNotifications: jest.fn(), getNativePushToken: jest.fn() }));
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { NotificationsScreen } from "./NotificationsScreen";
test("keeps reminders opt-in and persists distinct times", async () => {
  const preferences = { enabled: true, messages: true, training_reminders: false, nutrition_reminders: false, return_reminders: false, training_time: null, nutrition_time: null, reminder_timezone: "UTC", approved_plans: true, required_reviews: true, body_analysis: true, cycle_reminders: true, physician_decisions: true, nutrition_updates: true };
  let saved: Record<string, unknown> = {};
  const request = jest.fn(async (input: { method?: string; path: string; body?: unknown }) => {
    if (input.method === "PUT") { saved = input.body as Record<string, unknown>; return saved; }
    return input.path.endsWith("inbox") ? { items: [], unread_count: 0 } : preferences;
  });
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request } as never);
  render(<SafeAreaProvider initialMetrics={{ frame: { height: 800, width: 400, x: 0, y: 0 }, insets: { top: 0, bottom: 0, left: 0, right: 0 } }}><NotificationsScreen /></SafeAreaProvider>);
  const training = await screen.findByLabelText("یادآوری روزهای تمرین");
  expect(training.props.value).toBe(false);
  fireEvent(training, "valueChange", true);
  fireEvent.changeText(screen.getByLabelText("ساعت تمرین"), "18:30");
  fireEvent.changeText(screen.getByLabelText("ساعت تغذیه"), "20:15");
  fireEvent.press(screen.getByText("ذخیره تنظیمات"));
  await waitFor(() => expect(saved.training_time).toBe("18:30"));
  expect(saved.nutrition_time).toBe("20:15");
  expect(saved.training_reminders).toBe(true);
  expect(saved.nutrition_reminders).toBe(false);
});
