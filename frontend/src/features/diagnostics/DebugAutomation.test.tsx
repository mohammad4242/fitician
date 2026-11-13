import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../../shared/apiClient";
import { DebugAutomationSetup, DebugOperations } from "./DebugAutomation";
vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
beforeEach(() => { vi.mocked(request).mockReset(); });

it("loads persisted CI evidence without dispatching and identifies its occurrence and purpose", async () => {
  vi.mocked(request).mockImplementation(async path => path.endsWith("/operations") ? { operations: [{
    id: "job-1", run_id: "run-1", occurrence_id: "occurrence-old", kind: "validate", state: "succeeded",
    environment: "production", profile: "backend", purpose: "connection_check", error_code: null,
    created_at: "2026-11-13", updated_at: "2026-11-13", cancel_requested: false,
    result: { candidate_commit: "a".repeat(40), workflow_run_id: 123, validation: { exercised: 28 } },
  }] } as never : { connected: false, configured: false, live_validation_verified: false } as never);
  render(<DebugOperations issueId="issue-1" occurrenceId="selected-occurrence" english={false} />);
  expect((await screen.findAllByText("آزمایش اتصال CI")).length).toBeGreaterThan(0);
  expect(screen.getByText("occurrence-old")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "GitHub Actions" })).toHaveAttribute("href", "https://github.com/mohammad4242/fitician/actions/runs/123");
  expect(vi.mocked(request).mock.calls.every(([, options]) => !options?.method || options.method === "GET")).toBe(true);
});

it("binds an explicit connection test to the selected occurrence without starting analysis", async () => {
  vi.mocked(request).mockImplementation(async (path, options) => options?.method === "POST" ? { id: "job-1" } as never : path.endsWith("/operations") ? { operations: [] } as never : { connected: true, configured: true, live_validation_verified: false } as never);
  render(<DebugOperations issueId="issue-1" occurrenceId="occurrence-1" english />);
  const button = await screen.findByRole("button", { name: "Test CI connection" });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  await waitFor(() => expect(request).toHaveBeenCalledWith("/api/v1/admin/diagnostics/issues/issue-1/automation-probe", expect.objectContaining({ method: "POST", body: JSON.stringify({ occurrence_id: "occurrence-1" }) })));
  expect(vi.mocked(request).mock.calls.every(([path]) => !path.endsWith("/messages"))).toBe(true);
});

it("downloads enrollment credentials without displaying or storing them", async () => {
  vi.mocked(request).mockImplementation(async (_path, options) => options?.method === "POST" ? { id: "worker", token: "private-test-enrollment", environment: "production", repository_name: "mohammad4242/fitician" } as never : [] as never);
  URL.createObjectURL = vi.fn(() => "blob:private-config");
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  render(<DebugAutomationSetup english />);
  fireEvent.click(screen.getByRole("button", { name: "Enroll Germany CI broker" }));
  await waitFor(() => expect(click).toHaveBeenCalled());
  expect(document.body.textContent).not.toContain("private-test-enrollment");
  expect(JSON.stringify(localStorage)).not.toContain("private-test-enrollment");
  expect(JSON.stringify(sessionStorage)).not.toContain("private-test-enrollment");
  click.mockRestore();
});
