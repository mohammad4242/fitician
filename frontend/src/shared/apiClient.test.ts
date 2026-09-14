import { afterEach, expect, it, vi } from "vitest";

import { request, requestBlob } from "./apiClient";

afterEach(() => vi.restoreAllMocks());

it("always includes cookies and JSON headers", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  await request<{ ok: boolean }>("/api/test", { method: "POST", body: "{}" });

  expect(fetch).toHaveBeenCalledWith(
    "/api/test",
    expect.objectContaining({
      credentials: "include",
    }),
  );
  const [, init] = vi.mocked(fetch).mock.calls[0];
  expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
});

it("preserves headers supplied as a Headers instance", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  await request("/api/test", {
    headers: new Headers({ Authorization: "Bearer token" }),
  });

  const [, init] = vi.mocked(fetch).mock.calls[0];
  const headers = new Headers(init?.headers);
  expect(headers.get("Authorization")).toBe("Bearer token");
  expect(headers.get("Content-Type")).toBe("application/json");
});

it("maps HTTP failures and empty success responses", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Conflict" }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(new Response(null, { status: 204 }));

  await expect(request("/api/fail")).rejects.toMatchObject({
    code: "CONFLICT",
    message: "Conflict",
    retryable: false,
    status: 409,
  });
  await expect(request<void>("/api/empty")).resolves.toBeUndefined();
});

it("uses the shared message for structured validation details", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: [{ msg: "Invalid value" }] }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    }),
  );

  await expect(request("/api/validation-error")).rejects.toMatchObject({
    status: 422,
    code: "VALIDATION_ERROR",
    message: "The request contains invalid fields.",
    details: [{ msg: "Invalid value" }],
  });
});

it("preserves a stable API error code", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: { code: "invalid_geometry" } }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    }),
  );

  await expect(request("/api/photo-error")).rejects.toMatchObject({
    status: 422,
    code: "invalid_geometry",
  });
});

it("lets the browser set the multipart boundary for FormData", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const body = new FormData();
  body.set("payload", "{}");

  await request("/api/upload", { method: "POST", body });

  const [, init] = vi.mocked(fetch).mock.calls[0];
  expect(new Headers(init?.headers).has("Content-Type")).toBe(false);
});

it("downloads binary responses with cookies", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response("%PDF-test", { headers: { "Content-Type": "application/pdf" } }),
  );

  const response = await requestBlob("/api/pdf");

  expect(response.type).toBe("application/pdf");
  expect(await response.text()).toBe("%PDF-test");
  expect(fetch).toHaveBeenCalledWith(
    "/api/pdf",
    expect.objectContaining({ credentials: "include" }),
  );
});

it("maps binary request failures to the existing API error", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "PDF unavailable" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    }),
  );

  await expect(requestBlob("/api/pdf")).rejects.toMatchObject({
    code: "SERVICE_UNAVAILABLE",
    message: "PDF unavailable",
    retryable: true,
    status: 503,
  });
});
