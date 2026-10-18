import {
  createClientRequestTraceContext,
  createGenerationRequestKeys,
  diagnosticWorkflow,
} from "@fitician/core";
import {
  ApiError,
  CORRELATION_ID_HEADER,
  TransportError,
  createCorrelationId,
  parseApiErrorPayload,
  type ClientRequestTraceContext,
  type BinaryDownload,
  type BinaryDownloadRequest,
  type FiticianTransport,
  type MultipartPart,
  type MultipartUploadRequest,
  type TransportRequest,
} from "@fitician/core";

import {
  reportWebClientRequestSpan,
  webClientPlatform,
  webClientVersion,
} from "./clientDiagnostics";

export type FetchLike = typeof fetch;

export interface WebFiticianTransport extends FiticianTransport {
  uploadFormData<TResponse>(
    request: Omit<MultipartUploadRequest, "parts"> & { formData: FormData },
  ): Promise<TResponse>;
}

export interface WebTransportOptions {
  readonly correlationIdFactory?: () => string;
  readonly successSampleRate?: number;
  readonly random?: () => number;
  readonly monotonicNow?: () => number;
}

function requestBody(body: TransportRequest["body"]): BodyInit | undefined {
  return body === undefined ? undefined : JSON.stringify(body);
}

function requestHeaders(
  headers: TransportRequest["headers"],
  isMultipart: boolean,
  correlationId: string,
  trace: ClientRequestTraceContext | null,
): Headers {
  const result = new Headers(headers);
  if (!isMultipart && !result.has("Content-Type")) {
    result.set("Content-Type", "application/json");
  }
  if (!result.has(CORRELATION_ID_HEADER)) {
    result.set(CORRELATION_ID_HEADER, correlationId);
  }
  if (trace !== null) result.set("traceparent", trace.traceparent);
  result.set("X-Fitician-Platform", webClientPlatform());
  const version = webClientVersion();
  if (version !== null) result.set("X-Fitician-Version", version);
  return result;
}

function requestInit(
  request: TransportRequest,
  body: BodyInit | undefined,
  correlationId: string,
  trace: ClientRequestTraceContext | null,
  isMultipart = false,
): RequestInit {
  return {
    body,
    credentials: "include",
    headers: requestHeaders(request.headers, isMultipart, correlationId, trace),
    method: request.method ?? "GET",
    signal: request.signal as AbortSignal | undefined,
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

function isOffline(): boolean {
  return typeof navigator !== "undefined" && navigator.onLine === false;
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

function normalizeFetchError(error: unknown, requestId: string): unknown {
  if (error instanceof ApiError || error instanceof TransportError) return error;
  const details = runtimeErrorDetails(error);
  if (details.name === "AbortError") {
    return new TransportError("aborted", requestId);
  }
  if (isOffline()) return new TransportError("offline", requestId);
  if (
    details.name === "TimeoutError"
    || /timed? ?out|timeout/iu.test(details.message)
  ) {
    return new TransportError("timeout", requestId);
  }
  if (
    error instanceof TypeError
    || /network|connection|fetch failed|dns/iu.test(details.message)
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

function bytesToBlob(part: MultipartPart): Blob {
  return new Blob([part.bytes?.buffer as ArrayBuffer], {
    type: part.contentType ?? "application/octet-stream",
  });
}

function multipartFormData(parts: readonly MultipartPart[]): FormData {
  const formData = new FormData();
  for (const part of parts) {
    if (part.bytes !== undefined) {
      const blob = bytesToBlob(part);
      if (part.filename !== undefined) {
        formData.append(part.name, blob, part.filename);
      } else {
        formData.append(part.name, blob);
      }
    } else {
      formData.append(part.name, part.value ?? "");
    }
  }
  return formData;
}

export async function formDataToMultipart(formData: FormData): Promise<MultipartPart[]> {
  const entries: Array<[string, FormDataEntryValue]> = [];
  formData.forEach((value, name) => entries.push([name, value]));
  return Promise.all(
    entries.map(async ([name, value]) => {
      if (typeof value === "string") {
        return { name, value };
      }
      return {
        bytes: new Uint8Array(await value.arrayBuffer()),
        contentType: value.type || undefined,
        filename: value.name,
        name,
      };
    }),
  );
}

export function createWebTransport(
  fetchImpl?: FetchLike,
  options: WebTransportOptions = {},
): WebFiticianTransport {
  const fetchRequest: FetchLike = fetchImpl ?? ((input, init) => globalThis.fetch(input, init));
  const correlationIdFactory = options.correlationIdFactory ?? createCorrelationId;
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
    isMultipart = false,
  ): Promise<Response> {
    const suppliedCorrelationId = request.headers === undefined
      ? null
      : new Headers(request.headers).get(CORRELATION_ID_HEADER);
    const correlationId = suppliedCorrelationId ?? correlationIdFactory();
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
    if (request.path.startsWith("/api/v1/auth/")) generationKeys.clear();
    const init = requestInit(request, body, correlationId, trace, isMultipart);
    init.headers = generationKeys.headers(request.path, request.method, new Headers(init.headers));
    let response: Response | undefined;
    try {
      response = await fetchRequest(
        request.path,
        init,
      );
      if (trace !== null) {
        const durationMs = Math.max(0, monotonicNow() - startedAt);
        reportWebClientRequestSpan({
          operation: diagnosticWorkflow(request.path, operation),
          requestId: correlationId,
          traceId: trace.traceId,
          spanId: trace.spanId,
          ...(trace.parentSpanId ? { parentSpanId: trace.parentSpanId } : {}),
          terminalStage: "response_received",
          durationMs,
          httpStatus: response.status,
          shouldRecord: !response.ok || sampledSuccess,
        });
      }
      generationKeys.completed(request.path, response.status, new Headers(init.headers).get("Idempotency-Key"));
      return await ensureOk(response);
    } catch (error) {
      const normalized = normalizeFetchError(error, correlationId);
      if (trace !== null && response === undefined) {
        // A resolved HTTP response was already recorded before status/body handling.
        // Only failures before receiving response headers end as transport_failed.
        reportWebClientRequestSpan({
          operation: diagnosticWorkflow(request.path, operation),
          requestId: correlationId,
          traceId: trace.traceId,
          spanId: trace.spanId,
          ...(trace.parentSpanId ? { parentSpanId: trace.parentSpanId } : {}),
          terminalStage: "transport_failed",
          transportKind: normalized instanceof TransportError ? normalized.kind : "unknown",
          durationMs: Math.max(0, monotonicNow() - startedAt),
          shouldRecord: true,
        });
      }
      throw normalized;
    }
  }

  return {
    async request<TResponse>(request: TransportRequest): Promise<TResponse> {
      const response = await send(request, requestBody(request.body), "request");
      if (response.status === 204) {
        return undefined as TResponse;
      }
      return (await response.json()) as TResponse;
    },

    async download(request: BinaryDownloadRequest): Promise<BinaryDownload> {
      const response = await send(request, requestBody(request.body), "download");
      return {
        bytes: new Uint8Array(await response.arrayBuffer()),
        contentType: response.headers.get("Content-Type"),
        filename: responseFilename(response),
      };
    },

    async upload<TResponse>(request: MultipartUploadRequest): Promise<TResponse> {
      const response = await send(request, multipartFormData(request.parts), "upload", true);
      if (response.status === 204) {
        return undefined as TResponse;
      }
      return (await response.json()) as TResponse;
    },

    async uploadFormData<TResponse>(
      request: Omit<MultipartUploadRequest, "parts"> & { formData: FormData },
    ): Promise<TResponse> {
      const response = await send(request, request.formData, "upload", true);
      if (response.status === 204) {
        return undefined as TResponse;
      }
      return (await response.json()) as TResponse;
    },
  };
}
