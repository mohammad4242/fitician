import { describe, expect, it, vi } from "vitest";

import {
  ClientDiagnosticsQueue,
  createClientDiagnosticEvent,
  isClientDiagnosticEvent,
  type ClientDiagnosticBatch,
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
