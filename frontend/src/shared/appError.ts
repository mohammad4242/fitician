import { resolveAppError } from "@fitician/core";
import type {
  ErrorAudienceInput,
  ErrorContext,
  ErrorLocale,
  ErrorNetworkState,
  ResolvedAppError,
} from "@fitician/core";

export interface WebErrorOptions {
  readonly audience: ErrorAudienceInput;
  readonly context: ErrorContext;
  readonly locale?: ErrorLocale;
  readonly networkState?: ErrorNetworkState;
}

export function resolveWebAppError(
  error: unknown,
  options: WebErrorOptions,
): ResolvedAppError {
  return resolveAppError(error, {
    audience: options.audience,
    context: options.context,
    locale: options.locale ?? "fa",
    networkState: options.networkState,
  });
}

export function webErrorMessage(
  error: unknown,
  fallback: string,
  options: WebErrorOptions,
): string {
  if (error === null || error === undefined) return fallback;
  return resolveWebAppError(error, options).message;
}
