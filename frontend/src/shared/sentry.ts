import * as Sentry from "@sentry/react";
import { createDiagnosticUuid } from "@fitician/core";
import { sanitizeSentryEvent } from "./sentryPrivacy";

const dsn = import.meta.env.VITE_SENTRY_DSN;
let enabled = false;
if (dsn) {
  try {
  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || "development",
    release: /^[a-f0-9]{40}$/.test(import.meta.env.VITE_APP_BUILD_SHA ?? "")
      ? `fitician-web@${import.meta.env.VITE_APP_BUILD_SHA}` : undefined,
    defaultIntegrations: false,
    // The application owns global and React capture through a single identity below.
    integrations: [Sentry.linkedErrorsIntegration()],
    dataCollection: { userInfo: false, cookies: false, httpHeaders: false, httpBodies: [], urlQueryParams: false, genAI: { inputs: false, outputs: false } },
    maxBreadcrumbs: 0,
    sampleRate: 1,
    tracesSampleRate: 0.05,
    beforeSend: sanitizeSentryEvent,
    beforeSendTransaction: sanitizeSentryEvent,
    beforeBreadcrumb: () => null,
    beforeSendLog: () => null,
  });
  enabled = true;
  } catch {
    // Capture configuration is optional and must not prevent application startup.
  }
}

export interface CapturedClientError {
  eventId: string;
  sentryEventId?: string;
  error: unknown;
  component: "ReactRoot" | "Window";
  operation: "render" | "error_event" | "promise_rejection";
  stage: "caught" | "uncaught" | "unhandled";
}
const captured = new WeakSet<object>();
const pending: CapturedClientError[] = [];
let listener: ((value: CapturedClientError) => void) | undefined;

export function onCapturedClientError(callback: (value: CapturedClientError) => void): () => void {
  listener = callback;
  for (const value of pending.splice(0)) callback(value);
  return () => { if (listener === callback) listener = undefined; };
}

function capture(error: unknown, metadata: Pick<CapturedClientError, "component" | "operation" | "stage">, componentStack?: string | null) {
  const object = (typeof error === "object" && error !== null) || typeof error === "function" ? error as object : undefined;
  if (object && captured.has(object)) return;
  if (object) captured.add(object);
  const eventId = createDiagnosticUuid();
  let sentryEventId: string | undefined;
  try {
    if (enabled) {
      const id = Sentry.captureException(error, {
        tags: { diagnostic_event_id: eventId, service: "web" },
        ...(componentStack ? { contexts: { react: { componentStack } } } : {}),
      });
      if (/^[a-f0-9]{32}$/.test(id)) sentryEventId = id;
    }
  } catch { /* SDK failure cannot replace the original error or prevent local diagnostics. */ }
  const value = { ...metadata, error, eventId, ...(sentryEventId ? { sentryEventId } : {}) };
  if (listener) {
    try { listener(value); } catch { /* Local persistence is independent of SDK transport. */ }
  }
  else { if (pending.length === 16) pending.shift(); pending.push(value); }
}

export function captureReactError(error: unknown, componentStack?: string | null, stage: "caught" | "uncaught" = "caught") {
  capture(error, { component: "ReactRoot", operation: "render", stage }, componentStack);
}

if (typeof window !== "undefined") {
  window.addEventListener("error", event => capture(event.error, { component: "Window", operation: "error_event", stage: "unhandled" }));
  window.addEventListener("unhandledrejection", event => capture(event.reason, { component: "Window", operation: "promise_rejection", stage: "unhandled" }));
}
