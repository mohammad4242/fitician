import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";
jest.mock("../ui/rtl", () => ({ ...(jest.requireActual("../ui/rtl") as Record<string, unknown>), languageForDirection: () => "fa" }));
jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("@expo/vector-icons", () => ({ MaterialCommunityIcons: () => null }));
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { ConversationPanel } from "./ConversationPanel";
test("retains retry identity and gracefully rejects an invalid response", async () => {
  let sends = 0;
  const bodies: unknown[] = [];
  const request = jest.fn(async (input: { method?: string; body?: unknown }) => {
    if (input.method === "POST") {
      bodies.push(input.body);
      if (++sends === 1) throw new Error("offline");
      return { id: "sent" };
    }
    return { available: true, review_id: "review", viewer_id: "member", messages: [], unread_count: 0 };
  });
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ConversationPanel initiallyOpen kind="workout" reviewId="review" />);
  await waitFor(() => expect(screen.getByLabelText("متن پیام").props.editable).toBe(true));
  fireEvent.changeText(screen.getByLabelText("متن پیام"), "Question");
  fireEvent.press(screen.getByText("ارسال"));
  await screen.findByText(/ارسال ناموفق/);
  fireEvent.press(screen.getByText("ارسال"));
  await waitFor(() => expect(bodies).toHaveLength(2));
  expect(bodies[0]).toEqual(bodies[1]);
});
test("shows a recoverable error for malformed responses", async () => {
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request: jest.fn(async () => ({})) } as never);
  render(<ConversationPanel initiallyOpen kind="nutrition" reviewId="review" />);
  await screen.findByText(/دریافت گفت‌وگو ناموفق/);
  expect(screen.getByLabelText("متن پیام").props.editable).toBe(false);
});
