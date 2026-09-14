import {
  ApiError,
  TransportError,
  type ApiValidationDetail,
} from "../transport";
import { ERROR_CATALOG, ERROR_FIELD_LABELS } from "./catalog";
import type {
  ErrorAudience,
  ErrorAudienceInput,
  ErrorCatalogEntry,
  ErrorLocale,
  ErrorNetworkState,
  ErrorSeverity,
  LocalizedErrorCopy,
  ResolveAppErrorOptions,
  ResolvedAppError,
  ResolvedFieldError,
} from "./types";

const SAFE_CODE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$/u;

const statusCode: Readonly<Record<number, string>> = {
  400: "BAD_REQUEST",
  401: "UNAUTHORIZED",
  403: "FORBIDDEN",
  404: "NOT_FOUND",
  409: "CONFLICT",
  422: "VALIDATION_ERROR",
  429: "RATE_LIMITED",
  500: "INTERNAL_SERVER_ERROR",
  502: "BAD_GATEWAY",
  503: "SERVICE_UNAVAILABLE",
};

const genericCopy: Readonly<Record<string, ErrorCatalogEntry>> = {
  BAD_REQUEST: ERROR_CATALOG.BAD_REQUEST,
  UNAUTHORIZED: ERROR_CATALOG.UNAUTHORIZED,
  FORBIDDEN: ERROR_CATALOG.FORBIDDEN,
  NOT_FOUND: ERROR_CATALOG.NOT_FOUND,
  CONFLICT: ERROR_CATALOG.CONFLICT,
  VALIDATION_ERROR: ERROR_CATALOG.VALIDATION_ERROR,
  RATE_LIMITED: ERROR_CATALOG.RATE_LIMITED,
  INTERNAL_SERVER_ERROR: ERROR_CATALOG.INTERNAL_SERVER_ERROR,
  BAD_GATEWAY: ERROR_CATALOG.BAD_GATEWAY,
  SERVICE_UNAVAILABLE: ERROR_CATALOG.SERVICE_UNAVAILABLE,
};

function normalizeAudience(audience: ErrorAudienceInput): ErrorAudience {
  return audience === "doctor" ? "physician" : audience;
}

function copyFor(
  entry: ErrorCatalogEntry,
  audience: ErrorAudience,
  locale: ErrorLocale,
): { title: string; message: string; action: string | null } {
  const override = entry.audiences?.[audience];
  const localized = (value: LocalizedErrorCopy | undefined): string | null => (
    value === undefined ? null : value[locale]
  );
  return {
    title: localized(override?.title) ?? entry.title[locale],
    message: localized(override?.message) ?? entry.message[locale],
    action: localized(override?.action) ?? localized(entry.action),
  };
}

function safeCode(value: string | null | undefined): string | null {
  return typeof value === "string" && SAFE_CODE.test(value) ? value : null;
}

function fieldName(detail: ApiValidationDetail): string | null {
  if (typeof detail.field === "string" && detail.field.length > 0) return detail.field;
  const loc = detail.loc?.filter((part) => typeof part === "string" || typeof part === "number") ?? [];
  const fields = loc.filter((part) => part !== "body" && part !== "query" && part !== "path");
  return fields.length > 0 ? fields.join(".") : null;
}

function localizedFieldMessage(
  detail: ApiValidationDetail,
  field: string | null,
  locale: ErrorLocale,
): string {
  const label = ERROR_FIELD_LABELS[field ?? ""]?.[locale]
    ?? (field ?? (locale === "fa" ? "این فیلد" : "This field"));
  const detailCode = (detail.code ?? detail.type ?? "").toLowerCase();
  if (detailCode.includes("missing") || detailCode === "required") {
    return locale === "fa" ? `${label} وارد نشده است.` : `${label} is required.`;
  }
  if (
    detailCode.includes("greater")
    || detailCode.includes("less")
    || detailCode.includes("range")
    || detailCode.includes("between")
  ) {
    return locale === "fa" ? `${label} باید در بازه مجاز باشد.` : `${label} must be within the supported range.`;
  }
  return locale === "fa" ? `${label} معتبر نیست.` : `${label} is invalid.`;
}

function fieldErrors(
  details: readonly ApiValidationDetail[] | null,
  audience: ErrorAudience,
  locale: ErrorLocale,
): readonly ResolvedFieldError[] {
  return (details ?? []).map((detail) => {
    const field = fieldName(detail);
    const code = safeCode(detail.code ?? detail.type) ?? "invalid";
    const rawMessage = detail.message ?? detail.msg;
    return {
      field,
      code,
      message: audience === "admin" && rawMessage ? rawMessage : localizedFieldMessage(detail, field, locale),
    };
  });
}

function runtimeErrorKind(
  error: unknown,
  networkState: ErrorNetworkState,
): TransportError | null {
  if (error instanceof TransportError) return error;
  const details = runtimeErrorDetails(error);
  if (details.name === "AbortError") return new TransportError("aborted");
  if (networkState === "offline") return new TransportError("offline");
  if (details.name === "TimeoutError" || /timed? ?out|timeout/i.test(details.message)) {
    return new TransportError("timeout");
  }
  if (
    error instanceof TypeError
    || /network|connection|fetch failed|dns/i.test(details.message)
  ) {
    return new TransportError("network");
  }
  return null;
}

function runtimeErrorDetails(error: unknown): { readonly name: string; readonly message: string } {
  if (error instanceof Error) {
    return { name: error.name, message: error.message };
  }
  if (typeof error === "object" && error !== null) {
    const candidate = error as { readonly name?: unknown; readonly message?: unknown };
    return {
      name: typeof candidate.name === "string" ? candidate.name : "",
      message: typeof candidate.message === "string" ? candidate.message : "",
    };
  }
  return { name: "", message: "" };
}

function runtimeResolution(
  error: TransportError,
): { code: string; entry: ErrorCatalogEntry; severity: ErrorSeverity; retryable: boolean } {
  const code = error.kind === "offline"
    ? "OFFLINE"
    : error.kind === "timeout"
      ? "REQUEST_TIMEOUT"
      : error.kind === "aborted"
        ? "REQUEST_ABORTED"
        : "NETWORK_ERROR";
  return {
    code,
    entry: ERROR_CATALOG[code] ?? ERROR_CATALOG.NETWORK_ERROR,
    severity: error.kind === "aborted" ? "silent" : "warning",
    retryable: error.kind !== "aborted",
  };
}

function fallbackEntry(code: string, status: number | null): ErrorCatalogEntry {
  return ERROR_CATALOG[code] ?? genericCopy[code] ?? (
    status !== null && status >= 500
      ? ERROR_CATALOG.INTERNAL_SERVER_ERROR
      : ERROR_CATALOG.VALIDATION_ERROR
  );
}

function statusSeverity(status: number | null, retryable: boolean): ErrorSeverity {
  if (status === 429 || (retryable && status !== null && status >= 500)) return "warning";
  return "error";
}

function resolveApiError(
  error: ApiError,
  options: ResolveAppErrorOptions,
  audience: ErrorAudience,
): ResolvedAppError {
  const code = safeCode(error.code) ?? statusCode[error.status] ?? "HTTP_ERROR";
  const entry = fallbackEntry(code, error.status);
  const copy = copyFor(entry, audience, options.locale);
  const resolvedFields = fieldErrors(error.validationDetails, audience, options.locale);
  const message = resolvedFields.length > 0 && code === "VALIDATION_ERROR"
    ? resolvedFields.map((item) => item.message).join(options.locale === "fa" ? " " : " ")
    : copy.message;
  return {
    title: copy.title,
    message,
    action: copy.action,
    severity: statusSeverity(error.status, error.retryable),
    retryable: error.retryable,
    code,
    status: error.status,
    requestId: error.requestId,
    fieldErrors: resolvedFields,
    meta: error.meta,
    showTechnicalDetails: audience === "admin",
  };
}

export function resolveAppError(
  error: unknown,
  options: ResolveAppErrorOptions,
): ResolvedAppError {
  const audience = normalizeAudience(options.audience);
  if (error instanceof ApiError) return resolveApiError(error, options, audience);

  const runtime = runtimeErrorKind(error, options.networkState ?? "unknown");
  if (runtime !== null) {
    const resolution = runtimeResolution(runtime);
    const copy = copyFor(resolution.entry, audience, options.locale);
    return {
      title: copy.title,
      message: copy.message,
      action: copy.action,
      severity: resolution.severity,
      retryable: resolution.retryable,
      code: resolution.code,
      status: null,
      requestId: runtime.requestId,
      fieldErrors: [],
      meta: {},
      showTechnicalDetails: audience === "admin",
    };
  }

  const entry = ERROR_CATALOG.UNKNOWN_ERROR ?? ERROR_CATALOG.INTERNAL_SERVER_ERROR;
  const copy = copyFor(entry, audience, options.locale);
  return {
    title: copy.title,
    message: copy.message,
    action: copy.action,
    severity: "error",
    retryable: true,
    code: "UNKNOWN_ERROR",
    status: null,
    requestId: null,
    fieldErrors: [],
    meta: {},
    showTechnicalDetails: audience === "admin",
  };
}
