export type JsonPrimitive = string | number | boolean | null;

export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];

export type JsonObject = {
  readonly [key: string]: JsonValue;
};

export type HttpMethod = "DELETE" | "GET" | "PATCH" | "POST" | "PUT";

export type RequestHeaders = Readonly<Record<string, string>>;

export const CORRELATION_ID_HEADER = "X-Correlation-ID";

export function createCorrelationId(): string {
  const randomUUID = globalThis.crypto?.randomUUID;
  if (typeof randomUUID === "function") {
    return randomUUID.call(globalThis.crypto);
  }
  return `fitician-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export interface CancellationSignal {
  readonly aborted: boolean;
}

export interface TransportRequest {
  readonly path: string;
  readonly method?: HttpMethod;
  readonly headers?: RequestHeaders;
  readonly query?: Readonly<Record<string, boolean | number | string | null | undefined>>;
  readonly body?: JsonValue;
  readonly signal?: CancellationSignal;
}

export interface ApiValidationDetail {
  readonly field?: string;
  readonly code?: string;
  readonly message?: string;
  readonly type?: string;
  readonly loc?: readonly (string | number)[];
  readonly msg?: string;
}

export interface ApiErrorObject {
  readonly code?: string;
  readonly message?: string;
  readonly retryable?: boolean;
  readonly fields?: readonly ApiValidationDetail[];
  readonly meta?: JsonObject;
  readonly request_id?: string;
  readonly requestId?: string;
  readonly [key: string]: unknown;
}

export interface ApiErrorPayload {
  readonly detail?: ApiErrorObject | ApiValidationDetail[] | string | null;
}

export interface ApiErrorOptions {
  readonly validationDetails?: readonly ApiValidationDetail[] | null;
  readonly retryable?: boolean;
  readonly meta?: JsonObject;
  readonly requestId?: string | null;
}

export type TransportErrorKind = "offline" | "network" | "timeout" | "aborted";

const SAFE_CORRELATION_ID = /^[A-Za-z0-9._:-]{1,128}$/u;
const SAFE_META_KEYS = new Set([
  "eligible_packages",
  "entitlement",
  "maximum_weeks",
  "missing_fields",
  "problems",
  "reason_codes",
  "requested_weeks",
  "reset_at",
  "retry_after_seconds",
  "safety_status",
  "current_state",
]);
const DEFAULT_API_ERROR_MESSAGE = "The request could not be completed.";
const STATUS_ERROR_CODES: Readonly<Record<number, string>> = {
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function safeString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function safeCorrelationId(value: unknown): string | null {
  return typeof value === "string" && SAFE_CORRELATION_ID.test(value) ? value : null;
}

function jsonValue(value: unknown): JsonValue | undefined {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") return Number.isFinite(value) ? value : undefined;
  if (Array.isArray(value)) {
    const values = value.map(jsonValue);
    return values.every((item) => item !== undefined)
      ? values as JsonValue[]
      : undefined;
  }
  if (!isRecord(value)) return undefined;
  const result: Record<string, JsonValue> = {};
  for (const [key, item] of Object.entries(value)) {
    const normalized = jsonValue(item);
    if (normalized !== undefined) result[key] = normalized;
  }
  return result as JsonObject;
}

function safeMeta(value: unknown): JsonObject {
  if (!isRecord(value)) return {};
  const result: Record<string, JsonValue> = {};
  for (const [key, item] of Object.entries(value)) {
    if (!SAFE_META_KEYS.has(key)) continue;
    const normalized = jsonValue(item);
    if (normalized !== undefined) result[key] = normalized;
  }
  return result as JsonObject;
}

function normalizedDetails(value: unknown): readonly ApiValidationDetail[] | null {
  if (!Array.isArray(value)) return null;
  const result = value.filter(isRecord).map((item) => {
    const detail: {
      field?: string;
      code?: string;
      message?: string;
      type?: string;
      loc?: readonly (string | number)[];
      msg?: string;
    } = {};
    if (typeof item.field === "string") detail.field = item.field;
    if (typeof item.code === "string") detail.code = item.code;
    if (typeof item.message === "string") detail.message = item.message;
    if (typeof item.type === "string") detail.type = item.type;
    if (Array.isArray(item.loc)) {
      const loc = item.loc.filter(
        (part): part is string | number => typeof part === "string" || typeof part === "number",
      );
      detail.loc = loc;
    }
    if (typeof item.msg === "string") detail.msg = item.msg;
    return detail;
  });
  return result.length > 0 ? result : null;
}

function retryableForStatus(status: number): boolean {
  return status === 408 || status === 425 || status === 429 || status >= 500;
}

function fallbackErrorCode(status: number): string {
  return STATUS_ERROR_CODES[status] ?? (status >= 500 ? "INTERNAL_SERVER_ERROR" : "BAD_REQUEST");
}

export class TransportError extends Error {
  readonly kind: TransportErrorKind;
  readonly requestId: string | null;

  constructor(kind: TransportErrorKind, requestId: string | null = null) {
    super(
      kind === "offline"
        ? "The device is offline."
        : kind === "timeout"
          ? "The request timed out."
          : kind === "aborted"
            ? "The request was cancelled."
            : "The network request failed.",
    );
    this.name = "TransportError";
    this.kind = kind;
    this.requestId = safeCorrelationId(requestId);
  }
}

export class ApiError extends Error {
  readonly status: number;
  readonly details: readonly ApiValidationDetail[] | null;
  readonly validationDetails: readonly ApiValidationDetail[] | null;
  readonly code: string | null;
  readonly retryable: boolean;
  readonly meta: JsonObject;
  readonly requestId: string | null;

  constructor(
    status: number,
    message: string,
    details: readonly ApiValidationDetail[] | null = null,
    code: string | null = null,
    options: ApiErrorOptions = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = options.validationDetails ?? details;
    this.validationDetails = this.details;
    this.code = code;
    this.retryable = options.retryable ?? retryableForStatus(status);
    this.meta = safeMeta(options.meta);
    this.requestId = safeCorrelationId(options.requestId);
  }
}

export interface ParseApiErrorOptions {
  readonly fallbackMessage?: string;
  readonly requestId?: string | null;
}

export function parseApiErrorPayload(
  status: number,
  payload: unknown,
  options: ParseApiErrorOptions = {},
): ApiError {
  const fallbackMessage = options.fallbackMessage ?? DEFAULT_API_ERROR_MESSAGE;
  const hasDetailEnvelope = isRecord(payload) && "detail" in payload;
  const detail = hasDetailEnvelope ? payload.detail : payload;
  if (typeof detail === "string" && hasDetailEnvelope) {
    return new ApiError(status, detail || fallbackMessage, null, null, {
      requestId: options.requestId,
    });
  }
  const details = normalizedDetails(detail);
  if (details !== null && Array.isArray(detail)) {
    return new ApiError(status, "The request contains invalid fields.", details, "VALIDATION_ERROR", {
      requestId: options.requestId,
    });
  }
  if (!isRecord(detail)) {
    return new ApiError(status, fallbackMessage, null, fallbackErrorCode(status), {
      requestId: options.requestId,
    });
  }
  const code = safeString(detail.code);
  const message = safeString(detail.message) ?? fallbackMessage;
  const detailMeta: Record<string, JsonValue> = { ...safeMeta(detail.meta) };
  for (const key of SAFE_META_KEYS) {
    const value = detail[key];
    const normalized = jsonValue(value);
    if (normalized !== undefined && detailMeta[key] === undefined) detailMeta[key] = normalized;
  }
  const fieldDetails = normalizedDetails(detail.fields);
  return new ApiError(status, message, fieldDetails, code, {
    meta: detailMeta as JsonObject,
    requestId: safeCorrelationId(detail.request_id) ?? safeCorrelationId(detail.requestId)
      ?? options.requestId,
    retryable: typeof detail.retryable === "boolean" ? detail.retryable : undefined,
  });
}

export interface Page<TItem> {
  readonly items: readonly TItem[];
  readonly page: number;
  readonly pageSize: number;
  readonly total: number;
}

export interface CursorPage<TItem> {
  readonly items: readonly TItem[];
  readonly next: string | null;
  readonly previous: string | null;
}

export interface BinaryDownload {
  readonly bytes: Uint8Array;
  readonly contentType: string | null;
  readonly filename: string | null;
}

export interface BinaryDownloadRequest extends TransportRequest {
  readonly responseType: "binary";
}

export interface MultipartPart {
  readonly name: string;
  readonly bytes?: Uint8Array;
  readonly value?: string;
  readonly filename?: string;
  readonly contentType?: string;
}

export interface MultipartUploadRequest extends Omit<TransportRequest, "body"> {
  readonly parts: readonly MultipartPart[];
}

export interface FiticianTransport {
  request<TResponse>(request: TransportRequest): Promise<TResponse>;
  download(request: BinaryDownloadRequest): Promise<BinaryDownload>;
  upload<TResponse>(request: MultipartUploadRequest): Promise<TResponse>;
}
