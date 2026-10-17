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
