import { afterEach, expect, it, vi } from "vitest";
import { configureWebClientDiagnostics, flushWebClientDiagnostics, reportWebClientDiagnostic } from "./clientDiagnostics";

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
