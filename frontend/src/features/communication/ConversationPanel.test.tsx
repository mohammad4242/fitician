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
  await waitFor(() => expect(screen.getByLabelText("متن پیام")).toHaveValue(""));
});

it("handles an invalid conversation response without rendering stale messages", async () => {
  vi.mocked(request).mockResolvedValue({ unexpected: true });
  render(<ConversationPanel kind="workout" reviewId="review" initiallyOpen />);
  await screen.findByText(/دریافت گفت‌وگو ناموفق/);
  expect(screen.queryByLabelText("متن پیام")).not.toBeInTheDocument();
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


it.each(["workout", "nutrition"] as const)("shows a collapsed accessible %s header and a real unavailable state", async kind => {
  vi.mocked(request).mockResolvedValue({ available: false, review_id: null, viewer_id: "member", messages: [], unread_count: 0 });
  render(<ConversationPanel kind={kind} planId="active" />);
  const header = screen.getByRole("button", { name: "گفت‌وگو درباره برنامه" });
  expect(header).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(header);
  expect(header).toHaveAttribute("aria-expanded", "true");
  await screen.findByText(kind === "workout"
    ? "ارسال پیام پس از تخصیص مربی برای برنامه‌ی شما فعال می‌شود."
    : "ارسال پیام پس از تخصیص متخصص این برنامه فعال می‌شود.");
  expect(screen.queryByLabelText("متن پیام")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "ارسال" })).not.toBeInTheDocument();
});

it("keeps unread context, multiline bubbles and initiallyOpen", async () => {
  vi.mocked(request).mockImplementation(async path => path.endsWith("/read") ? undefined as never : ({
    available: true, review_id: "review", viewer_id: "member", unread_count: 2,
    messages: [{ id: "message", sender_id: "other", body: "First line\n" + "long ".repeat(100), created_at: "2026-10-01T10:00:00Z" }],
  }) as never);
  const { container } = render(<ConversationPanel kind="workout" reviewId="review" initiallyOpen />);
  expect(screen.getByRole("button", { name: /گفت‌وگو درباره برنامه/ })).toHaveAttribute("aria-expanded", "true");
  await screen.findByText(/First line/);
  expect(container.querySelector(".conversation-panel__bubble--other p")?.textContent).toContain("First line\n");
  await waitFor(() => expect(request).toHaveBeenCalledWith(expect.stringContaining("/read"), expect.anything()));
});


it("only reads unread messages after expanding the header", async () => {
  vi.mocked(request).mockReset();
  vi.mocked(request).mockImplementation(async (_path, options) => options?.method === "PUT" ? undefined as never : ({
    available: true, review_id: "review", viewer_id: "member", unread_count: 2,
    messages: [{ id: "unread", body: "Hello", sender_id: "other", created_at: "2026-10-01T10:00:00Z" }],
  }) as never);
  render(<ConversationPanel kind="workout" planId="active" />);
  await screen.findByLabelText("2 پیام خوانده‌نشده");
  expect(vi.mocked(request).mock.calls.some(([, options]) => options?.method === "PUT")).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "گفت‌وگو درباره برنامه" }));
  await waitFor(() => expect(screen.queryByLabelText("2 پیام خوانده‌نشده")).not.toBeInTheDocument());
});
