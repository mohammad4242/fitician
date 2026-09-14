import { expect, it, vi } from "vitest";

import { createWebTransport } from "./webTransport";

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
  expect((init?.headers as Headers).get("X-Correlation-ID")).toBe("web-correlation-1");
});

it.each([
  ["network", new TypeError("Failed to fetch")],
  ["timeout", new DOMException("The request timed out", "TimeoutError")],
  ["aborted", new DOMException("The request was aborted", "AbortError")],
] as const)("classifies %s runtime failures", async (kind, failure) => {
  const fetchImpl = vi.fn<typeof fetch>().mockRejectedValue(failure);
  const transport = createWebTransport(fetchImpl);

  await expect(transport.request({ path: "/api/v1/test" })).rejects.toMatchObject({
    kind,
    name: "TransportError",
  });
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
  } finally {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: previous });
  }
});
