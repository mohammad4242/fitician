import * as Sentry from "@sentry/react-native";
import Constants from "expo-constants";
import { diagnosticsRelease } from "../config/diagnosticsRelease";
import { configureMobileTelemetry } from "./logging";
import { createSentryCompatibleAdapter } from "./sentryAdapter";
import { sanitizeSentryEvent } from "./sentryPrivacy";

const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN;
const release = diagnosticsRelease(
  Constants.expoConfig?.extra?.diagnosticBuildCommit,
  Constants.nativeBuildVersion,
);
if (dsn) {
  try {
  Sentry.init({
    dsn,
    ...(release.release ? { release: release.release } : {}),
    ...(release.dist ? { dist: release.dist } : {}),
    environment: process.env.EXPO_PUBLIC_SENTRY_ENVIRONMENT || "development",
    sendDefaultPii: false,
    maxBreadcrumbs: 0,
    sampleRate: 1,
    tracesSampleRate: 0,
    enableAutoSessionTracking: false,
    enableMemoryIntrospection: false,
    attachScreenshot: false,
    attachViewHierarchy: false,
    enableCaptureFailedRequests: false,
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
