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

it("shows recorded tool evidence with its citation identity after reload", async () => {
  vi.mocked(request).mockImplementation(async (path) => path.includes("/events?") ? {
    events: [{ id: "evidence-42", sequence: 1, kind: "tool_completed", payload: { tool: "fitician_read_file", output: "bug.py:2: return a + b", provenance: "connector_tool" } }], next_cursor: 1,
  } as never : { messages: [], runs: [{ id: "run-42", state: "completed", config: {}, error_code: null }], next_cursor: null } as never);
  render(<DebugConversation issueId="issue-42" english />);
  expect(await screen.findByText("bug.py:2: return a + b")).toBeInTheDocument();
  expect(screen.getByText("evidence-42")).toBeInTheDocument();
});

it("shows the retained execution target and an honest Persian offline state", async () => {
  vi.mocked(request).mockImplementation(async (path) => path.includes("/events?") ? { events: [], next_cursor: 0 } as never : {
    messages: [], next_cursor: null,
    runs: [{ id: "run-offline", state: "blocked", error_code: "execution_target_offline", config: { agent_model_id: "chosen-model", connector_name: "Germany server" }, evidence_id: null, occurrence_id: "occurrence-server" }],
  } as never);
  render(<DebugConversation issueId="issue-offline" english={false} occurrenceId="occurrence-server" />);
  expect(await screen.findByText(/اتصال اجرای منتخب آفلاین است/)).toBeInTheDocument();
  expect(screen.getByText("Germany server")).toBeInTheDocument();
  expect(screen.getByText("chosen-model")).toBeInTheDocument();
});
