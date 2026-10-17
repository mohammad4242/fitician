import {
  ClientDiagnosticsQueue,
  safeClientException,
  createClientDiagnosticEvent,
  type ClientDiagnosticErrorCode,
  type ClientDiagnosticEvent,
} from "@fitician/core";

let authenticated = false;

type DiagnosticInput = Omit<ClientDiagnosticEvent, "event_id" | "platform" | "error_code">;

function clientPlatform(): "web" | "ios_pwa" {
  if (typeof navigator === "undefined") return "web";
  const extendedNavigator = navigator as Navigator & { standalone?: boolean };
  const isAppleMobile = /iPhone|iPad|iPod/u.test(navigator.userAgent)
    || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  return extendedNavigator.standalone === true && isAppleMobile ? "ios_pwa" : "web";
}

async function sendDiagnostics(events: readonly ClientDiagnosticEvent[]): Promise<void> {
  if (typeof fetch !== "function") throw new Error("diagnostics transport unavailable");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3_000);
  try {
  const response = await fetch("/api/v1/diagnostics/client", {
    signal: controller.signal,
    body: JSON.stringify({ events }),
    cache: "no-store",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    keepalive: true,
    method: "POST",
  });
  if ([401, 403, 422].includes(response.status)) return;
  if (!response.ok) throw new Error("diagnostics request failed");
  } finally { clearTimeout(timeout); }
}

const queue = new ClientDiagnosticsQueue({ send: (batch) => sendDiagnostics(batch.events) });

export function reportWebClientDiagnostic(
  input: DiagnosticInput,
  errorCode: ClientDiagnosticErrorCode,
): void {
  if (!authenticated) return;
  try {
    const build = import.meta.env.VITE_APP_BUILD_SHA as unknown;
    const buildFields = typeof build === "string" && /^[a-f0-9]{7,40}$/u.test(build) ? { build } : {};
    const event = createClientDiagnosticEvent({ ...input, ...buildFields, platform: clientPlatform(), error_code: errorCode });
    if (event !== null) queue.enqueue(event);
  } catch { /* Telemetry cannot alter the original UI or transport result. */ }
}

export function reportWebApiFailure(input: {
  readonly operation: string;
  readonly requestId?: string | null;
  readonly durationMs: number;
  readonly httpStatus?: number;
  readonly stage: string;
}): void {
  reportWebClientDiagnostic({
    component: "WebTransport",
    operation: input.operation,
    stage: input.stage,
    ...(input.requestId ? { request_id: input.requestId } : {}),
    duration_ms: Math.min(Math.max(0, Math.round(input.durationMs)), 86_400_000),
    ...(input.httpStatus !== undefined ? { http_status: input.httpStatus } : {}),
  }, "API_REQUEST_FAILED");
}

export function installWebRuntimeDiagnostics(): () => void {
  if (typeof window === "undefined") return () => {};
  const onError = (event: ErrorEvent) => {
    reportWebClientDiagnostic({ component: "Window", operation: "error_event", stage: "unhandled", ...safeClientException(event.error) }, "CLIENT_RUNTIME_ERROR");
  };
  const onRejection = (event: PromiseRejectionEvent) => {
    reportWebClientDiagnostic({ component: "Window", operation: "promise_rejection", stage: "unhandled", ...safeClientException(event.reason) }, "CLIENT_UNHANDLED_REJECTION");
  };
  window.addEventListener("error", onError);
  window.addEventListener("unhandledrejection", onRejection);
  const online = () => { void queue.flush(); };
  window.addEventListener("online", online);
  return () => {
    window.removeEventListener("error", onError);
    window.removeEventListener("unhandledrejection", onRejection);
    window.removeEventListener("online", online);
  };
}

export function reportReactRootError(stage: "caught" | "uncaught", error?: unknown): void {
  reportWebClientDiagnostic({ component: "ReactRoot", operation: "render", stage, ...safeClientException(error) }, "CLIENT_RENDER_ERROR");
}

export async function flushWebClientDiagnostics(): Promise<void> {
  await queue.flush();
}

export function clearWebClientDiagnostics(): void { queue.clear(); }

export function configureWebClientDiagnostics(isAuthenticated: boolean): void {
  queue.clear();
  authenticated = isAuthenticated;
}
