import { describe, expect, it, vi } from "vitest";

import {
  ClientDiagnosticsQueue,
  createClientDiagnosticEvent,
  createClientRequestTraceContext,
  isClientDiagnosticEvent,
  type ClientDiagnosticBatch,
  type ClientDiagnosticEvent,
} from "./diagnostics";

const base = {
  platform: "web" as const,
  component: "WebTransport",
  operation: "request",
  stage: "failed",
  error_code: "API_REQUEST_FAILED" as const,
};

function event(index = 1) {
  return createClientDiagnosticEvent(base, () => `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`)!;
}

describe("client diagnostics", () => {
  it("accepts the closed event schema and rejects arbitrary fields and unsafe tokens", () => {
    expect(isClientDiagnosticEvent(event())).toBe(true);
    expect(isClientDiagnosticEvent({ ...event(), message: "private data" })).toBe(false);
    expect(createClientDiagnosticEvent({ ...base, component: "private/user@example.com" })).toBeNull();
  });

  it("validates traced request observations and W3C traceparent contexts", () => {
    const trace = createClientRequestTraceContext(null, (length) => "a".repeat(length));
    expect(trace).toEqual({
      traceId: "a".repeat(32),
      spanId: "a".repeat(16),
      traceparent: `00-${"a".repeat(32)}-${"a".repeat(16)}-01`,
    });
    const child = createClientRequestTraceContext(
      `00-${"b".repeat(32)}-${"c".repeat(16)}-01`,
      (length) => "d".repeat(length),
    );
    expect(child).toEqual({
      traceId: "b".repeat(32),
      spanId: "d".repeat(16),
      parentSpanId: "c".repeat(16),
      traceparent: `00-${"b".repeat(32)}-${"d".repeat(16)}-01`,
    });
    expect(createClientRequestTraceContext("not-a-trace", (length) => "e".repeat(length)).traceId)
      .toBe("e".repeat(32));
    expect(createClientRequestTraceContext(
      `00-${"0".repeat(32)}-${"f".repeat(16)}-01`,
      (length) => "e".repeat(length),
    )).not.toHaveProperty("parentSpanId");

    const observed = createClientDiagnosticEvent({
      platform: "web",
      component: "WebTransport",
      operation: "request",
      operation_id: trace.traceId,
      stage: "response_received",
      error_code: "CLIENT_REQUEST_OBSERVED",
      request_id: "corr-1",
      trace_id: trace.traceId,
      span_id: trace.spanId,
      offset_ms: 0,
      duration_ms: 14,
    });
    expect(observed).not.toBeNull();
    expect(isClientDiagnosticEvent({ ...observed, body: "private" })).toBe(false);
    expect(isClientDiagnosticEvent({ ...observed, stage: "response_failed" })).toBe(false);
  });

  it.each(["network", "timeout", "aborted", "offline", "unknown"] as const)(
    "accepts normalized terminal transport kind %s only on transport failures",
    (transportKind) => {
      const failed = createClientDiagnosticEvent({
        ...base,
        stage: "transport_failed",
        error_code: "CLIENT_REQUEST_OBSERVED",
        transport_kind: transportKind,
      });
      expect(failed).not.toBeNull();
      expect(isClientDiagnosticEvent(failed)).toBe(true);
      expect(isClientDiagnosticEvent({ ...failed, stage: "dispatch" })).toBe(false);
      expect(isClientDiagnosticEvent({ ...failed, transport_kind: "private" })).toBe(false);
    },
  );

  it("deduplicates without request IDs and sends no more than ten events per batch", async () => {
    let now = 1_000;
    let releaseFirst!: () => void;
    const firstSend = new Promise<void>((resolve) => { releaseFirst = resolve; });
    const send = vi.fn(async (_batch: ClientDiagnosticBatch) => {
      if (send.mock.calls.length === 1) await firstSend;
    });
    const queue = new ClientDiagnosticsQueue({ send, now: () => now });
    expect(queue.enqueue(event(1))).toBe(true);
    expect(queue.enqueue({ ...event(2), request_id: "req-2" })).toBe(false);
    now += 60_001;
    for (let i = 2; i < 14; i += 1) queue.enqueue({ ...event(i), operation: `request${i}` });
    releaseFirst();
    await queue.flush();
    expect(send.mock.calls.map(([batch]) => batch.events.length)).toEqual([1, 10, 2]);
  });

  it("keeps distinct client spans when request observations share the same stage", async () => {
    const received: ClientDiagnosticEvent[][] = [];
    const queue = new ClientDiagnosticsQueue({
      send: async ({ events }) => { received.push([...events]); },
    });
    const requestEvent = (traceId: string) => createClientDiagnosticEvent({
      platform: "web",
      component: "WebTransport",
      operation: "nutrition",
      operation_id: traceId,
      stage: "dispatch",
      error_code: "CLIENT_REQUEST_OBSERVED",
      trace_id: traceId,
      span_id: "1".repeat(16),
      offset_ms: 0,
      duration_ms: 0,
    })!;

    queue.enqueue(requestEvent("2".repeat(32)));
    queue.enqueue(requestEvent("3".repeat(32)));
    await queue.flush();

    expect(received.flat().map((item) => item.trace_id)).toEqual([
      "2".repeat(32),
      "3".repeat(32),
    ]);
  });

  it("bounds the queue, retries three times with backoff, and clears queued events", async () => {
    const scheduled: Array<{ callback: () => void; delay: number }> = [];
    const send = vi.fn(async () => { throw new Error("failure detail must not escape"); });
    const queue = new ClientDiagnosticsQueue({
      send,
      schedule: (callback, delay) => {
        scheduled.push({ callback, delay });
        return setTimeout(() => {}, 0);
      },
      cancel: () => {},
    });
    for (let i = 1; i <= 35; i += 1) queue.enqueue({ ...event(i), operation: `op${i}` });
    await queue.flush();
    expect(queue.size()).toBeLessThanOrEqual(30);
    expect(scheduled[0]?.delay).toBe(1_000);
    scheduled.shift()?.callback();
    await queue.flush();
    expect(scheduled[0]?.delay).toBe(2_000);
    scheduled.shift()?.callback();
    await queue.flush();
    expect(scheduled[0]?.delay).toBe(4_000);
    scheduled.shift()?.callback();
    await queue.flush();
    expect(send).toHaveBeenCalledTimes(4);
    expect(scheduled).toHaveLength(0);
    queue.clear();
    expect(queue.size()).toBe(0);
  });

  it("keeps the in-flight batch intact when the bounded queue overflows", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const delivered: string[] = [];
    const queue = new ClientDiagnosticsQueue({
      send: async ({ events }) => {
        if (delivered.length === 0) await gate;
        delivered.push(...events.map((item) => item.operation));
      },
    });
    queue.enqueue({ ...event(1), operation: "op1" });
    for (let i = 2; i <= 31; i += 1) queue.enqueue({ ...event(i), operation: `op${i}` });
    expect(queue.size()).toBe(30);
    release();
    await queue.flush();
    expect(delivered).toHaveLength(30);
    expect(delivered[0]).toBe("op1");
    expect(delivered).not.toContain("op2");
    expect(delivered).toContain("op31");
  });
});

it("does not remove a new account's queued event when an old delivery finishes", async () => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const delivered: string[][] = [];
  const queue = new ClientDiagnosticsQueue({ send: async (batch) => {
    delivered.push(batch.events.map((row) => row.event_id));
    if (delivered.length === 1) await gate;
  } });
  queue.enqueue(event(1));
  queue.clear();
  queue.enqueue(event(2));
  release();
  await queue.flush();
  await Promise.resolve();
  expect(delivered).toEqual([[event(1).event_id], [event(2).event_id]]);
  expect(queue.size()).toBe(0);
});

it("calls default host timers without attaching the queue as their receiver", async () => {
  const nativeSchedule = globalThis.setTimeout;
  const nativeCancel = globalThis.clearTimeout;
  const scheduledReceivers: unknown[] = [];
  const cancelledReceivers: unknown[] = [];
  vi.stubGlobal("setTimeout", function (this: unknown, callback: () => void, delay: number) {
    scheduledReceivers.push(this);
    return nativeSchedule(callback, delay);
  });
  vi.stubGlobal("clearTimeout", function (this: unknown, timer: ReturnType<typeof setTimeout>) {
    cancelledReceivers.push(this);
    nativeCancel(timer);
  });
  const queue = new ClientDiagnosticsQueue({ send: async () => { throw new Error("offline"); } });
  try {
    queue.enqueue(event());
    await queue.flush();
    queue.clear();
    expect(scheduledReceivers).toEqual([undefined]);
    expect(cancelledReceivers).toEqual([undefined]);
  } finally {
    queue.clear();
    vi.unstubAllGlobals();
  }
});
