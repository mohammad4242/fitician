import { afterEach, expect, it, vi } from "vitest";
const sdk = vi.hoisted(() => ({ init: vi.fn<(options: { integrations: { name: string }[] }) => void>(), captureException: vi.fn<(error: unknown, hint?: unknown) => string>(() => "a".repeat(32)), linkedErrorsIntegration: () => ({ name: "LinkedErrors" }) }));
vi.mock("@sentry/react", () => sdk);
afterEach(() => { vi.unstubAllEnvs(); vi.clearAllMocks(); });

it("preserves the original React error and one occurrence across the window rethrow", async () => {
  vi.stubEnv("VITE_SENTRY_DSN", "https://public@example.invalid/1");
  const sentry = await import("./sentry");
  const listener = vi.fn();
  const dispose = sentry.onCapturedClientError(listener);
  const error = new TypeError("private medical fixture");
  sentry.captureReactError(error, "\n at PatientForm (/private/path:1)", "uncaught");
  window.dispatchEvent(new ErrorEvent("error", { error }));
  expect(sdk.captureException).toHaveBeenCalledTimes(1);
  expect(sdk.captureException.mock.calls[0]?.[0]).toBe(error);
  expect(listener).toHaveBeenCalledTimes(1);
  const metadata = listener.mock.calls[0]?.[0];
  expect(metadata.sentryEventId).toBe("a".repeat(32));
  expect(metadata.eventId).toMatch(/^[a-f0-9-]{36}$/);
  expect(sdk.captureException).toHaveBeenCalledWith(error, expect.objectContaining({ tags: { diagnostic_event_id: metadata.eventId, service: "web" }, contexts: { react: { componentStack: expect.any(String) } } }));
  expect(sdk.init.mock.calls[0]?.[0].integrations.map(item => item.name)).toEqual(["LinkedErrors"]);
  dispose();
});
