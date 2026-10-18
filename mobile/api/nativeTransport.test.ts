import { expect, it, vi } from "vitest";

import { createNativeTransport } from "./nativeTransport";
import {
  MobileTelemetryLogger,
  type MobileLogger,
  type SentryCompatibleAdapter,
} from "../platform/logging";

const fileSystem = vi.hoisted(() => {
  const fileConstructor = vi.fn();
  const fileWrite = vi.fn();
  class MockFile {
    readonly uri: string;
    readonly bytes = vi.fn(async () => Uint8Array.from([1, 2, 3]));
    readonly write = fileWrite;
    readonly delete = vi.fn();

    constructor(...uris: unknown[]) {
      fileConstructor();
      const directory = uris[0] as { uri?: string } | undefined;
      this.uri = `${directory?.uri ?? "file:///cache/"}${String(uris[1] ?? "upload.bin")}`;
    }
  }

  return {
    File: MockFile,
    Paths: { cache: { uri: "file:///cache/" } },
    fileConstructor,
    fileWrite,
  };
});

const clientDiagnostics = vi.hoisted(() => ({
  mobileClientPlatform: () => "android" as const,
  mobileClientVersion: () => "2.3.1",
  reportMobileClientRequestSpan: vi.fn(),
}));

vi.mock("expo-file-system", () => fileSystem);
vi.mock("../platform/clientDiagnostics", () => clientDiagnostics);

it("builds native requests from the configured API origin", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
      status: 200,
    }),
  );
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example/",
    fetchImpl,
    trustedOrigin: "https://fitician.example",
  });

  await expect(
    transport.request<{ ok: boolean }>({
      body: { email: "member@example.com" },
      method: "POST",
      path: "/api/v1/auth/register",
    }),
  ).resolves.toEqual({ ok: true });

  const [, init] = fetchImpl.mock.calls[0];
  expect(init).toMatchObject({
    body: JSON.stringify({ email: "member@example.com" }),
    method: "POST",
  });
  const headers = init?.headers as Headers;
  expect(headers.get("Content-Type")).toBe("application/json");
  expect(headers.get("Origin")).toBe("https://fitician.example");
});

it("propagates a child W3C span while preserving correlation and platform headers", async () => {
  clientDiagnostics.reportMobileClientRequestSpan.mockClear();
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), { status: 200 }),
  );
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    correlationIdFactory: () => "native-correlation",
    fetchImpl,
    monotonicNow: vi.fn().mockReturnValueOnce(700).mockReturnValueOnce(725),
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
  const headers = init?.headers as Headers;
  const traceparent = headers.get("traceparent")!;
  expect(traceparent).toMatch(new RegExp(`^00-${"a".repeat(32)}-[0-9a-f]{16}-01$`, "u"));
  expect(traceparent).not.toContain("b".repeat(16));
  expect(headers.get("X-Correlation-ID")).toBe("caller-correlation");
  expect(headers.get("X-Fitician-Platform")).toBe("android");
  expect(headers.get("X-Fitician-Version")).toBe("2.3.1");
  expect(clientDiagnostics.reportMobileClientRequestSpan).toHaveBeenCalledWith(expect.objectContaining({
    operation: "nutrition",
    requestId: "caller-correlation",
    terminalStage: "response_received",
    durationMs: 25,
    httpStatus: 200,
    shouldRecord: true,
    parentSpanId: "b".repeat(16),
  }));
  expect(JSON.stringify(clientDiagnostics.reportMobileClientRequestSpan.mock.calls)).not.toContain("private=1");
});

it("records HTTP responses as received and fetch rejections as transport failures", async () => {
  clientDiagnostics.reportMobileClientRequestSpan.mockClear();
  const responseTransport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 503 })),
  });
  await expect(responseTransport.request({ path: "/api/v1/test" })).rejects.toMatchObject({ status: 503 });
  expect(clientDiagnostics.reportMobileClientRequestSpan).toHaveBeenLastCalledWith(expect.objectContaining({
    terminalStage: "response_received",
    httpStatus: 503,
    shouldRecord: true,
  }));

  clientDiagnostics.reportMobileClientRequestSpan.mockClear();
  const failedTransport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockRejectedValue(new TypeError("network error")),
  });
  await expect(failedTransport.request({ path: "/api/v1/test" })).rejects.toMatchObject({ kind: "network" });
  expect(clientDiagnostics.reportMobileClientRequestSpan).toHaveBeenCalledWith(expect.objectContaining({
    terminalStage: "transport_failed",
    transportKind: "network",
    shouldRecord: true,
  }));
});

it.each([
  ["timeout", new DOMException("The request timed out", "TimeoutError"), "online"],
  ["aborted", new DOMException("The request was aborted", "AbortError"), "online"],
  ["offline", new TypeError("Network request failed"), "offline"],
] as const)("reports normalized native transport kind %s", async (kind, failure, networkState) => {
  clientDiagnostics.reportMobileClientRequestSpan.mockClear();
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockRejectedValue(failure),
    networkStateProvider: () => networkState,
  });
  await expect(transport.request({ path: "/api/v1/test" })).rejects.toMatchObject({
    kind,
    name: "TransportError",
  });
  expect(clientDiagnostics.reportMobileClientRequestSpan).toHaveBeenCalledWith(expect.objectContaining({
    terminalStage: "transport_failed",
    transportKind: kind,
  }));
});

it("converts API error payloads into the shared ApiError", async () => {
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({
        detail: {
          code: "AUTH_INVALID",
          message: "Invalid",
          meta: { entitlement: "none", private_note: "hidden" },
          request_id: "native-server-request-1",
          retryable: false,
        },
      }), {
        headers: {
          "Content-Type": "application/json",
          "X-Correlation-ID": "native-server-request-1",
        },
        status: 401,
      }),
    ),
  });

  await expect(transport.request({ method: "GET", path: "/api/v1/auth/me" })).rejects.toMatchObject({
    code: "AUTH_INVALID",
    message: "Invalid",
    meta: { entitlement: "none" },
    requestId: "native-server-request-1",
    retryable: false,
    status: 401,
  });
});

it("preserves legacy string details while assigning the stable status code", async () => {
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid credentials" }), {
        headers: { "X-Correlation-ID": "native-string-detail-1" },
        status: 401,
      }),
    ),
  });

  await expect(transport.request({ method: "POST", path: "/api/v1/auth/sign-in" })).rejects.toMatchObject({
    code: "UNAUTHORIZED",
    message: "Invalid credentials",
    requestId: "native-string-detail-1",
    status: 401,
  });
});

it("handles non-JSON error bodies without exposing their contents", async () => {
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(
      new Response("<html>stack trace token=secret</html>", { status: 502 }),
    ),
  });

  await expect(transport.request({ path: "/api/v1/test" })).rejects.toMatchObject({
    code: "BAD_GATEWAY",
    message: "The request could not be completed.",
    status: 502,
  });
});

it("parses validation arrays consistently with web", async () => {
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({
        detail: [{ loc: ["body", "weight_kg"], msg: "Field required", type: "missing" }],
      }), { status: 422 }),
    ),
  });

  await expect(transport.request({ path: "/api/v1/profile" })).rejects.toMatchObject({
    code: "VALIDATION_ERROR",
    status: 422,
    validationDetails: [{ type: "missing", loc: ["body", "weight_kg"] }],
  });
});

it.each([
  ["network", new TypeError("Failed to fetch")],
  ["timeout", new DOMException("The request timed out", "TimeoutError")],
  ["aborted", new DOMException("The request was aborted", "AbortError")],
] as const)("classifies %s runtime failures", async (kind, failure) => {
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockRejectedValue(failure),
  });

  await expect(transport.request({ path: "/api/v1/test" })).rejects.toMatchObject({
    kind,
    name: "TransportError",
  });
});

it("keeps offline failures distinct from generic network failures", async () => {
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockRejectedValue(new TypeError("Failed to fetch")),
    networkStateProvider: () => "offline",
  });

  await expect(transport.request({ path: "/api/v1/test" })).rejects.toMatchObject({
    kind: "offline",
    name: "TransportError",
  });
});

it("adds a correlation id and emits redacted request telemetry", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), { status: 200 }),
  );
  const logger = {
    captureException: vi.fn<MobileLogger["captureException"]>(),
    captureMessage: vi.fn<MobileLogger["captureMessage"]>(),
  } satisfies MobileLogger;
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    correlationIdFactory: () => "corr-request-1",
    fetchImpl,
    logger,
  });

  await transport.request({
    body: { email: "member@example.com" },
    method: "POST",
    path: "/api/v1/auth/register/member-1",
  });

  const [, init] = fetchImpl.mock.calls[0];
  expect((init?.headers as Headers).get("X-Correlation-ID")).toBe("corr-request-1");
  expect(logger.captureMessage).toHaveBeenCalledWith(
    "native_request_completed",
    "info",
    expect.objectContaining({
      correlation_id: "corr-request-1",
      method: "POST",
      operation: "request",
      http_status: 200,
    }),
  );
  expect(JSON.stringify(logger.captureMessage.mock.calls[0])).not.toContain("member-1");
  expect(JSON.stringify(logger.captureMessage.mock.calls[0])).not.toContain("member@example.com");
});

it("reports failed HTTP requests without sending response details", async () => {
  const captureException = vi.fn<SentryCompatibleAdapter["captureException"]>();
  const adapter = {
    captureException,
    captureMessage: vi.fn<SentryCompatibleAdapter["captureMessage"]>(),
  } satisfies SentryCompatibleAdapter;
  const logger = new MobileTelemetryLogger(adapter, () => "corr-failure-1");
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    correlationIdFactory: () => "corr-failure-1",
    fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: { code: "PROFILE_PRIVATE", message: "member@example.com" } }),
        { status: 403 },
      ),
    ),
    logger,
  });

  await expect(transport.request({
    method: "GET",
    headers: { traceparent: `00-${"a".repeat(32)}-${"b".repeat(16)}-01` },
    path: "/api/v1/profile/member-1",
  })).rejects.toThrow();

  expect(captureException).toHaveBeenCalledWith(
    expect.any(Error),
    expect.objectContaining({
      correlation_id: "corr-failure-1",
      http_status: 403,
      event: "native_request_failed",
      operation: "onboarding",
      trace_id: "a".repeat(32),
      operation_id: "a".repeat(32),
      parent_span_id: "b".repeat(16),
    }),
  );
  expect(JSON.stringify(captureException.mock.calls[0])).not.toContain("member@example.com");
  expect(JSON.stringify(captureException.mock.calls[0])).not.toContain("PROFILE_PRIVATE");
});

it("does not re-report diagnostics ingestion failures", async () => {
  const logger = {
    captureException: vi.fn<MobileLogger["captureException"]>(),
    captureMessage: vi.fn<MobileLogger["captureMessage"]>(),
  } satisfies MobileLogger;
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockRejectedValue(new TypeError("Failed to fetch")),
    logger,
  });

  await expect(transport.request({ method: "POST", path: "/api/v1/diagnostics/client" })).rejects.toMatchObject({ kind: "network" });
  expect(logger.captureException).not.toHaveBeenCalled();
  expect(logger.captureMessage).not.toHaveBeenCalled();
});

it("serializes multipart bytes without native temporary files", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ uploaded: true }), { status: 200 }),
  );
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl,
  });
  const originalTextEncoder = globalThis.TextEncoder;
  Object.defineProperty(globalThis, "TextEncoder", { configurable: true, value: undefined });
  try {
    await expect(transport.upload({
      method: "PUT",
      parts: [{
        bytes: Uint8Array.from([1, 2, 3]),
        contentType: "image/jpeg",
        filename: "body-front.jpg",
        name: "file",
      }],
      path: "/api/v1/body-photo-sessions/session-1/photos/front",
    })).resolves.toEqual({ uploaded: true });
  } finally {
    Object.defineProperty(globalThis, "TextEncoder", {
      configurable: true,
      value: originalTextEncoder,
    });
  }

  const [, init] = fetchImpl.mock.calls[0];
  const body = init?.body;
  expect(body).toBeInstanceOf(Uint8Array);
  const serialized = new TextDecoder().decode(body as Uint8Array);
  expect(serialized).toContain('name="file"; filename="body-front.jpg"');
  expect(serialized).toContain("Content-Type: image/jpeg");
  expect((init?.headers as Headers).get("Content-Type")).toMatch(
    /^multipart\/form-data; boundary=----FiticianBoundary/u,
  );
  expect(fileSystem.fileConstructor).not.toHaveBeenCalled();
  expect(fileSystem.fileWrite).not.toHaveBeenCalled();
});

it("does not pass the upload manager signal to native fetch", async () => {
  const managerSignal = { aborted: false };
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ uploaded: true }), { status: 200 }),
  );
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl,
  });

  await transport.upload({
    method: "POST",
    parts: [{
      bytes: Uint8Array.from([1, 2, 3]),
      contentType: "image/jpeg",
      filename: "food-photo.jpg",
      name: "file",
    }],
    path: "/api/v1/nutrition/tracking/photo-estimates?language=fa",
    signal: managerSignal,
  });

  const [, init] = fetchImpl.mock.calls[0];
  // The structural upload-manager signal stays outside native fetch; the
  // transport now supplies its own real AbortSignal for the finite deadline.
  expect(init?.signal).toBeInstanceOf(AbortSignal);
  expect(init?.signal).not.toBe(managerSignal);
});

it("rejects absolute API paths so requests cannot escape the configured backend", async () => {
  const fetchImpl = vi.fn<typeof fetch>();
  const transport = createNativeTransport({
    apiBaseUrl: "https://api.fitician.example",
    fetchImpl,
  });

  await expect(transport.request({
    method: "GET",
    path: "https://public.example/api/v1/profile",
  })).rejects.toThrow(/relative/u);
  expect(fetchImpl).not.toHaveBeenCalled();
});

it("does not trace diagnostics explorer requests", async () => {
  clientDiagnostics.reportMobileClientRequestSpan.mockClear();
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 200 }));
  const transport = createNativeTransport({ apiBaseUrl: "https://api.fitician.example", fetchImpl, successSampleRate: 1 });
  await transport.request({ path: "/api/v1/admin/diagnostics/traces?limit=25" });
  expect(clientDiagnostics.reportMobileClientRequestSpan).not.toHaveBeenCalled();
  expect(new Headers(fetchImpl.mock.calls[0]?.[1]?.headers).has("traceparent")).toBe(false);
});
