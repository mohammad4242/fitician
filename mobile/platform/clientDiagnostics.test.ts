import { afterEach, expect, it, vi } from "vitest";

vi.mock("expo-constants", () => ({ default: { expoConfig: { version: "2.3.1" }, nativeBuildVersion: "45" } }));
vi.mock("react-native", () => ({ Platform: { OS: "android", Version: 35 } }));

import {
  clearMobileClientDiagnostics,
  configureMobileClientDiagnostics,
  flushMobileClientDiagnostics,
  reportMobileClientDiagnostic,
  reportMobileClientRequestSpan,
} from "./clientDiagnostics";

afterEach(() => clearMobileClientDiagnostics());

it("queues a privacy-safe event and suppresses telemetry recursion", async () => {
  const batches: unknown[][] = [];
  configureMobileClientDiagnostics(async (events) => {
    batches.push([...events]);
    if (batches.length === 1) {
      reportMobileClientDiagnostic({ component: "NativeTransport", operation: "telemetry_submit", stage: "failed" });
    }
  });
  reportMobileClientDiagnostic({
    component: "NativeTransport",
    operation: "request",
    stage: "failed",
    correlation_id: "corr-1",
    duration_ms: 28,
    http_status: 503,
    body: "private health data",
  });

  await vi.waitFor(() => expect(batches).toHaveLength(1));
  const event = batches[0]?.[0] as Record<string, unknown>;
  expect(event).toMatchObject({
    platform: "android",
    component: "NativeTransport",
    operation: "request",
    request_id: "corr-1",
    version: "2.3.1",
    build: "45",
    os_version: "35",
    duration_ms: 28,
    http_status: 503,
  });
  expect(Object.keys(event).sort()).not.toContain("body");
  expect(JSON.stringify(batches)).not.toContain("private health data");
  clearMobileClientDiagnostics();
});


it("delivers the same bounded event after connectivity recovery and discards account-cleared events", async () => {
  let online = false;
  const send = vi.fn(async () => { if (!online) throw new Error("offline"); });
  configureMobileClientDiagnostics(send);
  reportMobileClientDiagnostic({ component: "NativeTransport", operation: "request", stage: "failed" });
  await flushMobileClientDiagnostics();
  expect(send).toHaveBeenCalledTimes(1);
  online = true;
  await flushMobileClientDiagnostics();
  expect(send).toHaveBeenCalledTimes(2);
  await flushMobileClientDiagnostics();
  expect(send).toHaveBeenCalledTimes(2);
  online = false;
  reportMobileClientDiagnostic({ component: "NativeTransport", operation: "upload", stage: "failed" });
  await flushMobileClientDiagnostics();
  expect(send).toHaveBeenCalledTimes(3);
  clearMobileClientDiagnostics();
  online = true;
  await flushMobileClientDiagnostics();
  expect(send).toHaveBeenCalledTimes(3);
});

it("queues matched dispatch and terminal request observations", async () => {
  const batches: unknown[][] = [];
  configureMobileClientDiagnostics(async (events) => { batches.push([...events]); });
  reportMobileClientRequestSpan({
    operation: "nutrition",
    requestId: "corr-2",
    traceId: "a".repeat(32),
    spanId: "b".repeat(16),
    parentSpanId: "c".repeat(16),
    terminalStage: "response_received",
    durationMs: 14,
    httpStatus: 200,
    shouldRecord: true,
  });
  await flushMobileClientDiagnostics();

  const events = batches.flat() as Array<Record<string, unknown>>;
  expect(events.map((event) => event.stage)).toEqual(["dispatch", "response_received"]);
  expect(events).toMatchObject([
    { error_code: "CLIENT_REQUEST_OBSERVED", offset_ms: 0, duration_ms: 0 },
    { error_code: "CLIENT_REQUEST_OBSERVED", offset_ms: 0, duration_ms: 14, http_status: 200 },
  ]);
  expect(events[0]).toMatchObject({
    operation_id: "a".repeat(32),
    trace_id: "a".repeat(32),
    span_id: "b".repeat(16),
    parent_span_id: "c".repeat(16),
    request_id: "corr-2",
    version: "2.3.1",
    build: "45",
  });
});

it("emits the normalized transport kind only on the terminal failure span", async () => {
  const batches: unknown[][] = [];
  configureMobileClientDiagnostics(async (events) => { batches.push([...events]); });
  reportMobileClientRequestSpan({
    operation: "request",
    requestId: "corr-offline",
    traceId: "a".repeat(32),
    spanId: "b".repeat(16),
    terminalStage: "transport_failed",
    transportKind: "offline",
    durationMs: 12,
    shouldRecord: true,
  });
  await flushMobileClientDiagnostics();
  const events = batches.flat() as Array<Record<string, unknown>>;
  expect(events[0]).not.toHaveProperty("transport_kind");
  expect(events[1]).toMatchObject({ stage: "transport_failed", transport_kind: "offline" });
});
