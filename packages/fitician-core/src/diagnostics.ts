import { CLIENT_EXCEPTION_TYPES, CLIENT_SOURCE_PATTERN } from "./clientException";

export type ClientDiagnosticPlatform = "android" | "ios_pwa" | "web";

export type ClientDiagnosticErrorCode =
  | "API_REQUEST_FAILED"
  | "CLIENT_RENDER_ERROR"
  | "CLIENT_RUNTIME_ERROR"
  | "CLIENT_UNHANDLED_REJECTION";

export interface ClientDiagnosticEvent {
  readonly event_id: string;
  readonly platform: ClientDiagnosticPlatform;
  readonly component: string;
  readonly operation: string;
  readonly stage: string;
  readonly error_code: ClientDiagnosticErrorCode;
  readonly request_id?: string;
  readonly version?: string;
  readonly build?: string;
  readonly duration_ms?: number;
  readonly http_status?: number;
  readonly os_version?: string;
  readonly exception_type?: string;
  readonly source_location?: string;
}

export interface ClientDiagnosticBatch {
  readonly events: readonly ClientDiagnosticEvent[];
}

export interface ClientDiagnosticsQueueOptions {
  readonly send: (batch: ClientDiagnosticBatch) => Promise<void>;
  readonly now?: () => number;
  readonly schedule?: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>;
  readonly cancel?: (timer: ReturnType<typeof setTimeout>) => void;
}

const TOKEN = /^[A-Za-z0-9_.:-]+$/u;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/iu;

function validToken(value: unknown, max: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= max && TOKEN.test(value);
}

export function isClientDiagnosticEvent(value: unknown): value is ClientDiagnosticEvent {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const event = value as Record<string, unknown>;
  const required = ["event_id", "platform", "component", "operation", "stage", "error_code"];
  const allowed = new Set([...required, "request_id", "version", "build", "duration_ms", "http_status", "os_version", "exception_type", "source_location"]);
  if (Object.keys(event).some((key) => !allowed.has(key))) return false;
  if (required.some((key) => !(key in event))) return false;
  if (typeof event.event_id !== "string" || !UUID.test(event.event_id)) return false;
  if (event.platform !== "android" && event.platform !== "ios_pwa" && event.platform !== "web") return false;
  if (!validToken(event.component, 80) || !validToken(event.operation, 80) || !validToken(event.stage, 80)) return false;
  if (event.error_code !== "API_REQUEST_FAILED" && event.error_code !== "CLIENT_RENDER_ERROR"
    && event.error_code !== "CLIENT_RUNTIME_ERROR" && event.error_code !== "CLIENT_UNHANDLED_REJECTION") return false;
  if (event.request_id !== undefined && !validToken(event.request_id, 128)) return false;
  if (event.version !== undefined && !validToken(event.version, 64)) return false;
  if (event.build !== undefined && !validToken(event.build, 64)) return false;
  if (event.exception_type !== undefined && (typeof event.exception_type !== "string" || !CLIENT_EXCEPTION_TYPES.has(event.exception_type))) return false;
  if (event.source_location !== undefined && (typeof event.source_location !== "string" || !CLIENT_SOURCE_PATTERN.test(event.source_location))) return false;
  if (event.os_version !== undefined && !validToken(event.os_version, 40)) return false;
  if (event.duration_ms !== undefined && (typeof event.duration_ms !== "number"
    || !Number.isInteger(event.duration_ms) || event.duration_ms < 0 || event.duration_ms > 86_400_000)) return false;
  if (event.http_status !== undefined && (typeof event.http_status !== "number"
    || !Number.isInteger(event.http_status) || event.http_status < 100 || event.http_status > 599)) return false;
  return true;
}

export function createClientDiagnosticEvent(
  input: Omit<ClientDiagnosticEvent, "event_id">,
  uuidFactory: () => string = createDiagnosticUuid,
): ClientDiagnosticEvent | null {
  const event = { ...input, event_id: uuidFactory() };
  return isClientDiagnosticEvent(event) ? event : null;
}

export function createDiagnosticUuid(): string {
  const cryptoApi = globalThis.crypto;
  if (typeof cryptoApi?.randomUUID === "function") return cryptoApi.randomUUID();
  const bytes = new Uint8Array(16);
  if (typeof cryptoApi?.getRandomValues === "function") cryptoApi.getRandomValues(bytes);
  else for (let i = 0; i < bytes.length; i += 1) bytes[i] = Math.floor(Math.random() * 256);
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export class ClientDiagnosticsQueue {
  private readonly now: () => number;
  private readonly schedule: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>;
  private readonly cancel: (timer: ReturnType<typeof setTimeout>) => void;
  private readonly queue: ClientDiagnosticEvent[] = [];
  private readonly deduplicated = new Map<string, number>();
  private timer: ReturnType<typeof setTimeout> | null = null;
  private flushing: Promise<void> | null = null;
  private inFlightCount = 0;
  private retries = 0;
  private epoch = 0;

  constructor(private readonly options: ClientDiagnosticsQueueOptions) {
    this.now = options.now ?? Date.now;
    this.schedule = options.schedule ?? setTimeout;
    this.cancel = options.cancel ?? clearTimeout;
  }

  enqueue(event: ClientDiagnosticEvent): boolean {
    if (!isClientDiagnosticEvent(event)) return false;
    const now = this.now();
    for (const [key, timestamp] of this.deduplicated) {
      if (now - timestamp >= 60_000) this.deduplicated.delete(key);
    }
    const dedupeKey = [event.component, event.operation, event.stage, event.error_code, event.http_status ?? "", event.exception_type ?? "", event.source_location ?? ""].join("|");
    const previous = this.deduplicated.get(dedupeKey);
    if (previous !== undefined && now - previous < 60_000) return false;
    if (this.deduplicated.size >= 128) this.deduplicated.delete(this.deduplicated.keys().next().value!);
    this.deduplicated.set(dedupeKey, now);
    if (this.queue.length === 30) this.queue.splice(this.inFlightCount, 1);
    this.queue.push(event);
    if (this.retries >= 3) this.retries = 0;
    void this.flush();
    return true;
  }

  clear(): void {
    this.epoch += 1;
    if (this.timer !== null) this.cancel(this.timer);
    this.timer = null;
    this.queue.length = 0;
    this.inFlightCount = 0;
    this.deduplicated.clear();
    this.retries = 0;
  }

  size(): number {
    return this.queue.length;
  }

  async flush(): Promise<void> {
    if (this.flushing !== null) return this.flushing;
    if (this.timer !== null) {
      this.cancel(this.timer);
      this.timer = null;
    }
    if (this.queue.length === 0) return;
    const epoch = this.epoch;
    this.flushing = this.flushQueued();
    try {
      await this.flushing;
    } finally {
      this.flushing = null;
      if (epoch !== this.epoch && this.queue.length > 0) void this.flush();
    }
  }

  private async flushQueued(): Promise<void> {
    const epoch = this.epoch;
    while (this.queue.length > 0) {
      const batch = this.queue.slice(0, 10);
      this.inFlightCount = batch.length;
      try {
        await this.options.send({ events: batch });
        if (epoch !== this.epoch) return;
        this.queue.splice(0, batch.length);
        this.inFlightCount = 0;
        this.retries = 0;
      } catch {
        if (epoch !== this.epoch) return;
        this.inFlightCount = 0;
        this.retries += 1;
        if (this.retries <= 3) {
          const delayMs = Math.min(1_000 * 2 ** (this.retries - 1), 60_000);
          this.timer = this.schedule(() => {
            this.timer = null;
            void this.flush();
          }, delayMs);
        }
        return;
      }
    }
  }
}


/** Return a fixed workflow label, never a URL, path parameter, or query. */
export function diagnosticWorkflow(path: string, fallback: string): string {
  const routes: readonly (readonly [string, string])[] = [
    ["/api/v1/auth/register", "registration"], ["/api/v1/auth/login", "login"],
    ["/api/v1/auth", "authentication"], ["/api/v1/profile", "onboarding"],
    ["/api/v1/workout-plans", "workout_generation"], ["/api/v1/nutrition", "nutrition"],
    ["/api/v1/body", "body_analysis"], ["/api/v1/notifications", "notifications"],
    ["/api/v1/billing", "subscriptions"], ["/api/v1/entitlements", "entitlements"],
    ["/media/", "media"],
  ];
  return routes.find(([prefix]) => path.startsWith(prefix))?.[1] ?? fallback;
}
