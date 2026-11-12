import * as Sentry from "@sentry/react-native";
import { configureMobileTelemetry } from "./logging";
import { createSentryCompatibleAdapter } from "./sentryAdapter";
import { sanitizeSentryEvent } from "./sentryPrivacy";

const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN;
if (dsn) {
  try {
  Sentry.init({
    dsn,
    environment: process.env.EXPO_PUBLIC_SENTRY_ENVIRONMENT || "development",
    sendDefaultPii: false,
    maxBreadcrumbs: 0,
    sampleRate: 1,
    tracesSampleRate: 0,
    enableAutoSessionTracking: false,
    enableNative: true,
    enableNativeCrashHandling: true,
    beforeSend: sanitizeSentryEvent,
    beforeSendTransaction: sanitizeSentryEvent,
    beforeBreadcrumb: () => null,
    enableLogs: false,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
    integrations: defaults => defaults.filter(integration => ["ReactNativeErrorHandlers", "NativeLinkedErrors", "Dedupe", "DebugSymbolicator", "RewriteFrames"].includes(integration.name)),
  });
  configureMobileTelemetry(createSentryCompatibleAdapter(Sentry));
  } catch {
    // Invalid observability configuration must not prevent application startup.
  }
}
