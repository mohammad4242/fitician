import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DiagnosticsPage } from "./DiagnosticsPage";
import type { DiagnosticEvent, DiagnosticIssue, DiagnosticIssueDetail } from "./api";
import i18n from "../../i18n";

const api = vi.hoisted(() => ({
  getDiagnosticsOverview: vi.fn(), getDiagnosticEvents: vi.fn(), getDiagnosticIssues: vi.fn(),
  getDiagnosticIssue: vi.fn(), getDiagnosticGenerations: vi.fn(), getDiagnosticAlerts: vi.fn(),
  updateDiagnosticIssue: vi.fn(), getDiagnosticInfrastructure: vi.fn(),
}));
vi.mock("./api", () => api);
vi.mock("../../shared/AuthenticatedHeader", () => ({ AuthenticatedHeader: () => null }));

const issue: DiagnosticIssue = {
  id: "issue-1", fingerprint: "safe-fingerprint", component: "planner", operation: "generate", stage: "validate",
  platform: "web", severity: "error", category: "engine_validation", error_code: "PLAN_INVALID",
  exception_type: "ValidationError", source_location: "planner/service.py", confidence: "unknown", title: "Validation failure",
  first_seen: "2026-10-16T08:00:00Z", last_seen: "2026-10-16T09:00:00Z", count: 5, status: "new", regression_count: 0, last_alert_at: null,
};
const event: DiagnosticEvent = {
  event_id: "event-1", issue_id: issue.id, timestamp: "2026-10-16T09:00:00Z", request_id: "request-safe-1", operation_id: "operation-1",
  user_id: "user-1", component: "planner", operation: "generate", stage: "validate", platform: "web", version: "1.2.3", build: "42",
  category: issue.category, severity: issue.severity, error_code: issue.error_code, exception_type: issue.exception_type,
  source_location: issue.source_location, input_fingerprint: null, resource_id: null, outcome: "failure", duration_ms: 120, retry_count: 0,
  http_status: 422, os_version: null,
};
const detail: DiagnosticIssueDetail = {
  issue, events: [event], status_history: [{ id: "history-1", issue_id: issue.id, actor_user_id: "admin-1", previous_status: "new", new_status: "investigating", note: "Reviewed safely", created_at: "2026-10-16T09:10:00Z" }],
};

function renderAt(path = "/admin/diagnostics") {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/admin/diagnostics" element={<DiagnosticsPage />} /></Routes></MemoryRouter>);
}

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage("en");
  api.getDiagnosticsOverview.mockResolvedValue({ hours: 24, event_count: 8, issue_count: 2, failure_count: 2, critical_count: 1, new_issue_count: 1, affected_users: 1, error_rate: 0.25, trend: [{timestamp: "2026-10-16T09:00:00Z", count: 8}], platforms: [{platform: "web", count: 8}], http_response_count: { success: 6, failure: 2 }, infrastructure: { status: "unknown", last_seen: null, outcome: null } });
  api.getDiagnosticEvents.mockResolvedValue([event]);
  api.getDiagnosticIssues.mockResolvedValue([issue]);
  api.getDiagnosticIssue.mockResolvedValue(detail);
  api.getDiagnosticGenerations.mockResolvedValue({ hours: 24, operations: [] });
  api.getDiagnosticAlerts.mockResolvedValue([]);
  api.updateDiagnosticIssue.mockResolvedValue({});
});

describe("admin diagnostics", () => {
  it("shows real overview metrics and an accessible trend chart", async () => {
    renderAt();
    expect((await screen.findAllByText("8")).length).toBeGreaterThan(0);
    expect(await screen.findByTitle("Operation trend")).toBeInTheDocument();
    expect(screen.getByText(/all recorded outcomes/i)).toBeInTheDocument();
    expect(screen.getByText("web")).toBeInTheDocument();
  });

  it("applies event deep-link filters and reflects them in the URL", async () => {
    renderAt("/admin/diagnostics?tab=events&request_id=request-safe-1");
    await screen.findByText("PLAN_INVALID");
    expect(api.getDiagnosticEvents).toHaveBeenCalledWith(expect.objectContaining({ request_id: "request-safe-1" }));
    expect(screen.getByRole("link", { name: /request-safe-1/ })).toHaveAttribute("href", expect.stringContaining("request-safe-1"));
  });

  it("shows issue taxonomy, confidence, status history, and records an admin status note", async () => {
    renderAt("/admin/diagnostics?tab=issues&issue=issue-1");
    expect(await screen.findByText(/not enough evidence/i)).toBeInTheDocument();
    expect(screen.getByText("Reviewed safely")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /admin-1/ })).toHaveAttribute("href", "/admin/billing/users/admin-1");
    fireEvent.change(screen.getByLabelText("Admin note (optional)"), { target: { value: "Checked correlated request" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "investigating" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.updateDiagnosticIssue).toHaveBeenCalledWith("issue-1", "investigating", "Checked correlated request"));
  });

  it("shows loading, errors and retries without exposing member UI", async () => {
    let resolve!: (value: unknown) => void;
    api.getDiagnosticsOverview.mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    renderAt();
    expect(screen.getByRole("status")).toBeInTheDocument();
    await act(async () => resolve({ hours: 24, event_count: 0, issue_count: 0, failure_count: 0, critical_count: 0, new_issue_count: 0, affected_users: 0, error_rate: null, trend: [], platforms: [], http_response_count: { success: 0, failure: 0 }, infrastructure: { status: "unknown", last_seen: null, outcome: null } }));
    await screen.findByText("Successful HTTP responses");
    expect(screen.queryByText(/my workouts|meal plan|profile settings/i)).not.toBeInTheDocument();

    api.getDiagnosticGenerations.mockRejectedValueOnce(new Error("network failure"));
    fireEvent.click(screen.getByRole("tab", { name: "Generations" }));
    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(api.getDiagnosticGenerations).toHaveBeenCalledTimes(2));
  });
});
