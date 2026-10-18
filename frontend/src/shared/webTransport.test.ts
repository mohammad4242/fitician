import { expect, it, vi } from "vitest";

import { createWebTransport } from "./webTransport";

const reportWebClientRequestSpan = vi.hoisted(() => vi.fn());
vi.mock("./clientDiagnostics", () => ({
  reportWebClientRequestSpan,
  webClientPlatform: () => "web",
  webClientVersion: () => null,
}));

it("maps JSON requests through an injected fetch implementation", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const transport = createWebTransport(fetchImpl);

  await expect(
    transport.request<{ ok: boolean }>({
      path: "/api/test",
      method: "POST",
      body: { enabled: true },
    }),
  ).resolves.toEqual({ ok: true });

  expect(fetchImpl).toHaveBeenCalledWith(
    "/api/test",
    expect.objectContaining({
      method: "POST",
      credentials: "include",
      body: JSON.stringify({ enabled: true }),
    }),
  );
});

it("maps multipart parts to browser FormData", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ uploaded: true }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const transport = createWebTransport(fetchImpl);

  await expect(
    transport.upload<{ uploaded: boolean }>({
      path: "/api/upload",
      method: "POST",
      parts: [
        { name: "payload", value: "{}" },
        {
          bytes: new Uint8Array([1, 2, 3]),
          contentType: "application/octet-stream",
          filename: "sample.bin",
          name: "file",
        },
      ],
    }),
  ).resolves.toEqual({ uploaded: true });

  const [, init] = fetchImpl.mock.calls[0];
  expect(new Headers(init?.headers).has("Content-Type")).toBe(false);
  expect(init?.body).toBeInstanceOf(FormData);
  const formData = init?.body as FormData;
  expect(formData.get("payload")).toBe("{}");
  expect(formData.get("file")).toMatchObject({ name: "sample.bin", type: "application/octet-stream" });
  expect(Array.from(new Uint8Array(await (formData.get("file") as File).arrayBuffer()))).toEqual([1, 2, 3]);
});

it("maps binary responses and response metadata", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(new Uint8Array([80, 68, 70]), {
      status: 200,
      headers: {
        "Content-Disposition": "attachment; filename*=UTF-8''plan%20fa.pdf",
        "Content-Type": "application/pdf",
      },
    }),
  );
  const transport = createWebTransport(fetchImpl);

  const result = await transport.download({ path: "/api/plan.pdf", responseType: "binary" });
  expect(result).toMatchObject({
    contentType: "application/pdf",
    filename: "plan fa.pdf",
  });
  expect(Array.from(result.bytes)).toEqual([80, 68, 70]);
});

it("parses structured API errors without falling back to Request failed", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({
      detail: {
        code: "ENTITLEMENT_REQUIRED",
        fields: [{ loc: ["body", "weight_kg"], type: "missing", msg: "Field required" }],
        message: "safe backend message",
        meta: { entitlement: "training.plan.generate", private_note: "do not expose" },
        request_id: "server-request-1",
        retryable: false,
      },
    }), {
      headers: { "Content-Type": "application/json", "X-Correlation-ID": "server-request-1" },
      status: 403,
    }),
  );
  const transport = createWebTransport(fetchImpl);

  await expect(transport.request({ path: "/api/v1/protected" })).rejects.toMatchObject({
    code: "ENTITLEMENT_REQUIRED",
    meta: { entitlement: "training.plan.generate" },
    message: "safe backend message",
    requestId: "server-request-1",
    retryable: false,
    status: 403,
    validationDetails: [{ type: "missing", loc: ["body", "weight_kg"] }],
  });
});

it("parses validation arrays and non-JSON error bodies", async () => {
  const validationFetch = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({
      detail: [{ loc: ["body", "height_cm"], msg: "Field required", type: "missing" }],
    }), { status: 422 }),
  );
  const validationTransport = createWebTransport(validationFetch);
  await expect(validationTransport.request({ path: "/api/v1/profile" })).rejects.toMatchObject({
    code: "VALIDATION_ERROR",
    status: 422,
    validationDetails: [{ type: "missing", loc: ["body", "height_cm"] }],
  });

  const plainFetch = vi.fn<typeof fetch>().mockResolvedValue(
    new Response("upstream returned HTML", { status: 502 }),
  );
  const plainTransport = createWebTransport(plainFetch);
  await expect(plainTransport.request({ path: "/api/v1/profile" })).rejects.toMatchObject({
    code: "BAD_GATEWAY",
    message: "The request could not be completed.",
    status: 502,
  });
});

it("adds one correlation id to every web request", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), { status: 200 }),
  );
  const transport = createWebTransport(fetchImpl, {
    correlationIdFactory: () => "web-correlation-1",
  });

  await transport.request({ path: "/api/v1/test" });

  const [, init] = fetchImpl.mock.calls[0];
  expect(new Headers(init?.headers).get("X-Correlation-ID")).toBe("web-correlation-1");
});

it("propagates a child W3C span and observes successful HTTP responses", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), { status: 200 }),
  );
  const transport = createWebTransport(fetchImpl, {
    monotonicNow: vi.fn().mockReturnValueOnce(500).mockReturnValueOnce(514),
    random: () => 0,
    successSampleRate: 1,
  });

  await transport.request({
    headers: {
      "X-Correlation-ID": "caller-correlation",
      traceparent: `00-${"a".repeat(32)}-${"b".repeat(16)}-01`,
    },
    path: "/api/v1/nutrition/plans?private=1",
  });

  const [, init] = fetchImpl.mock.calls[0]!;
  const headers = new Headers(init?.headers);
  const traceparent = headers.get("traceparent")!;
  expect(traceparent).toMatch(new RegExp(`^00-${"a".repeat(32)}-[0-9a-f]{16}-01$`, "u"));
  expect(traceparent).not.toContain("b".repeat(16));
  expect(headers.get("X-Correlation-ID")).toBe("caller-correlation");
  expect(headers.get("X-Fitician-Platform")).toBe("web");
  expect(reportWebClientRequestSpan).toHaveBeenCalledWith(expect.objectContaining({
    operation: "nutrition",
    requestId: "caller-correlation",
    terminalStage: "response_received",
    durationMs: 14,
    httpStatus: 200,
    shouldRecord: true,
    parentSpanId: "b".repeat(16),
  }));
  expect(JSON.stringify(reportWebClientRequestSpan.mock.calls)).not.toContain("private=1");
});

it("records failed HTTP responses as received and transport failures separately", async () => {
  reportWebClientRequestSpan.mockClear();
  const responseTransport = createWebTransport(
    vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 503 })),
  );
  await expect(responseTransport.request({ path: "/api/v1/test" })).rejects.toMatchObject({ status: 503 });
  expect(reportWebClientRequestSpan).toHaveBeenLastCalledWith(expect.objectContaining({
    terminalStage: "response_received",
    httpStatus: 503,
    shouldRecord: true,
  }));

  reportWebClientRequestSpan.mockClear();
  const failedTransport = createWebTransport(
    vi.fn<typeof fetch>().mockRejectedValue(new TypeError("network error")),
  );
  await expect(failedTransport.request({ path: "/api/v1/test" })).rejects.toMatchObject({ kind: "network" });
  expect(reportWebClientRequestSpan).toHaveBeenCalledWith(expect.objectContaining({
    terminalStage: "transport_failed",
    transportKind: "network",
    shouldRecord: true,
  }));
});

it("samples successful requests while keeping the configured rate deterministic", async () => {
  reportWebClientRequestSpan.mockClear();
  const transport = createWebTransport(
    vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 200 })),
    { random: () => 0.99, successSampleRate: 0.1 },
  );

  await transport.request({ path: "/api/v1/test" });

  expect(reportWebClientRequestSpan).toHaveBeenCalledWith(expect.objectContaining({
    terminalStage: "response_received",
    shouldRecord: false,
  }));
});

it.each([
  ["network", new TypeError("Failed to fetch")],
  ["timeout", new DOMException("The request timed out", "TimeoutError")],
  ["aborted", new DOMException("The request was aborted", "AbortError")],
] as const)("classifies %s runtime failures", async (kind, failure) => {
  reportWebClientRequestSpan.mockClear();
  const fetchImpl = vi.fn<typeof fetch>().mockRejectedValue(failure);
  const transport = createWebTransport(fetchImpl);

  await expect(transport.request({ path: "/api/v1/test" })).rejects.toMatchObject({
    kind,
    name: "TransportError",
  });
  expect(reportWebClientRequestSpan).toHaveBeenCalledWith(expect.objectContaining({
    terminalStage: "transport_failed",
    transportKind: kind,
  }));
});

it("keeps offline failures distinct from generic network failures", async () => {
  const previous = navigator.onLine;
  Object.defineProperty(navigator, "onLine", { configurable: true, value: false });
  try {
    const fetchImpl = vi.fn<typeof fetch>().mockRejectedValue(new TypeError("Failed to fetch"));
    const transport = createWebTransport(fetchImpl);
    await expect(transport.request({ path: "/api/v1/test" })).rejects.toMatchObject({
      kind: "offline",
      name: "TransportError",
    });
    expect(reportWebClientRequestSpan).toHaveBeenCalledWith(expect.objectContaining({
      terminalStage: "transport_failed",
      transportKind: "offline",
    }));
  } finally {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: previous });
  }
});

it("does not report diagnostics ingestion failures back into diagnostics", async () => {
  reportWebClientRequestSpan.mockClear();
  const fetchImpl = vi.fn<typeof fetch>().mockRejectedValue(new TypeError("Failed to fetch"));
  const transport = createWebTransport(fetchImpl);
  await expect(transport.request({ path: "/api/v1/diagnostics/client", method: "POST" })).rejects.toMatchObject({ kind: "network" });
  expect(reportWebClientRequestSpan).not.toHaveBeenCalled();
});

it("does not trace diagnostics explorer requests", async () => {
  reportWebClientRequestSpan.mockClear();
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 200 }));
  const transport = createWebTransport(fetchMock, { successSampleRate: 1 });
  await transport.request({ path: "/api/v1/admin/diagnostics/traces?limit=25" });
  expect(reportWebClientRequestSpan).not.toHaveBeenCalled();
  expect(new Headers(fetchMock.mock.calls[0]?.[1]?.headers).has("traceparent")).toBe(false);
});
