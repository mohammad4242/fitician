import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ConversationPanel } from "./ConversationPanel";
import { request } from "../../shared/apiClient";
vi.mock("../auth/AuthContext", () => ({ useAuthIdentity: () => "member" }));
vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
it("retries a failed message with the same request identity", async () => {
  let sends = 0;
  const bodies: string[] = [];
  vi.mocked(request).mockImplementation(async (_path, input) => {
    if (input?.method === "POST") {
      bodies.push(String(input.body));
      if (++sends === 1) throw new Error("offline");
      return { id: "sent" } as never;
    }
    return { available: true, review_id: "review", viewer_id: "member", messages: [], unread_count: 0 } as never;
  });
  render(<ConversationPanel kind="workout" reviewId="review" />);
  fireEvent.click(await screen.findByText(/گفت‌وگو درباره برنامه/));
  await waitFor(() => expect(screen.getByLabelText("متن پیام")).not.toBeDisabled());
  fireEvent.change(screen.getByLabelText("متن پیام"), { target: { value: "Question" } });
  fireEvent.click(screen.getByRole("button", { name: "ارسال" }));
  await screen.findByText(/ارسال ناموفق/);
  fireEvent.click(screen.getByRole("button", { name: "ارسال" }));
  await waitFor(() => expect(bodies).toHaveLength(2));
  expect(JSON.parse(bodies[0]!).request_id).toBe(JSON.parse(bodies[1]!).request_id);
});

it("handles an invalid conversation response without rendering stale messages", async () => {
  vi.mocked(request).mockResolvedValue({ unexpected: true });
  render(<ConversationPanel kind="workout" reviewId="review" />);
  await screen.findByText(/دریافت گفت‌وگو ناموفق/);
  expect(screen.getByLabelText("متن پیام")).toBeDisabled();
});


it("can page into messages missed while the app was away", async () => {
  vi.useFakeTimers();
  const messages = (start: number, end: number) => Array.from({ length: end - start + 1 }, (_, index) => ({
    id: String(start + index), body: `message-${start + index}`, sender_id: "other",
    created_at: new Date(Date.UTC(2026, 8, 30, 0, 0, start + index)).toISOString(),
  }));
  const base = { available: true, review_id: "review", viewer_id: "member", unread_count: 0 };
  vi.mocked(request).mockResolvedValueOnce({ ...base, messages: messages(1, 50), older_cursor: null })
    .mockResolvedValueOnce({ ...base, messages: messages(101, 150), older_cursor: "101" })
    .mockResolvedValue({ ...base, messages: messages(51, 100), older_cursor: "51" });
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
  try {
    render(<ConversationPanel kind="workout" reviewId="review" initiallyOpen />);
    await act(async () => { await Promise.resolve(); });
    await act(async () => { vi.advanceTimersByTime(10_000); });
    fireEvent.click(screen.getByRole("button", { name: "پیام‌های قبلی" }));
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("message-51")).toBeInTheDocument();
    expect(screen.getByText("message-150")).toBeInTheDocument();
  } finally { vi.useRealTimers(); vi.restoreAllMocks(); }
});
