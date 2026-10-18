import {
  createClientRequestTraceContext,
  createGenerationRequestKeys,
  diagnosticWorkflow,
  type ClientRequestTraceContext,
} from "@fitician/core";
import {
  ApiError,
  TransportError,
  parseApiErrorPayload,
  type BinaryDownload,
  type BinaryDownloadRequest,
  type FiticianTransport,
  type MultipartPart,
  type MultipartUploadRequest,
  type TransportRequest,
} from "@fitician/core";
import {
  mobileClientPlatform,
  mobileClientVersion,
  reportMobileClientRequestSpan,
} from "../platform/clientDiagnostics";
import {
  CORRELATION_ID_HEADER,
  createCorrelationId,
  mobileLogger,
  type MobileLogger,
} from "../platform/logging";
import { resolveBackendResourceUrl } from "../config/backendResourceUrl";

export type NativeFetchLike = typeof fetch;

export interface NativeTransportOptions {
  readonly apiBaseUrl: string;
  readonly correlationIdFactory?: () => string;
  readonly fetchImpl?: NativeFetchLike;
  readonly logger?: MobileLogger;
  readonly networkStateProvider?: () => "offline" | "online" | "unknown";
  readonly successSampleRate?: number;
  readonly random?: () => number;
  readonly monotonicNow?: () => number;
  readonly trustedOrigin?: string | null;
}

type PreparedMultipartBody = {
  readonly body: Uint8Array;
  readonly contentType: string;
};

let multipartBoundarySequence = 0;
const abortKinds = new WeakMap<AbortSignal, "timeout" | "aborted">();
const abortListenerCleanup = new WeakMap<AbortSignal, () => void>();

const AUTH_BOOTSTRAP_TIMEOUT_MS = 30_000;
const LONG_REQUEST_TIMEOUT_MS = 180_000;

function needsAuthDeadline(path: string): boolean {
  const pathname = path.split(/[?#]/u)[0];
  return pathname?.startsWith("/api/v1/auth/") === true
    || pathname === "/api/v1/profile/status";
}

async function withRequestDeadline<T>(
  request: TransportRequest,
  requestId: string,
  operation: (signal: AbortSignal) => Promise<T>,
  timeoutMs = LONG_REQUEST_TIMEOUT_MS,
): Promise<T> {
  const callerSignal = nativeAbortSignal(request.signal);
  if (callerSignal?.aborted) throw new TransportError("aborted", requestId);
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  let onAbort: (() => void) | undefined;
  const interrupted = new Promise<never>((_, reject) => {
    onAbort = () => {
      abortKinds.set(controller.signal, "aborted");
      reject(new TransportError("aborted", requestId));
      controller.abort();
    };
    callerSignal?.addEventListener("abort", onAbort, { once: true });
    timer = setTimeout(() => {
      // Reject before aborting so native AbortError does not hide the timeout.
      abortKinds.set(controller.signal, "timeout");
      reject(new TransportError("timeout", requestId));
      controller.abort();
    }, timeoutMs);
  });
  try {
    return await Promise.race([operation(controller.signal), interrupted]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
    if (onAbort !== undefined) callerSignal?.removeEventListener("abort", onAbort);
    abortListenerCleanup.get(controller.signal)?.();
    abortListenerCleanup.delete(controller.signal);
    abortKinds.delete(controller.signal);
  }
}

function requestUrl(baseUrl: string, path: string): string {
  if (/^https?:\/\//i.test(path)) {
    throw new Error("Native API request paths must be relative to the configured backend");
  }
  return resolveBackendResourceUrl(path, baseUrl);
}

function requestBody(body: TransportRequest["body"]): string | undefined {
  return body === undefined ? undefined : JSON.stringify(body);
}

function nativeAbortSignal(signal: TransportRequest["signal"]): AbortSignal | undefined {
  if (signal === undefined || typeof AbortSignal === "undefined") return undefined;
  return signal instanceof AbortSignal ? signal : undefined;
}

function requestHeaders(
  headers: TransportRequest["headers"],
  trustedOrigin: string | null | undefined,
  correlationId: string,
  contentType: string | null,
  trace: ClientRequestTraceContext | null,
): Headers {
  const result = new Headers(headers);
  if (trustedOrigin !== undefined && trustedOrigin !== null && !result.has("Origin")) {
    result.set("Origin", trustedOrigin);
  }
  if (!result.has("Content-Type")) {
    result.set("Content-Type", contentType ?? "application/json");
  }
  if (!result.has(CORRELATION_ID_HEADER)) {
    result.set(CORRELATION_ID_HEADER, correlationId);
  }
  if (trace !== null) result.set("traceparent", trace.traceparent);
  result.set("X-Fitician-Platform", mobileClientPlatform());
  const version = mobileClientVersion();
  if (version !== null) result.set("X-Fitician-Version", version);
  return result;
}

function requestInit(
  request: TransportRequest,
  body: BodyInit | undefined,
  trustedOrigin: string | null | undefined,
  correlationId: string,
  trace: ClientRequestTraceContext | null,
  contentType: string | null = null,
): RequestInit {
  return {
    body,
    headers: requestHeaders(request.headers, trustedOrigin, correlationId, contentType, trace),
    method: request.method ?? "GET",
    signal: nativeAbortSignal(request.signal),
  };
}

async function throwForError(response: Response): Promise<never> {
  const rawBody = await response.text().catch(() => "");
  let payload: unknown = null;
  if (rawBody.trim().length > 0) {
    try {
      payload = JSON.parse(rawBody) as unknown;
    } catch {
      payload = null;
    }
  }
  throw parseApiErrorPayload(response.status, payload, {
    requestId: response.headers.get(CORRELATION_ID_HEADER),
  });
}

async function ensureOk(response: Response): Promise<Response> {
  if (!response.ok) {
    await throwForError(response);
  }
  return response;
}

function normalizeFetchError(
  error: unknown,
  requestId: string,
  networkState: "offline" | "online" | "unknown",
): unknown {
  if (error instanceof ApiError || error instanceof TransportError) return error;
  if (error instanceof Error && error.name === "AbortError") {
    return new TransportError("aborted", requestId);
  }
  if (networkState === "offline") return new TransportError("offline", requestId);
  if (
    error instanceof Error
    && (error.name === "TimeoutError" || /timed? ?out|timeout/iu.test(error.message))
  ) {
    return new TransportError("timeout", requestId);
  }
  if (
    error instanceof TypeError
    || (error instanceof Error && /network|connection|fetch failed|dns/iu.test(error.message))
  ) {
    return new TransportError("network", requestId);
  }
  return error;
}

function responseFilename(response: Response): string | null {
  const contentDisposition = response.headers.get("Content-Disposition");
  if (!contentDisposition) {
    return null;
  }
  const match = /filename\*=(?:UTF-8'')?([^;]+)|filename="?([^";]+)"?/i.exec(
    contentDisposition,
  );
  const filename = match?.[1] ?? match?.[2];
  if (!filename) {
    return null;
  }
  try {
    return decodeURIComponent(filename);
  } catch {
    return filename;
  }
}

function multipartQuotedValue(value: string): string {
  return value.replace(/["\r\n]/gu, "_");
}

function joinBytes(chunks: readonly Uint8Array[]): Uint8Array {
  const result = new Uint8Array(chunks.reduce((total, chunk) => total + chunk.byteLength, 0));
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return result;
}

function utf8Bytes(value: string): Uint8Array {
  const bytes: number[] = [];
  for (const character of value) {
    const codePoint = character.codePointAt(0) ?? 0xfffd;
    if (codePoint <= 0x7f) {
      bytes.push(codePoint);
    } else if (codePoint <= 0x7ff) {
      bytes.push(0xc0 | (codePoint >> 6), 0x80 | (codePoint & 0x3f));
    } else if (codePoint <= 0xffff) {
      bytes.push(
        0xe0 | (codePoint >> 12),
        0x80 | ((codePoint >> 6) & 0x3f),
        0x80 | (codePoint & 0x3f),
      );
    } else {
      bytes.push(
        0xf0 | (codePoint >> 18),
        0x80 | ((codePoint >> 12) & 0x3f),
        0x80 | ((codePoint >> 6) & 0x3f),
        0x80 | (codePoint & 0x3f),
      );
    }
  }
  return Uint8Array.from(bytes);
}

function multipartBody(parts: readonly MultipartPart[]): PreparedMultipartBody {
  const boundary = `----FiticianBoundary${Date.now().toString(36)}${multipartBoundarySequence++}`;
  const chunks: Uint8Array[] = [];
  for (const part of parts) {
    const disposition = `Content-Disposition: form-data; name="${multipartQuotedValue(part.name)}"`;
    chunks.push(utf8Bytes(`--${boundary}\r\n`));
    if (part.bytes !== undefined) {
      const filename = multipartQuotedValue(part.filename ?? "upload.bin");
      const contentType = part.contentType ?? "application/octet-stream";
      chunks.push(utf8Bytes(
        `${disposition}; filename="${filename}"\r\nContent-Type: ${contentType}\r\n\r\n`,
      ));
      chunks.push(part.bytes as Uint8Array);
    } else {
      chunks.push(utf8Bytes(`${disposition}\r\n\r\n${part.value ?? ""}`));
    }
    chunks.push(utf8Bytes("\r\n"));
  }
  chunks.push(utf8Bytes(`--${boundary}--\r\n`));
  return {
    body: joinBytes(chunks),
    contentType: `multipart/form-data; boundary=${boundary}`,
  };
}

export function createNativeTransport(options: NativeTransportOptions): FiticianTransport {
  const fetchRequest = options.fetchImpl ?? ((input, init) => globalThis.fetch(input, init));
  const logger = options.logger ?? mobileLogger;
  const correlationIdFactory = options.correlationIdFactory ?? createCorrelationId;
  const networkStateProvider = options.networkStateProvider ?? (() => "unknown" as const);
  const successSampleRate = Number.isFinite(options.successSampleRate)
    ? Math.min(1, Math.max(0, options.successSampleRate!))
    : 0.1;
  const random = options.random ?? Math.random;
  const monotonicNow = options.monotonicNow ?? (() => globalThis.performance?.now?.() ?? 0);

  const generationKeys = createGenerationRequestKeys();

  async function send(
    request: TransportRequest,
    body: BodyInit | undefined,
    operation: "request" | "download" | "upload",
    contentType: string | null = null,
    correlationId = correlationIdFactory(),
  ): Promise<Response> {
    const suppliedCorrelationId = request.headers === undefined
      ? null
      : new Headers(request.headers).get(CORRELATION_ID_HEADER);
    const requestId = suppliedCorrelationId ?? correlationId;
    const telemetryPath = request.path.split(/[?#]/u)[0] ?? "";
    const diagnosticRequest = telemetryPath.startsWith("/api/v1/diagnostics/")
      || telemetryPath.startsWith("/api/v1/admin/diagnostics");
    const suppliedTraceparent = request.headers === undefined
      ? null
      : new Headers(request.headers).get("traceparent");
    const trace = diagnosticRequest
      ? null
      : createClientRequestTraceContext(suppliedTraceparent);
    const sampledSuccess = random() < successSampleRate;
    const startedAt = monotonicNow();
    let response: Response | undefined;
    if (request.path.startsWith("/api/v1/auth/")) generationKeys.clear();
    const init = requestInit(request, body, options.trustedOrigin, requestId, trace, contentType);
    init.headers = generationKeys.headers(request.path, request.method, new Headers(init.headers));
    const signal = nativeAbortSignal(request.signal);
    let transportFailureReported = false;
    const reportTransportFailure = (transportKind: "network" | "timeout" | "aborted" | "offline" | "unknown") => {
      if (trace === null || transportFailureReported) return;
      transportFailureReported = true;
      reportMobileClientRequestSpan({
        operation: diagnosticWorkflow(request.path, operation),
        requestId,
        traceId: trace.traceId,
        spanId: trace.spanId,
        ...(trace.parentSpanId ? { parentSpanId: trace.parentSpanId } : {}),
        terminalStage: "transport_failed",
        transportKind,
        durationMs: Math.max(0, monotonicNow() - startedAt),
        ...(response ? { httpStatus: response.status } : {}),
        shouldRecord: true,
      });
    };
    if (signal !== undefined && trace !== null) {
      const onSignalAbort = () => reportTransportFailure(abortKinds.get(signal) ?? "aborted");
      signal.addEventListener("abort", onSignalAbort, { once: true });
      abortListenerCleanup.set(signal, () => signal.removeEventListener("abort", onSignalAbort));
    }
    try {
      response = await fetchRequest(
        requestUrl(options.apiBaseUrl, request.path),
        init,
      );
      if (trace !== null) {
        reportMobileClientRequestSpan({
          operation: diagnosticWorkflow(request.path, operation),
          requestId,
          traceId: trace.traceId,
          spanId: trace.spanId,
          ...(trace.parentSpanId ? { parentSpanId: trace.parentSpanId } : {}),
          terminalStage: "response_received",
          durationMs: Math.max(0, monotonicNow() - startedAt),
          httpStatus: response.status,
          shouldRecord: !response.ok || sampledSuccess,
        });
      }
      generationKeys.completed(request.path, response.status, new Headers(init.headers).get("Idempotency-Key"));
      await ensureOk(response);
      const isDiagnosticsRequest = diagnosticRequest;
      if (!isDiagnosticsRequest) logger.captureMessage("native_request_completed", "info", {
        correlation_id: correlationId,
        duration_ms: Math.max(0, monotonicNow() - startedAt),
        http_status: response.status,
        method: request.method ?? "GET",
        operation,
      });
      return response;
    } catch (error) {
      const isDiagnosticsRequest = diagnosticRequest;
      const signalAbortKind = signal === undefined ? undefined : abortKinds.get(signal);
      const normalized = signalAbortKind
        ? new TransportError(signalAbortKind, requestId)
        : normalizeFetchError(error, requestId, networkStateProvider());
      if (response === undefined) {
        reportTransportFailure(normalized instanceof TransportError ? normalized.kind : "unknown");
      }
      if (!isDiagnosticsRequest) logger.captureException("native_request_failed", error, {
        component: "NativeTransport",
        correlation_id: correlationId,
        ...(trace ? {
          operation_id: trace.traceId,
          trace_id: trace.traceId,
          span_id: trace.spanId,
          ...(trace.parentSpanId ? { parent_span_id: trace.parentSpanId } : {}),
        } : {}),
        duration_ms: Math.max(0, monotonicNow() - startedAt),
        error_code: "API_REQUEST_FAILED",
        http_status: response?.status ?? null,
        method: request.method ?? "GET",
        operation: diagnosticWorkflow(request.path, operation),
        stage: "failed",
      });
      throw normalized;
    }
  }

  return {
    async request<TResponse>(request: TransportRequest): Promise<TResponse> {
      const readResponse = async (boundedRequest: TransportRequest, requestId?: string) => {
        const response = await send(
          boundedRequest, requestBody(request.body), "request", null, requestId,
        );
        if (response.status === 204) return undefined as TResponse;
        return (await response.json()) as TResponse;
      };
      const requestId = correlationIdFactory();
      return withRequestDeadline(request, requestId, (signal) => (
        readResponse({ ...request, signal }, requestId)
      ), needsAuthDeadline(request.path) ? AUTH_BOOTSTRAP_TIMEOUT_MS : LONG_REQUEST_TIMEOUT_MS);
    },

    async download(request: BinaryDownloadRequest): Promise<BinaryDownload> {
      const requestId = correlationIdFactory();
      return withRequestDeadline(request, requestId, async (signal) => {
        const response = await send({ ...request, signal }, requestBody(request.body), "download", null, requestId);
        return {
          bytes: new Uint8Array(await response.arrayBuffer()),
          contentType: response.headers.get("Content-Type"),
          filename: responseFilename(response),
        };
      });
    },

    async upload<TResponse>(request: MultipartUploadRequest): Promise<TResponse> {
      const prepared = multipartBody(request.parts);
      const requestId = correlationIdFactory();
      return withRequestDeadline(request, requestId, async (signal) => {
        const response = await send(
          { ...request, signal },
          prepared.body as unknown as BodyInit,
          "upload",
          prepared.contentType,
          requestId,
        );
        if (response.status === 204) return undefined as TResponse;
        return (await response.json()) as TResponse;
      });
    },
  };
}
