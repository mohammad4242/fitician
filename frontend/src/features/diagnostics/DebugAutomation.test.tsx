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

it("shows persisted draft PR evidence separately from deployed or resolved states", async () => {
  vi.mocked(request).mockImplementation(async path => path.endsWith("/operations") ? { operations: [{ id: "pr-operation", run_id: "run", occurrence_id: "occurrence", kind: "publish_pr", purpose: "repair_publication", state: "succeeded", environment: "production", profile: "backend", result: { pr_url: "https://github.com/mohammad4242/fitician/pull/43", candidate_commit: "b".repeat(40) } }] } as never : { connected: false, configured: false } as never);
  render(<DebugOperations issueId="issue" occurrenceId="occurrence" english={false} />);
  expect(await screen.findByText("پیشنهاد اصلاح در GitHub")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "مشاهدهٔ PR" })).toHaveAttribute("href", "https://github.com/mohammad4242/fitician/pull/43");
  expect(screen.getByText("این PR به معنی انتشار یا رفع تأییدشدهٔ خطا نیست.")).toBeInTheDocument();
});

it("shows server observations without labeling them as repair or resolution", async () => {
  vi.mocked(request).mockImplementation(async (path) => path.endsWith('/automation-status') ? { connected: false, configured: false } as never : {
    operations: [{ id: 'host-op', kind: 'observe', state: 'succeeded', profile: null, purpose: 'server_observation', environment: 'production', occurrence_id: 'selected-host', result: { observation: { target_environment: 'production-germany', business_outcome_verified: false } } }],
  } as never);
  render(<DebugOperations issueId="host-issue" occurrenceId="selected-host" english />);
  expect(await screen.findByText('Read-only server observations')).toBeInTheDocument();
  expect(screen.getByText('Verified workflow evidence; business outcome unverified')).toBeInTheDocument();
});

it("explains absent GitHub credentials in Persian alongside the exact code", async () => {
  vi.mocked(request).mockImplementation(async path => path.endsWith('/automation-status') ? { connected: false, configured: false } as never : {
    operations: [{ id: 'blocked-ci', kind: 'validate', state: 'blocked', profile: 'backend', purpose: 'repair_validation', environment: 'production', occurrence_id: 'selected', error_code: 'github_credential_not_configured', result: {} }],
  } as never);
  render(<DebugOperations issueId="ci-issue" occurrenceId="selected" english={false} />);
  expect(await screen.findByText(/دسترسی مستقل GitHub تنظیم نشده/)).toBeInTheDocument();
  expect(screen.getByText('github_credential_not_configured')).toBeInTheDocument();
});
