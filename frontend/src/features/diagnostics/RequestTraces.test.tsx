import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DiagnosticEvent, TraceAnalytics, TraceDetail, TracePage, TraceSummary } from "./api";
import { RequestTraces } from "./RequestTraces";
import i18n from "../../i18n";

const api = vi.hoisted(() => ({
  getDiagnosticTraces: vi.fn(), getDiagnosticTrace: vi.fn(), getDiagnosticTraceAnalytics: vi.fn(),
}));
vi.mock("./api", () => api);
vi.mock("../../shared/AppErrorNotice", () => ({ AppErrorNotice: () => <div /> }));

const trace: TraceSummary = {
  trace_id: "trace-abc", request_id: "req-abc", operation_id: "op-abc", user_id: "user-abc",
  operation: "workout_generation", component: "workout_engine", platform: "backend",
  started_at: "2026-10-18T08:00:00Z", ended_at: "2026-10-18T08:00:00.400Z", duration_ms: 400,
  stage_count: 2, outcome: "failure", failure_stage: "provider_call", http_status: 503,
  incomplete: false, dropped_count: 0,
};
const event: DiagnosticEvent = {
  event_id: "event-abc", issue_id: null, timestamp: trace.started_at, request_id: trace.request_id,
  operation_id: trace.operation_id, user_id: trace.user_id, component: "workout_engine",
  operation: trace.operation, stage: "provider_call", platform: "backend", version: null, build: null,
  category: "provider_failure", severity: "error", error_code: "PROVIDER_UNAVAILABLE",
  exception_type: "TimeoutError", source_location: "provider.py:42", input_fingerprint: null,
  resource_id: null, outcome: "failure", duration_ms: 220, retry_count: 0, http_status: 503,
  os_version: null,
};
const page: TracePage = { items: [trace], limit: 25, offset: 0, has_more: false };
const detail: TraceDetail = {
  trace,
  spans: [
    { ...event, stage: "request_received", trace_id: trace.trace_id, span_id: "span-root", parent_span_id: null, record_type: "span", started_at: trace.started_at, ended_at: trace.ended_at, offset_ms: 0, clock_domain: "backend-monotonic" },
    { ...event, event_id: "event-child", stage: "provider_call", trace_id: trace.trace_id, span_id: "span-child", parent_span_id: "span-root", record_type: "span", started_at: "2026-10-18T08:00:00.100Z", ended_at: "2026-10-18T08:00:00.320Z", offset_ms: 100, duration_ms: 220, clock_domain: "backend-monotonic" },
  ],
  summary: {
    operation: trace.operation, platform: trace.platform, observed_stages: ["request_received", "provider_call"],
    succeeded_stages: ["request_received"], failure_stage: "provider_call", cause: "Provider timed out",
    confidence: "likely", persistence: "confirmed", recommendation: "Inspect provider latency",
    description_fa: "پاسخ سرویس‌دهنده دیر رسید.",
  },
  related_issue_ids: ["issue-abc"], truncated: false,
};
const analytics: TraceAnalytics = {
  observed_requests: 10, success_count: 7, failure_count: 2, incomplete_count: 1, success_rate: 0.7,
  stages: [{ stage: "provider_call", count: 8, failure_count: 2, p50_ms: 120, p95_ms: 400 }],
  operations: [{ operation: "workout_generation", count: 5, failure_count: 1, affected_users: 2 }],
  platforms: [{ platform: "backend", count: 10, failure_count: 2 }], trend: [], limitations: "Only captured requests are included.",
  capture: { success_sample_rate: 1, process_dropped_count: 4, queue_depth: 2, process_local: true },
};

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage("en");
  api.getDiagnosticTraces.mockResolvedValue(page);
  api.getDiagnosticTrace.mockResolvedValue(detail);
  api.getDiagnosticTraceAnalytics.mockResolvedValue(analytics);
});

describe("request traces", () => {
  it("shows analytics, applies trace filters and pages from the returned cursor", async () => {
    render(<MemoryRouter initialEntries={["/admin/diagnostics?tab=traces&request_id=req-abc"]}><RequestTraces /></MemoryRouter>);
    expect(await screen.findByText("trace-abc")).toBeInTheDocument();
    expect(api.getDiagnosticTraces).toHaveBeenCalledWith(expect.objectContaining({ request_id: "req-abc", limit: 25, offset: 0, sort: "newest" }));
    expect(screen.getByText("70%")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Operation"), { target: { value: "workout_generation" } });
    fireEvent.change(screen.getByLabelText("Order"), { target: { value: "slowest" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => expect(api.getDiagnosticTraces).toHaveBeenLastCalledWith(expect.objectContaining({ operation: "workout_generation", sort: "slowest" })));
  });

  it("renders a nested, expandable waterfall with evidence and related admin links", async () => {
    const { container } = render(<MemoryRouter initialEntries={["/admin/diagnostics?tab=traces&trace_id=trace-abc"]}><RequestTraces /></MemoryRouter>);
    expect(await screen.findByText("Provider timed out")).toBeInTheDocument();
    expect(screen.getByText("پاسخ سرویس‌دهنده دیر رسید.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "issue-abc" })).toHaveAttribute("href", "/admin/diagnostics?tab=issues&issue=issue-abc");
    const span = screen.getByRole("button", { name: /provider_call/i });
    fireEvent.click(span);
    expect((await screen.findAllByText(/backend-monotonic/)).length).toBeGreaterThan(0);
    expect(container.querySelectorAll(".diagnostics-waterfall-children")).toHaveLength(1);
    const childBarStyle = container.querySelectorAll(".diagnostics-waterfall-bar")[1]?.getAttribute("style") ?? "";
    expect(childBarStyle).toContain("--trace-left: 31.25%");
    expect(Number.parseFloat(childBarStyle.match(/--trace-width:\s*([\d.]+)%/u)?.[1] ?? "0")).toBeCloseTo(68.75);
    expect(screen.getByRole("link", { name: /user-abc/ })).toHaveAttribute("href", "/admin/billing/users/user-abc");
  });

  it("switches the trace workbench copy and direction for Persian", async () => {
    await i18n.changeLanguage("fa");
    const { container } = render(<MemoryRouter initialEntries={["/admin/diagnostics?tab=traces"]}><RequestTraces /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "ردیابی درخواست‌ها" })).toBeInTheDocument();
    expect(container.querySelector(".diagnostics-traces")).toHaveAttribute("dir", "rtl");
  });

  it("keeps client and backend offsets in independent lanes and labels client receipt timestamps", async () => {
    const successful: TraceSummary = { ...trace, outcome: "success", http_status: 201, failure_stage: null };
    const clientSpan = { ...event, event_id: "client-event", stage: "client_request", platform: "web", outcome: "success", trace_id: trace.trace_id, span_id: "client-span", parent_span_id: null, record_type: "span" as const, started_at: "2026-10-18T09:00:00Z", ended_at: "2026-10-18T09:00:00.600Z", offset_ms: 0, duration_ms: 600, clock_domain: "client" };
    const backendRoot = { ...event, event_id: "backend-root-event", stage: "request_received", trace_id: trace.trace_id, span_id: "backend-root", parent_span_id: "client-span", record_type: "span" as const, started_at: "2026-10-18T08:00:00Z", ended_at: null, offset_ms: 0, duration_ms: null, outcome: "started", clock_domain: "backend" };
    const backendChild = { ...event, event_id: "backend-child-event", stage: "database_read", trace_id: trace.trace_id, span_id: "backend-child", parent_span_id: "backend-root", record_type: "span" as const, started_at: "2026-10-18T08:00:00.100Z", ended_at: "2026-10-18T08:00:00.300Z", offset_ms: 100, duration_ms: 200, clock_domain: "backend" };
    api.getDiagnosticTrace.mockResolvedValue({ ...detail, trace: successful, spans: [clientSpan, backendRoot, backendChild], summary: { ...detail.summary, failure_stage: "database_read" } });
    const { container } = render(<MemoryRouter initialEntries={["/admin/diagnostics?tab=traces&trace_id=trace-abc"]}><RequestTraces /></MemoryRouter>);
    expect(await screen.findByText("Client timestamps show when the server received observations. Offset and duration use the client monotonic clock and have a separate origin.")).toBeInTheDocument();
    const clientExpand = screen.getByRole("button", { name: /client_request/i });
    fireEvent.click(clientExpand);
    expect(screen.getByText(/Server receipt time:/)).toBeInTheDocument();
    expect(screen.getByText(/Last receipt time:/)).toBeInTheDocument();
    expect(screen.getAllByText("The backend root has no completion record; the request remains processing or unknown.").length).toBeGreaterThan(0);
    expect(screen.getByText("Recorded failed stages do not make this completed request a failure.")).toBeInTheDocument();
    const lanes = container.querySelectorAll(".diagnostics-waterfall-lane");
    expect(lanes).toHaveLength(2);
    const backendLane = container.querySelector('[data-clock-domain="backend"]');
    const clientLane = container.querySelector('[data-clock-domain="client"]');
    expect(backendLane?.querySelectorAll(":scope > .diagnostics-waterfall-tree > .diagnostics-waterfall-node > .diagnostics-waterfall-children > .diagnostics-waterfall-node")).toHaveLength(1);
    expect(clientLane?.querySelector(".diagnostics-waterfall-children")).toBeNull();
    expect(backendLane?.querySelector(".diagnostics-waterfall-cross-link")).toHaveTextContent("client-span");
    expect(backendLane?.querySelector(".diagnostics-waterfall-bar")).toHaveAttribute("style", expect.stringContaining("--trace-left: 0%"));
    expect(clientLane?.querySelector(".diagnostics-waterfall-bar")).toHaveAttribute("style", expect.stringContaining("--trace-left: 0%"));
    expect(container.querySelector(".diagnostics-trace-detail-meta .diagnostics-badge")).toHaveTextContent("Unknown");
    expect(screen.getByText("Process dropped records: 4")).toBeInTheDocument();
  });
});
