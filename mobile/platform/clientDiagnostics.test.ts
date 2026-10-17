import { afterEach, expect, it, vi } from "vitest";

vi.mock("expo-constants", () => ({ default: { expoConfig: { version: "2.3.1" }, nativeBuildVersion: "45" } }));
vi.mock("react-native", () => ({ Platform: { OS: "android", Version: 35 } }));

import {
  clearMobileClientDiagnostics,
  configureMobileClientDiagnostics,
  reportMobileClientDiagnostic,
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
