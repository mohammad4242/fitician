import {
  ApiError,
  TransportError,
  resolveAppError,
  type ErrorAudienceInput,
  type ErrorContext,
  type ErrorLocale,
  type ResolvedAppError,
} from "@fitician/core";
import type { QueryObserverResult } from "@tanstack/react-query";

import type { ConnectivityStatus } from "../platform/connectivity";

export type MobileQueryResult<TData> = Pick<
  QueryObserverResult<TData, unknown>,
  "data" | "error" | "isError" | "isFetching" | "isPending" | "isStale"
>;

export type MobileStateErrorKind = "validation" | "permission" | "server";

export type MobileStateError = {
  readonly kind: MobileStateErrorKind;
  readonly message: string;
  readonly status: number | null;
  readonly code: string | null;
  readonly retryable: boolean;
  readonly presentation: ResolvedAppError;
};

export type MobileViewState<TData> =
  | { readonly status: "loading" }
  | { readonly status: "empty"; readonly data: TData; readonly isStale: boolean }
  | { readonly status: "ready"; readonly data: TData }
  | { readonly status: "stale"; readonly data: TData }
  | { readonly status: "offline"; readonly data?: TData; readonly isStale?: boolean }
  | {
      readonly status: "error";
      readonly error: MobileStateError;
      readonly data?: TData;
      readonly isStale?: boolean;
    };

export interface MobileViewStateOptions<TData> {
  readonly audience?: ErrorAudienceInput;
  readonly context?: ErrorContext;
  readonly connectivityStatus?: ConnectivityStatus;
  readonly isEmpty?: (data: TData) => boolean;
  readonly locale?: ErrorLocale;
}

function isNetworkFailure(error: unknown): boolean {
  if (error instanceof TransportError) return error.kind === "offline";
  if (error instanceof ApiError || error === null || typeof error !== "object") return false;
  const candidate = error as { readonly name?: unknown; readonly message?: unknown };
  return candidate.name !== "AbortError" && typeof candidate.message === "string"
    && /offline/i.test(candidate.message);
}

function isAborted(error: unknown): boolean {
  return error instanceof TransportError
    ? error.kind === "aborted"
    : typeof error === "object"
      && error !== null
      && (error as { readonly name?: unknown }).name === "AbortError";
}

function isDefaultEmpty<TData>(data: TData): boolean {
  return data === null || (Array.isArray(data) && data.length === 0);
}

export interface MobileErrorPresentationOptions {
  readonly audience?: ErrorAudienceInput;
  readonly context?: ErrorContext;
  readonly connectivityStatus?: ConnectivityStatus;
  readonly locale?: ErrorLocale;
}

export function classifyMobileStateError(
  error: unknown,
  options: MobileErrorPresentationOptions = {},
): MobileStateError {
  const presentation = resolveAppError(error, {
    audience: options.audience ?? "member",
    context: options.context ?? "generic",
    locale: options.locale ?? "fa",
    networkState: options.connectivityStatus ?? "unknown",
  });
  const kind: MobileStateErrorKind =
    presentation.status === 400
    || presentation.status === 409
    || presentation.status === 422
    || presentation.fieldErrors.length > 0
      ? "validation"
      : presentation.status === 401 || presentation.status === 403
        ? "permission"
        : "server";
  return {
    code: presentation.code,
    kind,
    message: presentation.message,
    presentation,
    retryable: presentation.retryable,
    status: presentation.status,
  };
}

export function mobileRequestErrorMessage(
  error: unknown,
  fallback: string,
  options: MobileErrorPresentationOptions = {},
): string {
  if (error === null || error === undefined) return fallback;
  return classifyMobileStateError(error, options).message;
}

export function getMobileViewState<TData>(
  result: MobileQueryResult<TData>,
  options: MobileViewStateOptions<TData> = {},
): MobileViewState<TData> {
  const hasData = result.data !== undefined;
  const isOffline =
    options.connectivityStatus === "offline" || (result.isError && isNetworkFailure(result.error));

  if (isOffline) {
    return hasData
      ? { data: result.data, isStale: result.isStale, status: "offline" }
      : { status: "offline" };
  }
  if (result.isError && isAborted(result.error)) {
    return hasData
      ? { data: result.data as TData, status: "stale" }
      : { status: "loading" };
  }
  if (result.isPending && !hasData) {
    return { status: "loading" };
  }
  if (result.isError) {
    return {
      ...(hasData ? { data: result.data, isStale: true } : {}),
      error: classifyMobileStateError(result.error, options),
      status: "error",
    };
  }
  if (!hasData) {
    return { status: "loading" };
  }

  const data = result.data as TData;
  if ((options.isEmpty ?? isDefaultEmpty)(data)) {
    return { data, isStale: result.isStale || result.isFetching, status: "empty" };
  }
  if (result.isFetching || result.isStale) {
    return { data, status: "stale" };
  }
  return { data, status: "ready" };
}
