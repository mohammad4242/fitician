import { request } from "../../shared/apiClient";

const base = "/api/v1/admin/diagnostics";

export type DiagnosticStatus = "new" | "investigating" | "resolved" | "ignored";
export type DiagnosticConfidence = "unknown" | "likely" | "confirmed";

export interface DiagnosticIssue {
  readonly id: string;
  readonly fingerprint: string;
  readonly component: string;
  readonly operation: string;
  readonly stage: string;
  readonly platform: string;
  readonly severity: string;
  readonly category: string;
  readonly error_code: string;
  readonly exception_type: string | null;
  readonly source_location: string | null;
  readonly confidence: DiagnosticConfidence;
  readonly title: string;
  readonly first_seen: string;
  readonly last_seen: string;
  readonly count: number;
  readonly status: DiagnosticStatus;
  readonly regression_count: number;
  readonly last_alert_at: string | null;
}

export interface DiagnosticEvent {
  readonly app_version?: string | null;
  readonly event_id: string;
  readonly issue_id: string | null;
  readonly timestamp: string;
  readonly request_id: string | null;
  readonly operation_id: string | null;
  readonly user_id: string | null;
  readonly component: string;
  readonly operation: string;
  readonly stage: string;
  readonly platform: string;
  readonly version: string | null;
  readonly build: string | null;
  readonly category: string;
  readonly severity: string;
  readonly error_code: string;
  readonly exception_type: string | null;
  readonly source_location: string | null;
  readonly input_fingerprint: string | null;
  readonly resource_id: string | null;
  readonly outcome: string;
  readonly duration_ms: number | null;
  readonly retry_count: number;
  readonly http_status: number | null;
  readonly os_version: string | null;
}

export interface DiagnosticStatusHistory {
  readonly id: string;
  readonly issue_id: string;
  readonly actor_user_id: string | null;
  readonly previous_status: string;
  readonly new_status: string;
  readonly note: string | null;
  readonly created_at: string;
}

export interface DiagnosticIssueDetail {
  readonly issue: DiagnosticIssue;
  readonly events: readonly DiagnosticEvent[];
  readonly status_history: readonly DiagnosticStatusHistory[];
}

export interface DiagnosticAlert {
  readonly id: string;
  readonly issue_id: string;
  readonly created_at: string;
  readonly reason: string;
}

export interface DiagnosticOverview {
  readonly hours: number;
  readonly event_count: number;
  readonly failure_count: number;
  readonly critical_count: number;
  readonly new_issue_count: number;
  readonly affected_users: number;
  readonly error_rate: number | null;
  readonly trend: readonly { readonly timestamp: string; readonly count: number }[];
  readonly platforms: readonly { readonly platform: string; readonly count: number }[];
  readonly issue_count: number;
  readonly http_response_count: { readonly success: number; readonly failure: number };
  readonly infrastructure: {
    readonly status: string;
    readonly last_seen: string | null;
    readonly outcome: string | null;
  };
}

export interface DiagnosticGenerationOperation {
  readonly operation: string;
  readonly terminal_count: number;
  readonly success_count: number;
  readonly success_rate: number | null;
  readonly outcomes: Readonly<Record<string, number>>;
}

export interface DiagnosticGenerationMetrics {
  readonly hours: number;
  readonly operations: readonly DiagnosticGenerationOperation[];
  readonly incomplete_attempts: number;
  readonly quota_integrity: Readonly<Record<string, number>>;
  readonly failure_reasons: readonly { readonly operation: string; readonly error_code: string; readonly count: number }[];
  readonly engine_versions: readonly { readonly operation: string; readonly version: string; readonly outcome: string; readonly count: number }[];
}

export interface DiagnosticIssueFilters {
  readonly limit: number;
  readonly offset: number;
  readonly hours?: number;
  readonly platform?: string;
  readonly component?: string;
  readonly severity?: string;
  readonly category?: string;
  readonly status?: string;
  readonly error_code?: string;
  readonly user_id?: string;
  readonly request_id?: string;
  readonly version?: string;
  readonly q?: string;
  readonly sort?: "last_seen" | "first_seen" | "count" | "severity";
}

export interface DiagnosticEventFilters {
  readonly limit: number;
  readonly offset: number;
  readonly hours?: number;
  readonly user_id?: string;
  readonly request_id?: string;
  readonly operation_id?: string;
  readonly resource_id?: string;
  readonly issue_id?: string;
  readonly platform?: string;
}

export interface TraceSummary {
  readonly business_outcome?: string;
  readonly transport_outcome?: string;
  readonly worker_outcome?: string;
  readonly trace_id: string;
  readonly request_id: string;
  readonly operation_id: string;
  readonly user_id: string | null;
  readonly operation: string;
  readonly component: string;
  readonly platform: string;
  readonly started_at: string;
  readonly ended_at: string | null;
  readonly duration_ms: number | null;
  readonly stage_count: number;
  readonly outcome: string;
  readonly failure_stage: string | null;
  readonly http_status: number | null;
  readonly incomplete: boolean;
  readonly dropped_count: number;
}

export interface TracePage {
  readonly items: readonly TraceSummary[];
  readonly limit: number;
  readonly offset: number;
  readonly has_more: boolean;
}

export interface TraceFilters {
  readonly limit: number;
  readonly offset: number;
  readonly user_id?: string;
  readonly trace_id?: string;
  readonly request_id?: string;
  readonly operation_id?: string;
  readonly platform?: string;
  readonly component?: string;
  readonly operation?: string;
  readonly outcome?: string;
  readonly error_code?: string;
  readonly since?: string;
  readonly until?: string;
  readonly sort: "newest" | "slowest" | "failed";
}

export interface TraceSpan extends DiagnosticEvent {
  readonly trace_id: string;
  readonly span_id: string;
  readonly parent_span_id: string | null;
  readonly record_type: "span";
  readonly started_at: string;
  readonly ended_at: string | null;
  readonly offset_ms: number;
  readonly clock_domain: string;
}

export interface TraceDetail {
  readonly trace: TraceSummary;
  readonly spans: readonly TraceSpan[];
  readonly summary: {
    readonly operation: string;
    readonly platform: string;
    readonly observed_stages: readonly string[];
    readonly succeeded_stages: readonly string[];
    readonly failure_stage: string | null;
    readonly cause: string;
    readonly confidence: DiagnosticConfidence;
    readonly persistence: "confirmed" | "unknown";
    readonly recommendation: string;
    readonly description_fa: string;
  };
  readonly related_issue_ids: readonly string[];
  readonly truncated: boolean;
}

export interface TraceAnalytics {
  readonly observed_requests: number;
  readonly success_count: number;
  readonly failure_count: number;
  readonly incomplete_count: number;
  readonly success_rate: number | null;
  readonly stages: readonly { readonly stage: string; readonly count: number; readonly failure_count: number; readonly p50_ms: number | null; readonly p95_ms: number | null }[];
  readonly operations: readonly { readonly operation: string; readonly count: number; readonly failure_count: number; readonly affected_users: number }[];
  readonly platforms: readonly { readonly platform: string; readonly count: number; readonly failure_count: number }[];
  readonly trend: readonly { readonly timestamp: string; readonly count: number; readonly failure_count: number }[];
  readonly limitations: string;
  readonly capture?: {
    readonly success_sample_rate: number;
    readonly process_dropped_count: number;
    readonly queue_depth: number;
    readonly process_local: boolean;
  };
}

function queryString(params: Readonly<Record<string, string | number | undefined>>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  const encoded = query.toString();
  return encoded === "" ? "" : `?${encoded}`;
}

export function getDiagnosticsOverview(hours: number): Promise<DiagnosticOverview> {
  return request(`${base}/overview${queryString({ hours })}`);
}

export function getDiagnosticIssues(filters: DiagnosticIssueFilters): Promise<DiagnosticIssue[]> {
  return request(`${base}/issues${queryString({ ...filters })}`);
}

export function getDiagnosticIssue(issueId: string): Promise<DiagnosticIssueDetail> {
  return request(`${base}/issues/${encodeURIComponent(issueId)}`);
}

export function updateDiagnosticIssue(
  issueId: string,
  status: DiagnosticStatus,
  note: string,
): Promise<DiagnosticStatusHistory> {
  return request(`${base}/issues/${encodeURIComponent(issueId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status, ...(note.trim() ? { note: note.trim() } : {}) }),
  });
}

export function getDiagnosticEvents(filters: DiagnosticEventFilters): Promise<DiagnosticEvent[]> {
  return request(`${base}/events${queryString({ ...filters })}`);
}

export function getDiagnosticAlerts(limit: number, offset: number): Promise<DiagnosticAlert[]> {
  return request(`${base}/alerts${queryString({ limit, offset })}`);
}

export function getDiagnosticGenerations(hours: number): Promise<DiagnosticGenerationMetrics> {
  return request(`${base}/generations${queryString({ hours })}`);
}

export function getDiagnosticTraces(filters: TraceFilters): Promise<TracePage> {
  return request(`${base}/traces${queryString({ ...filters })}`);
}

export function getDiagnosticTrace(traceId: string): Promise<TraceDetail> {
  return request(`${base}/traces/${encodeURIComponent(traceId)}`);
}

export function getDiagnosticTraceAnalytics(hours: number): Promise<TraceAnalytics> {
  return request(`${base}/trace-analytics${queryString({ hours })}`);
}


export interface InfrastructureSnapshot {
  readonly signals: readonly { readonly component: string; readonly status: string; readonly observed_at: string | null; readonly evidence: string; readonly business_operation_verified: boolean }[];
  readonly queues: Readonly<Record<string, Readonly<Record<string, number>>>>;
}
export function getDiagnosticInfrastructure(): Promise<InfrastructureSnapshot> {
  return request(`${base}/infrastructure`);
}
