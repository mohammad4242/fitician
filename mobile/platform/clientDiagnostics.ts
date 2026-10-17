import {
  ClientDiagnosticsQueue,
  createClientDiagnosticEvent,
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

export function clearMobileClientDiagnostics(): void {
  queue?.clear();
}

export function reportMobileClientDiagnostic(
  context: Readonly<Record<string, unknown>>,
  code: "API_REQUEST_FAILED" | "CLIENT_RENDER_ERROR" | "CLIENT_RUNTIME_ERROR" | "CLIENT_UNHANDLED_REJECTION" = "API_REQUEST_FAILED",
): void {
  try {
    if (queue === null || sendingDiagnostics > 0) return;
    const osVersion = String(Platform.Version);
    const event = createClientDiagnosticEvent({
      platform: Platform.OS === "android" ? "android" : "ios_pwa",
      component: safeToken(context.component, "NativeTransport", 80),
      operation: safeToken(context.operation, "request", 80),
      stage: safeToken(context.stage, "failed", 80),
      error_code: code,
      ...(safeToken(context.correlation_id, "", 128) ? { request_id: safeToken(context.correlation_id, "", 128) } : {}),
      ...(safeToken(Constants.expoConfig?.version, "", 64) ? { version: safeToken(Constants.expoConfig?.version, "", 64) } : {}),
      ...(safeToken(Constants.nativeBuildVersion, "", 64) ? { build: safeToken(Constants.nativeBuildVersion, "", 64) } : {}),
      ...(Number.isFinite(Number(context.duration_ms)) ? { duration_ms: Number(context.duration_ms) } : {}),
      ...(Number.isInteger(Number(context.http_status)) && Number(context.http_status) >= 100
        ? { http_status: Number(context.http_status) } : {}),
      ...(safeToken(osVersion, "", 40) ? { os_version: safeToken(osVersion, "", 40) } : {}),
    });
    if (event !== null) queue.enqueue(event);
  } catch { /* Telemetry must preserve the application outcome. */ }
}

function safeToken(value: unknown, fallback: string, maxLength: number): string {
  if (typeof value !== "string" && typeof value !== "number") return fallback;
  const token = String(value);
  return token.length <= maxLength && /^[A-Za-z0-9_.:-]+$/u.test(token) ? token : fallback;
}
