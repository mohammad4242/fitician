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
    method: "POST", headers: { "Idempotency-Key": expect.any(String) }, body: JSON.stringify({ content: "Inspect evidence", action: "analyze", occurrence_id: null }),
  })));
  expect(screen.getByLabelText("Your message")).toHaveValue("");
});

it("submits the selected occurrence and binds the retry identity to it", async () => {
  vi.stubGlobal("crypto", webcrypto);
  vi.mocked(request).mockImplementation(async (_path, options) => options?.method === "POST" ? { id: "run-2", state: "queued" } as never : { messages: [], runs: [], next_cursor: null } as never);
  render(<DebugConversation issueId="issue-2" occurrenceId="occurrence-2" english />);
  fireEvent.change(screen.getByLabelText("Your message"), { target: { value: "Inspect selected occurrence" } });
  fireEvent.click(screen.getByText("Send for analysis"));
  await waitFor(() => expect(request).toHaveBeenCalledWith(expect.stringContaining("/messages"), expect.objectContaining({
    body: JSON.stringify({ content: "Inspect selected occurrence", action: "analyze", occurrence_id: "occurrence-2" }),
  })));
});
