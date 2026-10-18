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

export function webClientPlatform(): "web" | "ios_pwa" {
  return clientPlatform();
}

export function webClientVersion(): string | null {
  const env = import.meta.env as unknown as Readonly<Record<string, unknown>>;
  const version = env.VITE_APP_VERSION;
  return typeof version === "string" && /^[A-Za-z0-9_.:-]{1,64}$/u.test(version)
    ? version
    : null;
}

function browserOsVersion(): string {
  if (typeof navigator === "undefined") return "unknown";
  const agent = navigator.userAgent;
  if (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1) return "ipados:unknown";
  for (const [category, pattern] of [
    ["ios", /(?:iPhone|iPad|iPod).*OS (\d{1,2})(?:[_.](\d{1,2}))?/u],
    ["android", /Android (\d{1,2})(?:\.(\d{1,2}))?/u],
    ["windows_nt", /Windows NT (\d{1,2})(?:\.(\d{1,2}))?/u],
    ["macos", /Mac OS X (\d{1,2})(?:[_.](\d{1,2}))?/u],
  ] as const) {
    const match = pattern.exec(agent);
    if (match) return `${category}:${match[1]}${match[2] ? `.${match[2]}` : ""}`;
  }
  return /Linux/u.test(agent) ? "linux:unknown" : "unknown";
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
    const event = createClientDiagnosticEvent({ ...input, ...buildFields, platform: clientPlatform(), os_version: browserOsVersion(), error_code: errorCode });
    if (event !== null) queue.enqueue(event);
  } catch { /* Telemetry cannot alter the original UI or transport result. */ }
}

export function reportWebClientRequestSpan(input: {
  readonly operation: string;
  readonly requestId: string;
  readonly traceId: string;
  readonly spanId: string;
  readonly parentSpanId?: string;
  readonly terminalStage: "response_received" | "transport_failed";
  readonly transportKind?: "network" | "timeout" | "aborted" | "offline" | "unknown";
  readonly durationMs: number;
  readonly httpStatus?: number;
  readonly shouldRecord: boolean;
}): void {
  if (!input.shouldRecord) return;
  const shared = {
    component: "WebTransport",
    operation: input.operation,
    operation_id: input.traceId,
    request_id: input.requestId,
    trace_id: input.traceId,
    span_id: input.spanId,
    ...(input.parentSpanId ? { parent_span_id: input.parentSpanId } : {}),
    offset_ms: 0,
  };
  const duration = Math.min(Math.max(0, Math.round(input.durationMs)), 86_400_000);
  reportWebClientDiagnostic({ ...shared, stage: "dispatch", duration_ms: 0 }, "CLIENT_REQUEST_OBSERVED");
  reportWebClientDiagnostic({
    ...shared,
    stage: input.terminalStage,
    duration_ms: duration,
    ...(input.terminalStage === "transport_failed"
      ? { transport_kind: input.transportKind ?? "unknown" }
      : {}),
    ...(input.httpStatus !== undefined ? { http_status: input.httpStatus } : {}),
  }, "CLIENT_REQUEST_OBSERVED");
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
