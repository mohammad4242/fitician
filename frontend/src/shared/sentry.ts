import * as Sentry from "@sentry/react";
import { sanitizeSentryEvent } from "./sentryPrivacy";

const dsn = import.meta.env.VITE_SENTRY_DSN;
if (dsn) {
  try {
  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || "development",
    release: /^[a-f0-9]{40}$/.test(import.meta.env.VITE_APP_BUILD_SHA ?? "")
      ? `fitician-web@${import.meta.env.VITE_APP_BUILD_SHA}` : undefined,
    defaultIntegrations: false,
    integrations: [Sentry.globalHandlersIntegration(), Sentry.dedupeIntegration()],
    dataCollection: { userInfo: false, cookies: false, httpHeaders: false, httpBodies: [], urlQueryParams: false, genAI: { inputs: false, outputs: false } },
    maxBreadcrumbs: 0,
    sampleRate: 1,
    tracesSampleRate: 0.05,
    beforeSend: sanitizeSentryEvent,
    beforeSendTransaction: sanitizeSentryEvent,
    beforeBreadcrumb: () => null,
    beforeSendLog: () => null,
  });
  } catch {
    // Capture configuration is optional and must not prevent application startup.
  }
}

export function captureReactError(error: unknown, componentStack?: string | null) {
  if (dsn) Sentry.captureException(error, { contexts: { react: { componentStack } } });
}
