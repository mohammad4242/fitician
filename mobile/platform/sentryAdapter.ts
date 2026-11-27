import type {
  MobileTelemetryContext,
  MobileTelemetryLevel,
  SentryCompatibleAdapter,
} from "./logging";

export interface SentryClientLike {
  captureException(error: Error, context?: { extra?: MobileTelemetryContext }): unknown;
  captureMessage(
    message: string,
    context?: { extra?: MobileTelemetryContext; level?: MobileTelemetryLevel },
  ): unknown;
}

export function createSentryCompatibleAdapter(client: SentryClientLike): SentryCompatibleAdapter {
  return {
    captureException: (error, context) => {
      // Expected authentication/input/product rejections stay in local diagnostics.
      const status = context.http_status;
      if (typeof status === "number" && status >= 400 && status < 500) return;
      client.captureException(error, { extra: context });
    },
    captureMessage: (message, level, context) => {
      client.captureMessage(message, { extra: context, level });
    },
  };
}
