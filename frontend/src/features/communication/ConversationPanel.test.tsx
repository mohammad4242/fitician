import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
