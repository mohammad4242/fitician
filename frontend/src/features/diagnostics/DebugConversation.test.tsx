import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { webcrypto } from "node:crypto";
import { afterEach, expect, it, vi } from "vitest";
import { DebugConversation } from "./DebugConversation";
import { request } from "../../shared/apiClient";
vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
afterEach(() => { vi.clearAllMocks(); sessionStorage.clear(); vi.unstubAllGlobals(); });

it("loads persisted replies and submits a real API run with an idempotency identity", async () => {
  vi.stubGlobal("crypto", webcrypto);
  const mocked = vi.mocked(request);
  mocked.mockImplementation(async (_path, options) => options?.method === "POST" ? { id: "run-1", state: "queued" } as never : {
    messages: [{ id: "message-1", role: "assistant", content: "Existing investigation", created_at: "2026-11-12" }], runs: [], next_cursor: null,
  } as never);
  render(<DebugConversation issueId="issue-1" english />);
  expect(await screen.findByText("Existing investigation")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Your message"), { target: { value: "Inspect evidence" } });
  fireEvent.click(screen.getByText("Send for analysis"));
  await waitFor(() => expect(mocked).toHaveBeenCalledWith("/api/v1/admin/diagnostics/issues/issue-1/messages", expect.objectContaining({
    method: "POST", headers: { "Idempotency-Key": expect.any(String) }, body: JSON.stringify({ content: "Inspect evidence", action: "analyze" }),
  })));
  expect(screen.getByLabelText("Your message")).toHaveValue("");
});
