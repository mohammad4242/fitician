import { captureReactError } from "./sentry";

export const rootErrorHandlers = {
  onCaughtError(error: unknown, info: { componentStack?: string | null }) {
    captureReactError(error, info.componentStack, "caught");
    console.error("Fitician CLIENT_RENDER_ERROR");
  },
  onUncaughtError(error: unknown, info: { componentStack?: string | null }) {
    captureReactError(error, info.componentStack, "uncaught");
    console.error("Fitician CLIENT_RENDER_ERROR");
  },
};
