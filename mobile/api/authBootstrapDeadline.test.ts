import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("expo-secure-store", () => ({}));

import { createNativeTransport } from "./nativeTransport";
import { MobileAuthSession } from "../auth/authSession";
import { loadMobileProfileStatus } from "../ui/navigation/profileRouteState";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

function pendingTransport() {
  const fetchImpl = vi.fn<typeof fetch>(() => new Promise(() => undefined));
  return {
    fetchImpl,
    transport: createNativeTransport({
      apiBaseUrl: "https://fitician.example",
      correlationIdFactory: () => "auth-deadline-test",
      fetchImpl,
    }),
  };
}

it.each([
  "/api/v1/auth/mobile/phone/send-otp",
  "/api/v1/auth/mobile/phone/verify-otp",
  "/api/v1/auth/mobile/password",
  "/api/v1/auth/mobile/google",
  "/api/v1/auth/mobile/refresh",
  "/api/v1/profile/status",
])("bounds a stalled %s request and cancels native fetch", async (path) => {
  const { transport, fetchImpl } = pendingTransport();
  let outcome = "pending";
  const completed = transport.request({ path }).catch((error: { kind: string }) => {
    outcome = error.kind;
  });
  await vi.advanceTimersByTimeAsync(29_999);
  expect(outcome).toBe("pending");
  await vi.advanceTimersByTimeAsync(1);
  expect(outcome).toBe("timeout");
  await completed;
  expect(fetchImpl.mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
  expect(vi.getTimerCount()).toBe(0);
});

it("bounds a stalled response body, not just the response headers", async () => {
  const transport = createNativeTransport({
    apiBaseUrl: "https://fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: () => new Promise(() => undefined),
    } as unknown as Response),
  });
  let outcome = "pending";
  const completed = transport.request({ path: "/api/v1/profile/status" })
    .catch((error: { kind: string }) => { outcome = error.kind; });
  await vi.advanceTimersByTimeAsync(30_000);
  expect(outcome).toBe("timeout");
  await completed;
  expect(vi.getTimerCount()).toBe(0);
});

it("releases the OTP busy state when verification stalls", async () => {
  const { transport } = pendingTransport();
  const session = new MobileAuthSession({
    metadata: { app_version: "0.1.3", device_id: "test-device", device_name: null, platform: "android" },
    refreshTokenStorage: { read: async () => null, write: vi.fn(), clear: vi.fn() },
    transport,
  });
  await session.restore();
  let outcome = "pending";
  const completed = session.verifyPhoneOtp("09123456789", "123456")
    .catch((error: { kind: string }) => { outcome = error.kind; });
  expect(session.getSnapshot().busy).toBe(true);
  await vi.advanceTimersByTimeAsync(30_000);
  expect(outcome).toBe("timeout");
  await completed;
  expect(session.getSnapshot()).toMatchObject({ busy: false, status: "signed_out", user: null });
});

it("changes a stalled profile bootstrap into a recoverable error state", async () => {
  const { transport } = pendingTransport();
  let status = "pending";
  const completed = loadMobileProfileStatus((request) => transport.request(request))
    .then((state) => { status = state.status; });
  await vi.advanceTimersByTimeAsync(30_000);
  expect(status).toBe("error");
  await completed;
});

it("preserves long-running AI requests", async () => {
  let resolveFetch!: (response: Response) => void;
  const transport = createNativeTransport({
    apiBaseUrl: "https://fitician.example",
    fetchImpl: () => new Promise((resolve) => { resolveFetch = resolve; }),
  });
  let outcome = "pending";
  const completed = transport.request({ path: "/api/v1/workouts/programs/generate" })
    .then(() => { outcome = "success"; });
  await vi.advanceTimersByTimeAsync(60_000);
  expect(outcome).toBe("pending");
  expect(vi.getTimerCount()).toBe(0);
  resolveFetch(new Response("{}", { status: 200 }));
  await completed;
  expect(outcome).toBe("success");
});

it("cleans up the deadline after a successful response", async () => {
  const transport = createNativeTransport({
    apiBaseUrl: "https://fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(new Response("{}")),
  });
  await expect(transport.request({ path: "/api/v1/profile/status" })).resolves.toEqual({});
  expect(vi.getTimerCount()).toBe(0);
});

it("keeps caller cancellation distinct from a timeout even if fetch ignores abort", async () => {
  const { transport, fetchImpl } = pendingTransport();
  const controller = new AbortController();
  const completed = transport.request({ path: "/api/v1/profile/status", signal: controller.signal });
  const rejected = expect(completed).rejects.toMatchObject({ kind: "aborted" });
  controller.abort();
  await rejected;
  expect(fetchImpl.mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
  expect(vi.getTimerCount()).toBe(0);
});

it("does not send an already cancelled authentication request", async () => {
  const { transport, fetchImpl } = pendingTransport();
  const controller = new AbortController();
  controller.abort();
  await expect(transport.request({
    path: "/api/v1/auth/mobile/refresh", signal: controller.signal,
  })).rejects.toMatchObject({ kind: "aborted" });
  expect(fetchImpl).not.toHaveBeenCalled();
  expect(vi.getTimerCount()).toBe(0);
});

it("preserves API authentication errors and clears their deadline", async () => {
  const transport = createNativeTransport({
    apiBaseUrl: "https://fitician.example",
    fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", { status: 401 })),
  });
  await expect(transport.request({ path: "/api/v1/auth/mobile/refresh" }))
    .rejects.toMatchObject({ status: 401 });
  expect(vi.getTimerCount()).toBe(0);
});
