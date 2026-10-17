import { afterEach, expect, it, vi } from "vitest";

const reportMobileClientDiagnostic = vi.hoisted(() => vi.fn());
vi.mock("./clientDiagnostics", () => ({ reportMobileClientDiagnostic }));

import { installMobileRuntimeDiagnostics } from "./runtimeDiagnostics";

afterEach(() => {
  vi.unstubAllGlobals();
});

it("chains existing native error and rejection handlers while reporting fixed fields", () => {
  const previousError = vi.fn();
  const previousRejection = vi.fn();
  let currentHandler = previousError;
  const ErrorUtils = {
    getGlobalHandler: () => currentHandler,
    setGlobalHandler: (handler: typeof currentHandler) => { currentHandler = handler; },
  };
  vi.stubGlobal("ErrorUtils", ErrorUtils);
  vi.stubGlobal("onunhandledrejection", previousRejection);

  const uninstall = installMobileRuntimeDiagnostics();
  const error = new Error("private member data");
  error.stack = "Error: private member data\n at anonymous (index.android.bundle:1:77)";
  currentHandler(error, true);
  const rejectionHandler = (globalThis as typeof globalThis & {
    onunhandledrejection: (event: { reason?: unknown }) => void;
  }).onunhandledrejection;
  rejectionHandler({ reason: "private rejection" });

  expect(previousError).toHaveBeenCalledOnce();
  expect(previousRejection).toHaveBeenCalledOnce();
  expect(reportMobileClientDiagnostic).toHaveBeenNthCalledWith(1, {
    component: "ReactNativeRuntime",
    operation: "global_error",
    stage: "fatal",
    exception_type: "Error",
    source_location: "index.android.bundle:1:77",
  }, "CLIENT_RUNTIME_ERROR");
  expect(reportMobileClientDiagnostic).toHaveBeenNthCalledWith(2, {
    component: "ReactNativeRuntime",
    operation: "promise_rejection",
    stage: "unhandled",
  }, "CLIENT_UNHANDLED_REJECTION");
  uninstall();
  expect(currentHandler).toBe(previousError);
});
