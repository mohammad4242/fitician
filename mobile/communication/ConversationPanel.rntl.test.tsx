import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { AppState } from "react-native";
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
  await waitFor(() => expect(screen.getByLabelText("متن پیام").props.value).toBe(""));
});
test("shows a recoverable error for malformed responses", async () => {
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request: jest.fn(async () => ({})) } as never);
  render(<ConversationPanel initiallyOpen kind="nutrition" reviewId="review" />);
  await screen.findByText(/دریافت گفت‌وگو ناموفق/);
  expect(screen.queryByLabelText("متن پیام")).toBeNull();
});


test("recovers messages missed between disjoint latest pages", async () => {
  jest.useFakeTimers();
  const state = Object.getOwnPropertyDescriptor(AppState, "currentState");
  Object.defineProperty(AppState, "currentState", { configurable: true, value: "active" });
  const messages = (start: number, end: number) => Array.from({ length: end - start + 1 }, (_, index) => ({
    id: String(start + index), body: `message-${start + index}`, sender_id: "other",
    created_at: new Date(Date.UTC(2026, 8, 30, 0, 0, start + index)).toISOString(),
  }));
  const base = { available: true, review_id: "review", viewer_id: "member", unread_count: 0 };
  const request = jest.fn<(input: { path: string }) => Promise<unknown>>()
    .mockResolvedValueOnce({ ...base, messages: messages(1, 50), older_cursor: null })
    .mockResolvedValueOnce({ ...base, messages: messages(101, 150), older_cursor: "101" })
    .mockResolvedValue({ ...base, messages: messages(51, 100), older_cursor: "51" });
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request } as never);
  try {
    render(<ConversationPanel initiallyOpen kind="workout" reviewId="review" />);
    await act(async () => { await Promise.resolve(); });
    await act(async () => { jest.advanceTimersByTime(10_000); });
    fireEvent.press(screen.getByText("پیام‌های قبلی"));
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("message-51")).toBeTruthy();
    expect(screen.getByText("message-150")).toBeTruthy();
  } finally {
    if (state) Object.defineProperty(AppState, "currentState", state);
    jest.useRealTimers();
  }
});


test.each(["workout", "nutrition"] as const)("collapses %s and removes unavailable composer controls", async kind => {
  const request = jest.fn(async () => ({ available: false, review_id: null, viewer_id: "member", messages: [], unread_count: 0 }));
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ConversationPanel kind={kind} planId="active" />);
  const header = screen.getByRole("button", { name: "گفت‌وگو درباره برنامه" });
  expect(header.props.accessibilityState.expanded).toBe(false);
  fireEvent.press(header);
  expect(screen.getByRole("button", { name: "گفت‌وگو درباره برنامه" }).props.accessibilityState.expanded).toBe(true);
  await screen.findByText(kind === "workout"
    ? "ارسال پیام پس از تخصیص مربی برای برنامه‌ی شما فعال می‌شود."
    : "ارسال پیام پس از تخصیص متخصص این برنامه فعال می‌شود.");
  expect(screen.queryByLabelText("متن پیام")).toBeNull();
  expect(screen.queryByRole("button", { name: "ارسال" })).toBeNull();
});


test("keeps unread messages until opened and renders long multiline messages", async () => {
  const body = "First line\n" + "long ".repeat(100);
  const request = jest.fn(async (input: { method?: string }) => input.method === "PUT" ? undefined : ({
    available: true, review_id: "review", viewer_id: "member", unread_count: 2,
    messages: [{ id: "unread", body, sender_id: "other", created_at: "2026-10-01T10:00:00Z" }],
  }));
  jest.mocked(useMobileAuth).mockReturnValue({ user: { id: "member" }, request } as never);
  render(<ConversationPanel kind="workout" planId="active" />);
  await waitFor(() => expect(screen.getByRole("button", { name: "گفت‌وگو درباره برنامه" }).props.accessibilityHint).toBe("2 پیام خوانده‌نشده"));
  expect(request.mock.calls.some(([input]) => input.method === "PUT")).toBe(false);
  fireEvent.press(screen.getByRole("button", { name: "گفت‌وگو درباره برنامه" }));
  await screen.findByText(body);
  await waitFor(() => expect(screen.getByRole("button", { name: "گفت‌وگو درباره برنامه" }).props.accessibilityHint).toBeUndefined());
});
