import { safeClientException } from "@fitician/core";
import { reportMobileClientDiagnostic } from "./clientDiagnostics";

interface GlobalErrorUtils {
  getGlobalHandler?: () => (error: unknown, isFatal?: boolean) => void;
  setGlobalHandler?: (handler: (error: unknown, isFatal?: boolean) => void) => void;
}

interface RejectionEventLike {
  readonly reason?: unknown;
}

type RejectionHandler = ((event: RejectionEventLike) => void) | null;

export function installMobileRuntimeDiagnostics(): () => void {
  const runtimeGlobal = globalThis as typeof globalThis & {
    ErrorUtils?: GlobalErrorUtils;
    onunhandledrejection?: RejectionHandler;
  };
  const errorUtils = runtimeGlobal.ErrorUtils;
  const previousErrorHandler = errorUtils?.getGlobalHandler?.();
  const errorHandler = (error: unknown, isFatal?: boolean): void => {
    reportMobileClientDiagnostic({
      component: "ReactNativeRuntime",
      operation: "global_error",
      stage: isFatal ? "fatal" : "unhandled",
      ...safeClientException(error),
    }, "CLIENT_RUNTIME_ERROR");
    previousErrorHandler?.(error, isFatal);
  };
  if (previousErrorHandler !== undefined) errorUtils?.setGlobalHandler?.(errorHandler);

  const previousRejectionHandler = runtimeGlobal.onunhandledrejection;
  const rejectionHandler: NonNullable<RejectionHandler> = (event) => {
    reportMobileClientDiagnostic({
      component: "ReactNativeRuntime",
      operation: "promise_rejection",
      stage: "unhandled",
      ...safeClientException(event.reason),
    }, "CLIENT_UNHANDLED_REJECTION");
    previousRejectionHandler?.(event);
  };
  if (typeof previousRejectionHandler === "function") {
    runtimeGlobal.onunhandledrejection = rejectionHandler;
  }

  return () => {
    if (errorUtils?.getGlobalHandler?.() === errorHandler && previousErrorHandler) {
      errorUtils.setGlobalHandler?.(previousErrorHandler);
    }
    if (runtimeGlobal.onunhandledrejection === rejectionHandler) {
      runtimeGlobal.onunhandledrejection = previousRejectionHandler ?? null;
    }
  };
}
