import {
  ClientDiagnosticsQueue,
  createClientDiagnosticEvent,
  type ClientDiagnosticErrorCode,
  type ClientDiagnosticEvent,
} from "@fitician/core";
import Constants from "expo-constants";
import { Platform } from "react-native";

type DiagnosticSender = (events: readonly ClientDiagnosticEvent[]) => Promise<void>;

let queue: ClientDiagnosticsQueue | null = null;
let sendingDiagnostics = 0;

export function configureMobileClientDiagnostics(send: DiagnosticSender): void {
  queue?.clear();
  queue = new ClientDiagnosticsQueue({
    send: async (batch) => {
      sendingDiagnostics += 1;
      try {
        await send(batch.events);
      } finally {
        sendingDiagnostics = Math.max(0, sendingDiagnostics - 1);
      }
    },
  });
}

export async function flushMobileClientDiagnostics(): Promise<void> {
  try { await queue?.flush(); } catch { /* Reconnection telemetry cannot affect app state. */ }
}

export function clearMobileClientDiagnostics(): void {
  queue?.clear();
}

export function reportMobileClientDiagnostic(
  context: Readonly<Record<string, unknown>>,
  code: ClientDiagnosticErrorCode = "API_REQUEST_FAILED",
): void {
  try {
    if (queue === null || sendingDiagnostics > 0) return;
    const event = mobileDiagnosticEvent(context, code);
    if (event !== null) queue.enqueue(event);
  } catch { /* Telemetry must preserve the application outcome. */ }
}

export function reportMobileClientRequestSpan(input: {
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
  try {
    if (!input.shouldRecord || queue === null) return;
    const shared = {
      component: "NativeTransport",
      operation: input.operation,
      operation_id: input.traceId,
      correlation_id: input.requestId,
      trace_id: input.traceId,
      span_id: input.spanId,
      ...(input.parentSpanId ? { parent_span_id: input.parentSpanId } : {}),
      offset_ms: 0,
    };
    const duration = Math.min(Math.max(0, Math.round(input.durationMs)), 86_400_000);
    const dispatch = mobileDiagnosticEvent({ ...shared, stage: "dispatch", duration_ms: 0 }, "CLIENT_REQUEST_OBSERVED");
    const terminal = mobileDiagnosticEvent({
      ...shared,
      stage: input.terminalStage,
      duration_ms: duration,
      ...(input.terminalStage === "transport_failed"
        ? { transport_kind: input.transportKind ?? "unknown" }
        : {}),
      ...(input.httpStatus !== undefined ? { http_status: input.httpStatus } : {}),
    }, "CLIENT_REQUEST_OBSERVED");
    if (dispatch !== null) queue.enqueue(dispatch);
    if (terminal !== null) queue.enqueue(terminal);
  } catch { /* Telemetry must preserve the application outcome. */ }
}

export function mobileClientPlatform(): "android" | "ios_pwa" {
  return Platform.OS === "android" ? "android" : "ios_pwa";
}

export function mobileClientVersion(): string | null {
  const version = safeToken(Constants.expoConfig?.version, "", 64);
  return version || null;
}

function mobileDiagnosticEvent(
  context: Readonly<Record<string, unknown>>,
  code: ClientDiagnosticErrorCode,
): ClientDiagnosticEvent | null {
  const osVersion = String(Platform.Version);
  const transportKind = context.transport_kind;
  const normalizedTransportKind: ClientDiagnosticEvent["transport_kind"] = transportKind === "network"
    || transportKind === "timeout"
    || transportKind === "aborted"
    || transportKind === "offline"
    || transportKind === "unknown"
    ? transportKind
    : undefined;
  return createClientDiagnosticEvent({
    platform: mobileClientPlatform(),
    component: safeToken(context.component, "NativeTransport", 80),
    operation: safeToken(context.operation, "request", 80),
    stage: safeToken(context.stage, "failed", 80),
    error_code: code,
    ...(typeof context.exception_type === "string" ? { exception_type: context.exception_type } : {}),
    ...(typeof context.source_location === "string" ? { source_location: context.source_location } : {}),
    ...(safeToken(context.correlation_id, "", 128) ? { request_id: safeToken(context.correlation_id, "", 128) } : {}),
    ...(safeToken(Constants.expoConfig?.version, "", 64) ? { version: safeToken(Constants.expoConfig?.version, "", 64) } : {}),
    ...(safeToken(Constants.nativeBuildVersion, "", 64) ? { build: safeToken(Constants.nativeBuildVersion, "", 64) } : {}),
    ...(safeToken(context.operation_id, "", 128) ? { operation_id: safeToken(context.operation_id, "", 128) } : {}),
    ...(safeToken(context.trace_id, "", 32) ? { trace_id: safeToken(context.trace_id, "", 32) } : {}),
    ...(safeToken(context.span_id, "", 16) ? { span_id: safeToken(context.span_id, "", 16) } : {}),
    ...(safeToken(context.parent_span_id, "", 16) ? { parent_span_id: safeToken(context.parent_span_id, "", 16) } : {}),
    ...(Number.isFinite(Number(context.offset_ms)) ? { offset_ms: Number(context.offset_ms) } : {}),
    ...(Number.isFinite(Number(context.duration_ms)) ? { duration_ms: Number(context.duration_ms) } : {}),
    ...(Number.isInteger(Number(context.http_status)) && Number(context.http_status) >= 100
      ? { http_status: Number(context.http_status) } : {}),
    ...(normalizedTransportKind ? { transport_kind: normalizedTransportKind } : {}),
    ...(safeToken(osVersion, "", 40) ? { os_version: safeToken(osVersion, "", 40) } : {}),
  });
}

function safeToken(value: unknown, fallback: string, maxLength: number): string {
  if (typeof value !== "string" && typeof value !== "number") return fallback;
  const token = String(value);
  return token.length <= maxLength && /^[A-Za-z0-9_.:-]+$/u.test(token) ? token : fallback;
}
