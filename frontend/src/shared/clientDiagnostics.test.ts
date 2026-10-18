import { afterEach, expect, it, vi } from "vitest";
import {
  configureWebClientDiagnostics,
  flushWebClientDiagnostics,
  reportWebClientDiagnostic,
  reportWebClientRequestSpan,
} from "./clientDiagnostics";

afterEach(() => { configureWebClientDiagnostics(false); vi.unstubAllGlobals(); });

it("delivers only after authentication and clears events across identity changes", async () => {
  const send = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 202 }));
  vi.stubGlobal("fetch", send);
  const input = {component: "Window", operation: "error_event", stage: "unhandled"};
  reportWebClientDiagnostic(input, "CLIENT_RUNTIME_ERROR");
  await flushWebClientDiagnostics();
  expect(send).not.toHaveBeenCalled();
  configureWebClientDiagnostics(true);
  reportWebClientDiagnostic(input, "CLIENT_RUNTIME_ERROR");
  await flushWebClientDiagnostics();
  expect(send).toHaveBeenCalledTimes(1);
  expect(send.mock.calls[0]?.[0]).toBe("/api/v1/diagnostics/client");
  configureWebClientDiagnostics(false);
  reportWebClientDiagnostic(input, "CLIENT_RUNTIME_ERROR");
  await flushWebClientDiagnostics();
  expect(send).toHaveBeenCalledTimes(1);
});


it("records only a bounded OS category/version, never the raw user agent", async () => {
  const send = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 202 }));
  vi.stubGlobal("fetch", send);
  vi.stubGlobal("navigator", { userAgent: "Mozilla iPhone OS 17_6 private-marker", platform: "iPhone", maxTouchPoints: 5 });
  configureWebClientDiagnostics(true);
  reportWebClientDiagnostic({component: "Window", operation: "error_event", stage: "unhandled"}, "CLIENT_RUNTIME_ERROR");
  await flushWebClientDiagnostics();
  const body = JSON.parse(String(send.mock.calls[0]?.[1]?.body));
  expect(body.events[0].os_version).toBe("ios:17.6");
  expect(JSON.stringify(body)).not.toContain("private-marker");
});

it("queues a matched dispatch and response observation without URL or payload fields", async () => {
  const send = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 202 }));
  vi.stubGlobal("fetch", send);
  configureWebClientDiagnostics(true);
  reportWebClientRequestSpan({
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
  await flushWebClientDiagnostics();

  const events = send.mock.calls.flatMap(([, init]) => {
    const body = JSON.parse(String(init?.body)) as { events: Array<Record<string, unknown>> };
    return body.events;
  });
  expect(events.map((event) => event.stage)).toEqual(["dispatch", "response_received"]);
  expect(events).toMatchObject([
    { error_code: "CLIENT_REQUEST_OBSERVED", offset_ms: 0, duration_ms: 0 },
    { error_code: "CLIENT_REQUEST_OBSERVED", offset_ms: 0, duration_ms: 14, http_status: 200 },
  ]);
  expect(events[0]).not.toHaveProperty("transport_kind");
  expect(events[1]).not.toHaveProperty("transport_kind");
  expect(events[0]).toMatchObject({
    operation_id: "a".repeat(32),
    trace_id: "a".repeat(32),
    span_id: "b".repeat(16),
    parent_span_id: "c".repeat(16),
    request_id: "corr-2",
  });
  expect(JSON.stringify(events)).not.toMatch(/url|body|header/i);
});

it("attaches normalized transport kind only to failed terminal observations", async () => {
  const send = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 202 }));
  vi.stubGlobal("fetch", send);
  configureWebClientDiagnostics(true);
  reportWebClientRequestSpan({
    operation: "request",
    requestId: "corr-transport",
    traceId: "a".repeat(32),
    spanId: "b".repeat(16),
    terminalStage: "transport_failed",
    transportKind: "offline",
    durationMs: 10,
    shouldRecord: true,
  });
  await flushWebClientDiagnostics();
  const events = send.mock.calls.flatMap(([, init]) => {
    const body = JSON.parse(String(init?.body)) as { events: Array<Record<string, unknown>> };
    return body.events;
  });
  expect(events[0]).not.toHaveProperty("transport_kind");
  expect(events[1]).toMatchObject({ stage: "transport_failed", transport_kind: "offline" });
});
