import { formatTehranDateTimeForLocale } from "@fitician/core";
import { useCallback, useEffect, useMemo, useState, type CSSProperties, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import {
  getDiagnosticTrace,
  getDiagnosticTraceAnalytics,
  getDiagnosticTraces,
  type TraceAnalytics,
  type TraceDetail,
  type TraceFilters,
  type TracePage,
  type TraceSpan,
  type TraceSummary,
} from "./api";
import "./requestTraces.css";

const words = {
  en: {
    requestNotFailed: "Recorded failed stages do not make this completed request a failure.",
    title: "Request traces", note: "Follow recorded stages across one request. Timing and causal notes depend on the evidence received.", refresh: "Refresh", live: "Poll every 15 seconds", pause: "Pause polling", resume: "Resume polling", polling: "Polling is paused while this page is hidden.",
    filters: "Trace filters", apply: "Apply filters", clear: "Clear", traceId: "Trace ID", requestId: "Request ID", operationId: "Operation ID", userId: "User ID", platform: "Platform", component: "Component", operation: "Operation", outcome: "Outcome", errorCode: "Error code", since: "Since", until: "Until", sort: "Order", newest: "Newest", slowest: "Slowest", failed: "Failures first", count: "Count",
    observed: "Observed requests", success: "Successful", failures: "Failed", incomplete: "Incomplete", successRate: "Recorded successes / observed requests", successRateNote: "Observed traces only; incomplete requests remain in the denominator, and sampling or dropped records limit this sample.", traces: "Requests", selected: "Trace detail", started: "Started", ended: "Ended", duration: "Duration", stages: "Stages", status: "HTTP", failureStage: "Failure stage", unknown: "Unknown", processing: "Processing / unknown", incompleteFlag: "Incomplete trace", dropped: "Dropped records", viewTrace: "Open trace", closeTrace: "Close trace", empty: "No traces match these filters.", loading: "Loading request traces…", failedLoad: "Request traces could not be loaded.", previous: "Previous", next: "Next", page: "Page", waterfall: "Stage timing", timeline: "Timeline", evidence: "Recorded evidence", observedStages: "Observed stages", succeededStages: "Succeeded stages", cause: "Cause assessment", confidence: "Confidence", persistence: "Persistence", recommendation: "Next step", description: "Persian summary", unknownEvidence: "Not established by the available records.", relatedIssues: "Related issues", noRelated: "No related issue was attached.", truncated: "The server shortened this trace; some records are not shown.", noSpans: "No span timings were recorded.", clockDomain: "Clock domain", clockLane: "Clock lane", clockNote: "Each lane has an independent origin. Compare offsets and durations only within a lane.", crossClockParent: "Parent span in another clock domain", crossClockTiming: "This cross-service parent link is structural; timestamps across these clocks are not comparable.", elapsed: "Offset", spanId: "Span ID", parentSpanId: "Parent span ID", source: "Source", recordedCode: "Recorded code", errorType: "Exception type", retryCount: "Retries", receivedAt: "Server receipt time", lastReceivedAt: "Last receipt time", clientReceiptNote: "Client timestamps show when the server received observations. Offset and duration use the client monotonic clock and have a separate origin.", openRoot: "The backend root has no completion record; the request remains processing or unknown.", openSpan: "This span has no completion record; its result remains unknown.", sampleRate: "Success sample rate", queueDepth: "Queue depth", processDropped: "Process dropped records", processLocal: "Process-local capture snapshot", captureNote: "Process counters are a local snapshot. Client sampling is independent, so this is not a complete capture rate.", limitationsCopy: "Stored observations only; sampling, queue drops, and retention affect totals. Client and server clocks are not directly comparable.", errors: "Errors", median: "p50", percentile95: "p95", stageStats: "Stage timings", operations: "Operations", platforms: "Platforms", trend: "Request volume and failures", trendFailures: "Failed", limitations: "Data limits", liveState: "Live polling is on", persistenceConfirmed: "Confirmed", persistenceUnknown: "Unknown", confidenceUnknown: "Unknown", confidenceLikely: "Likely", confidenceConfirmed: "Confirmed", outcomeSuccess: "Success", outcomeFailure: "Failure", incompleteUnknown: "A missing completion record does not establish failure.", user: "View user", issue: "View issue", perSpanEvidence: "This span records an observation, not a confirmed cause.", perSpanRecommendation: "Review this span with adjacent records; its causal role is unconfirmed.", crossDomain: "Different clock", outcomes: { success: "Success", failure: "Failure", timeout: "Timeout", cancelled: "Cancelled", reused: "Reused", pending_review: "Pending review", blocked: "Blocked", started: "Started", stage: "Stage", unknown: "Unknown", likely: "Likely", confirmed: "Confirmed", processing: "Processing / unknown" },
  },
  fa: {
    requestNotFailed: "ثبت مرحله ناموفق به‌تنهایی به معنی شکست این درخواستِ پایان‌یافته نیست.",
    title: "ردیابی درخواست‌ها", note: "مراحل ثبت‌شدهٔ یک درخواست را دنبال کن. زمان‌بندی و ارزیابی علت به شواهد دریافتی وابسته است.", refresh: "تازه‌سازی", live: "دریافت خودکار هر ۱۵ ثانیه", pause: "توقف دریافت خودکار", resume: "ادامه دریافت خودکار", polling: "هنگام پنهان‌بودن صفحه، دریافت خودکار متوقف است.",
    filters: "فیلترهای ردیابی", apply: "اعمال فیلترها", clear: "پاک‌کردن", traceId: "شناسه ردگیری", requestId: "شناسه درخواست", operationId: "شناسه عملیات", userId: "شناسه کاربر", platform: "پلتفرم", component: "بخش", operation: "عملیات", outcome: "نتیجه", errorCode: "کد خطا", since: "از زمان", until: "تا زمان", sort: "ترتیب", newest: "جدیدترین", slowest: "طولانی‌ترین", failed: "ابتدا ناموفق‌ها", count: "تعداد",
    observed: "درخواست‌های ثبت‌شده", success: "موفق", failures: "ناموفق", incomplete: "ناتمام", successRate: "موفقیت ثبت‌شده / درخواست مشاهده‌شده", successRateNote: "فقط ردگیری‌های مشاهده‌شده؛ درخواست‌های ناتمام در مخرج هستند و نمونه‌برداری یا رکوردهای ازدست‌رفته این نمونه را محدود می‌کنند.", traces: "درخواست‌ها", selected: "جزئیات ردگیری", started: "شروع", ended: "پایان", duration: "مدت", stages: "مراحل", status: "HTTP", failureStage: "مرحله شکست", unknown: "نامشخص", processing: "در حال پردازش / نامشخص", incompleteFlag: "ردگیری ناتمام", dropped: "رکوردهای ازدست‌رفته", viewTrace: "بازکردن ردگیری", closeTrace: "بستن ردگیری", empty: "ردگیری‌ای با این فیلترها پیدا نشد.", loading: "در حال دریافت ردگیری‌ها…", failedLoad: "ردگیری درخواست‌ها دریافت نشد.", previous: "قبلی", next: "بعدی", page: "صفحه", waterfall: "زمان‌بندی مراحل", timeline: "خط زمان", evidence: "شواهد ثبت‌شده", observedStages: "مراحل مشاهده‌شده", succeededStages: "مراحل موفق", cause: "ارزیابی علت", confidence: "میزان اطمینان", persistence: "ماندگاری داده", recommendation: "گام بعدی", description: "خلاصه فارسی", unknownEvidence: "با رکوردهای موجود مشخص نشده است.", relatedIssues: "مسئله‌های مرتبط", noRelated: "مسئله مرتبطی ثبت نشده است.", truncated: "بخشی از رکوردها در پاسخ سرور نمایش داده نمی‌شوند.", noSpans: "زمان‌بندی مرحله‌ای ثبت نشده است.", clockDomain: "مبنای ساعت", clockLane: "مسیر ساعت", clockNote: "هر مسیر مبدأ زمانی جداگانه دارد. زمان‌ها را فقط درون یک مسیر مقایسه کن.", crossClockParent: "والد در مبنای ساعت دیگر", crossClockTiming: "پیوند والد میان سرویس‌ها ساختاری است؛ زمان‌های آن با این مسیر قابل مقایسه نیستند.", elapsed: "فاصله از آغاز", spanId: "شناسه بازه", parentSpanId: "شناسه بازه والد", source: "منبع", recordedCode: "کد ثبت‌شده", errorType: "نوع استثنا", retryCount: "تلاش مجدد", receivedAt: "زمان دریافت در سرور", lastReceivedAt: "آخرین زمان دریافت", clientReceiptNote: "زمان کلاینت، زمان دریافت مشاهده در سرور است؛ فاصله و مدت از ساعت یکنواخت کلاینت و مبدأیی جداگانه می‌آیند.", openRoot: "رکورد پایان بازه اصلی سرور وجود ندارد؛ نتیجه درخواست در حال پردازش یا نامشخص است.", openSpan: "رکورد پایان این بازه وجود ندارد؛ نتیجه آن نامشخص است.", sampleRate: "نرخ نمونه‌برداری موفق‌ها", queueDepth: "عمق صف", processDropped: "رکوردهای ازدست‌رفته در این پردازه", processLocal: "وضعیت ثبت همین پردازه", captureNote: "شمارنده‌های پردازه فقط وضعیت همین پردازه‌اند. نمونه‌برداری کلاینت جداگانه است و نرخ کامل ثبت را نشان نمی‌دهد.", limitationsCopy: "فقط مشاهدات نگهداری‌شده؛ نمونه‌برداری، ازدست‌رفتن صف و مدت نگهداری بر مجموع اثر دارند. ساعت کلاینت و سرور مستقیماً قابل مقایسه نیست.", errors: "خطاها", median: "میانه", percentile95: "صدک ۹۵", stageStats: "زمان مراحل", operations: "عملیات‌ها", platforms: "پلتفرم‌ها", trend: "حجم درخواست و شکست‌ها", trendFailures: "ناموفق", limitations: "محدودیت داده", liveState: "دریافت خودکار روشن است", persistenceConfirmed: "تأییدشده", persistenceUnknown: "نامشخص", confidenceUnknown: "نامشخص", confidenceLikely: "محتمل", confidenceConfirmed: "تأییدشده", outcomeSuccess: "موفق", outcomeFailure: "ناموفق", incompleteUnknown: "نبود رکورد پایان، به‌تنهایی شکست را ثابت نمی‌کند.", user: "نمایش کاربر", issue: "نمایش مسئله", perSpanEvidence: "این بازه یک مشاهده را ثبت می‌کند، نه علت تأییدشده را.", perSpanRecommendation: "این بازه را همراه رکوردهای مجاور بررسی کن؛ نقش علّی آن تأیید نشده است.", crossDomain: "ساعت جداگانه", outcomes: { success: "موفق", failure: "ناموفق", timeout: "پایان مهلت", cancelled: "لغوشده", reused: "استفاده مجدد", pending_review: "در انتظار بررسی", blocked: "مسدودشده", started: "آغازشده", stage: "مرحله‌ای", unknown: "نامشخص", likely: "محتمل", confirmed: "تأییدشده", processing: "در حال پردازش / نامشخص" },
  },
} as const;

const stageNamesFa: Readonly<Record<string, string>> = {
  backend_request: "دریافت درخواست", backend_response_completed: "پایان پاسخ سرور",
  backend_response_interrupted: "پاسخ قطع‌شده", validation_and_dependencies: "اعتبارسنجی و وابستگی‌ها",
  authentication_authorization: "احراز هویت و مجوز", business_logic: "اجرای عملیات",
  entitlement_check: "بررسی دسترسی", medical_safety: "ایمنی پزشکی", profile_completeness: "کامل‌بودن پروفایل",
  nutrition_estimate: "برآورد تغذیه", dietary_constraints: "محدودیت‌های غذایی",
  catalogue_availability: "دسترسی به کاتالوگ", budget_and_program_selection: "انتخاب بودجه و برنامه",
  reuse_evaluation: "بررسی استفاده مجدد", quota_availability: "بررسی سهمیه",
  meal_construction: "ساخت وعده‌ها", candidate_plan_week: "ساخت گزینه هفتگی",
  ideal_plan_week: "ساخت برنامه ایده‌آل", budget_plan_week: "ساخت برنامه اقتصادی",
  candidate_comparison: "مقایسه گزینه‌ها", input_consistency_validation: "سازگاری ورودی‌ها",
  plan_persistence: "ذخیره برنامه", transaction_commit: "تأیید تراکنش",
  response_serialization: "آماده‌سازی داده پاسخ", response_preparation: "آماده‌سازی پاسخ",
  database_execute: "اجرای پایگاه داده", database_commit: "تأیید ذخیره‌سازی",
  database_connection_acquire: "دریافت اتصال پایگاه داده", worker_execution: "اجرای کار پس‌زمینه",
  agent_service_call: "فراخوانی سرویس Agent", dispatch: "ارسال درخواست کلاینت",
  response_received: "دریافت پاسخ کلاینت", transport_failed: "شکست ارتباط کلاینت",
};

type Copy = (typeof words)["en"];

function useTraceCopy() {
  const { i18n } = useTranslation();
  const english = i18n.resolvedLanguage === "en";
  return { c: (english ? words.en : words.fa) as Copy, english, locale: english ? "en" as const : "fa" as const };
}

function clean(value: string | null): string | undefined {
  const normalized = value?.trim();
  return normalized ? normalized : undefined;
}

function dateTime(value: string | null | undefined, english: boolean): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : formatTehranDateTimeForLocale(parsed.toISOString(), english ? "en-US" : "fa-IR");
}

function number(value: number | null, english: boolean, suffix = ""): string {
  return value === null ? "—" : `${value.toLocaleString(english ? "en-US" : "fa-IR")}${suffix}`;
}

function localDate(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function useTraceResource<T>(load: () => Promise<T>, key: string, revision: number) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    void load().then((value) => {
      if (active) { setData(value); setError(null); }
    }).catch((cause: unknown) => {
      if (active) setError(cause);
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [key, load, retry, revision]);
  return { data, error, loading, retry: () => setRetry((value) => value + 1) };
}

export function RequestTraces() {
  const { c, english, locale } = useTraceCopy();
  const [search, setSearch] = useSearchParams();
  const [live, setLive] = useState(false);
  const [visible, setVisible] = useState(() => typeof document === "undefined" || !document.hidden);
  const [revision, setRevision] = useState(0);
  const limit = 25;
  const offset = Math.max(0, Number(search.get("trace_offset") ?? 0) || 0);
  const sortValue = search.get("trace_sort");
  const sort: TraceFilters["sort"] = sortValue === "slowest" || sortValue === "failed" ? sortValue : "newest";
  const traceId = clean(search.get("trace_id")) ?? "";
  const filters = useMemo<TraceFilters>(() => ({
    limit, offset, sort,
    user_id: clean(search.get("trace_user_id")),
    trace_id: clean(search.get("trace_id")),
    request_id: clean(search.get("request_id")),
    operation_id: clean(search.get("operation_id")),
    platform: clean(search.get("trace_platform")),
    component: clean(search.get("trace_component")),
    operation: clean(search.get("trace_operation")),
    outcome: clean(search.get("trace_outcome")),
    error_code: clean(search.get("trace_error_code")),
    since: clean(search.get("trace_since")),
    until: clean(search.get("trace_until")),
  }), [offset, search, sort]);
  const filterKey = JSON.stringify(filters);
  const loadPage = useCallback(() => getDiagnosticTraces(filters), [filters]);
  const page = useTraceResource<TracePage>(loadPage, filterKey, revision);
  const loadAnalytics = useCallback(() => getDiagnosticTraceAnalytics(24), []);
  const analytics = useTraceResource<TraceAnalytics>(loadAnalytics, "trace-analytics-24", revision);
  const loadTrace = useCallback(() => traceId ? getDiagnosticTrace(traceId) : Promise.resolve(null), [traceId]);
  const detail = useTraceResource<TraceDetail | null>(loadTrace, traceId, revision);

  useEffect(() => {
    const onVisibility = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);
  useEffect(() => {
    if (!live || !visible) return;
    const timer = window.setInterval(() => setRevision((value) => value + 1), 15_000);
    return () => window.clearInterval(timer);
  }, [live, visible]);

  const updateSearch = (mutate: (next: URLSearchParams) => void) => {
    const next = new URLSearchParams(search);
    mutate(next);
    setSearch(next);
  };
  const apply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    updateSearch((next) => {
      next.set("tab", "traces");
      next.delete("trace_offset");
      const mappings: ReadonlyArray<readonly [string, string]> = [
        ["trace_id", "trace_id"], ["request_id", "request_id"], ["operation_id", "operation_id"], ["trace_user_id", "user_id"],
        ["trace_platform", "platform"], ["trace_component", "component"], ["trace_operation", "operation"], ["trace_outcome", "outcome"], ["trace_error_code", "error_code"],
      ];
      for (const [key, field] of mappings) {
        const value = String(values.get(field) ?? "").trim();
        if (value) next.set(key, value); else next.delete(key);
      }
      for (const key of ["trace_since", "trace_until"]) {
        const field = key === "trace_since" ? "since" : "until";
        const value = String(values.get(field) ?? "");
        if (value) next.set(key, new Date(value).toISOString()); else next.delete(key);
      }
      const selectedSort = String(values.get("sort") ?? "newest");
      if (selectedSort === "newest") next.delete("trace_sort"); else next.set("trace_sort", selectedSort);
    });
  };
  const move = (nextOffset: number) => updateSearch((next) => { next.set("tab", "traces"); next.set("trace_offset", String(nextOffset)); });
  const openTrace = (id: string) => updateSearch((next) => { next.set("tab", "traces"); next.set("trace_id", id); });
  const closeTrace = () => updateSearch((next) => next.delete("trace_id"));

  return <div className="diagnostics-stack diagnostics-traces" dir={english ? "ltr" : "rtl"}>
    <section className="diagnostics-trace-intro" aria-labelledby="trace-heading">
      <div><p className="diagnostics-label">W3C / REQUEST PATH</p><h2 id="trace-heading">{c.title}</h2><p>{c.note}</p></div>
      <div className="diagnostics-trace-controls">
        <label className="diagnostics-trace-live"><input checked={live} onChange={(event) => setLive(event.currentTarget.checked)} type="checkbox" />{c.live}</label>
        <button className="diagnostics-button diagnostics-button--quiet" onClick={() => setRevision((value) => value + 1)} type="button">{c.refresh}</button>
      </div>
    </section>
    {live && <p className="diagnostics-trace-poll-state" role="status">{visible ? c.liveState : c.polling}</p>}

    <TraceAnalyticsPanel result={analytics} />

    <form className="diagnostics-card diagnostics-filters diagnostics-trace-filters" key={filterKey} onSubmit={apply}>
      <div className="diagnostics-card__heading"><div><p className="diagnostics-label">TRACE QUERY</p><h2>{c.filters}</h2></div></div>
      <div className="diagnostics-filter-grid">
        <TraceField label={c.traceId} name="trace_id" value={search.get("trace_id") ?? ""} />
        <TraceField label={c.requestId} name="request_id" value={search.get("request_id") ?? ""} />
        <TraceField label={c.operationId} name="operation_id" value={search.get("operation_id") ?? ""} />
        <TraceField label={c.userId} name="user_id" value={search.get("trace_user_id") ?? ""} />
        <TraceField label={c.platform} name="platform" value={search.get("trace_platform") ?? ""} />
        <TraceField label={c.component} name="component" value={search.get("trace_component") ?? ""} />
        <TraceField label={c.operation} name="operation" value={search.get("trace_operation") ?? ""} />
        <TraceField label={c.outcome} name="outcome" value={search.get("trace_outcome") ?? ""} />
        <TraceField label={c.errorCode} name="error_code" value={search.get("trace_error_code") ?? ""} />
        <TraceField label={c.since} name="since" type="datetime-local" value={localDate(search.get("trace_since"))} />
        <TraceField label={c.until} name="until" type="datetime-local" value={localDate(search.get("trace_until"))} />
        <label className="diagnostics-field">{c.sort}<select defaultValue={sort} name="sort"><option value="newest">{c.newest}</option><option value="slowest">{c.slowest}</option><option value="failed">{c.failed}</option></select></label>
      </div>
      <div className="diagnostics-filter-actions">
        <button className="diagnostics-button" type="submit">{c.apply}</button>
        <button className="diagnostics-button diagnostics-button--quiet" onClick={() => updateSearch((next) => { for (const key of ["trace_id", "request_id", "operation_id", "trace_user_id", "trace_platform", "trace_component", "trace_operation", "trace_outcome", "trace_error_code", "trace_since", "trace_until", "trace_sort", "trace_offset"]) next.delete(key); next.set("tab", "traces"); })} type="button">{c.clear}</button>
      </div>
    </form>

    <section className="diagnostics-card" aria-labelledby="traces-list-heading">
      <div className="diagnostics-card__heading"><div><p className="diagnostics-label">REQUEST INDEX</p><h2 id="traces-list-heading">{c.traces}</h2></div></div>
      <ResourceState loading={page.loading} error={page.error} retry={page.retry} locale={locale} label={c.loading} failure={c.failedLoad} />
      {page.data && <>
        <div className="diagnostics-trace-list" role="list">
          {page.data.items.map((trace) => <TraceRow key={`${trace.trace_id}-${trace.operation_id}`} trace={trace} selected={trace.trace_id === traceId} onOpen={openTrace} />)}
          {page.data.items.length === 0 && <p className="diagnostics-empty">{c.empty}</p>}
        </div>
        <nav aria-label={c.traces} className="diagnostics-pager">
          <button className="diagnostics-button diagnostics-button--quiet" disabled={offset <= 0} onClick={() => move(Math.max(0, offset - limit))} type="button">{c.previous}</button>
          <span>{c.page} {number(Math.floor(offset / limit) + 1, english)}</span>
          <button className="diagnostics-button diagnostics-button--quiet" disabled={!page.data.has_more} onClick={() => move(offset + limit)} type="button">{c.next}</button>
        </nav>
      </>}
    </section>

    {traceId && <section className="diagnostics-card diagnostics-trace-detail" aria-labelledby="trace-detail-heading">
      <div className="diagnostics-card__heading"><div><p className="diagnostics-label">SELECTED REQUEST</p><h2 id="trace-detail-heading">{c.selected}</h2></div><button className="diagnostics-button diagnostics-button--quiet" onClick={closeTrace} type="button">{c.closeTrace}</button></div>
      <ResourceState loading={detail.loading} error={detail.error} retry={detail.retry} locale={locale} label={c.loading} failure={c.failedLoad} />
      {detail.data && <TraceDetailView detail={detail.data} english={english} />}
    </section>}
  </div>;
}

function TraceAnalyticsPanel({ result }: { result: ReturnType<typeof useTraceResource<TraceAnalytics>> }) {
  const { c, english, locale } = useTraceCopy();
  const data = result.data;
  return <section className="diagnostics-trace-analytics" aria-label={c.observed}>
    <p className="diagnostics-caption">{english ? "Analytics window: last 24 hours" : "بازه آمار: ۲۴ ساعت گذشته"}</p>
    <ResourceState loading={result.loading} error={result.error} retry={result.retry} locale={locale} label={c.loading} failure={c.failedLoad} />
    {data && <>
      <div className="diagnostics-trace-metrics">
        <Metric label={c.observed} value={number(data.observed_requests, english)} />
        <Metric label={c.success} value={number(data.success_count, english)} />
        <Metric label={c.failures} value={number(data.failure_count, english)} tone="failure" />
        <Metric label={c.incomplete} value={number(data.incomplete_count, english)} tone="quiet" />
        <Metric label={c.successRate} value={data.success_rate === null ? "—" : number(data.success_rate * 100, english, "%")} />
      </div>
      <p className="diagnostics-trace-rate-note">{c.successRateNote}</p>
      {data.capture && <div className="diagnostics-trace-capture" aria-label={c.processLocal}>
        <strong>{c.processLocal}</strong>
        <span>{c.sampleRate}: {number(data.capture.success_sample_rate * 100, english, "%")}</span>
        <span>{c.processDropped}: {number(data.capture.process_dropped_count, english)}</span>
        <span>{c.queueDepth}: {number(data.capture.queue_depth, english)}</span>
        <small>{c.captureNote}</small>
      </div>}
      <div className="diagnostics-trace-analytics-grid">
        <div className="diagnostics-card"><h3>{c.stageStats}</h3><div className="diagnostics-table-wrap"><table className="diagnostics-table"><thead><tr><th>{c.stages}</th><th>{c.count}</th><th>{c.errors}</th><th>{c.median}</th><th>{c.percentile95}</th></tr></thead><tbody>{data.stages.map((stage) => <tr key={stage.stage}><td dir="ltr">{stage.stage}</td><td>{number(stage.count, english)}</td><td>{number(stage.failure_count, english)}</td><td>{number(stage.p50_ms, english, " ms")}</td><td>{number(stage.p95_ms, english, " ms")}</td></tr>)}</tbody></table></div></div>
        <div className="diagnostics-card"><h3>{c.operations}</h3><div className="diagnostics-table-wrap"><table className="diagnostics-table"><thead><tr><th>{c.operation}</th><th>{c.count}</th><th>{c.errors}</th><th>{c.userId}</th></tr></thead><tbody>{data.operations.map((row) => <tr key={row.operation}><td dir="ltr">{row.operation}</td><td>{number(row.count, english)}</td><td>{number(row.failure_count, english)}</td><td>{number(row.affected_users, english)}</td></tr>)}</tbody></table></div></div>
        <div className="diagnostics-card"><h3>{c.platforms}</h3><div className="diagnostics-table-wrap"><table className="diagnostics-table"><thead><tr><th>{c.platform}</th><th>{c.count}</th><th>{c.errors}</th></tr></thead><tbody>{data.platforms.map((row) => <tr key={row.platform}><td dir="ltr">{row.platform}</td><td>{number(row.count, english)}</td><td>{number(row.failure_count, english)}</td></tr>)}</tbody></table></div></div>
        <div className="diagnostics-card"><h3>{c.trend}</h3><ol className="diagnostics-trace-trend">{data.trend.map((point) => { const width = data.observed_requests > 0 ? Math.max(2, (point.count / data.observed_requests) * 100) : 0; return <li key={point.timestamp}><time>{dateTime(point.timestamp, english)}</time><span className="diagnostics-trace-trend__track" aria-label={`${point.count} ${c.count}, ${point.failure_count} ${c.trendFailures}`}><i style={{ width: `${width}%` }} /><i className="diagnostics-trace-trend__failure" style={{ width: `${Math.min(width, point.count > 0 ? (point.failure_count / point.count) * width : 0)}%` }} /></span><b>{number(point.count, english)} / {number(point.failure_count, english)} {c.trendFailures}</b></li>; })}</ol></div>
      </div>
      {data.limitations && <p className="diagnostics-trace-limitations"><strong>{c.limitations}:</strong> <span lang={english ? "en" : "fa"} dir={english ? "ltr" : "rtl"}>{english ? c.limitationsCopy : data.limitations}</span></p>}
    </>}
  </section>;
}

function Metric({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return <article className={`diagnostics-trace-metric ${tone ? `diagnostics-trace-metric--${tone}` : ""}`}><span>{label}</span><strong>{value}</strong></article>;
}

function TraceField({ label, name, type = "text", value }: { label: string; name: string; type?: string; value: string }) {
  return <label className="diagnostics-field">{label}<input autoComplete="off" dir={type === "datetime-local" ? undefined : "ltr"} name={name} type={type} defaultValue={value} /></label>;
}

function ResourceState({ loading, error, retry, locale, label, failure }: { loading: boolean; error: unknown; retry: () => void; locale: "en" | "fa"; label: string; failure: string }) {
  const { c } = useTraceCopy();
  if (loading) return <p className="diagnostics-state" role="status">{label}</p>;
  if (error !== null) return <div className="diagnostics-error"><p className="diagnostics-caption">{failure}</p><AppErrorNotice audience="admin" context="generic" error={error} locale={locale} /><button className="diagnostics-button diagnostics-button--quiet" onClick={retry} type="button">{c.refresh}</button></div>;
  return null;
}

function TraceRow({ trace, selected, onOpen }: { trace: TraceSummary; selected: boolean; onOpen: (id: string) => void }) {
  const { c, english } = useTraceCopy();
  return <article aria-current={selected ? "true" : undefined} className={`diagnostics-trace-row ${selected ? "diagnostics-trace-row--selected" : ""}`} role="listitem">
    <div className="diagnostics-trace-row__main">
      <button className="diagnostics-trace-open" onClick={() => onOpen(trace.trace_id)} type="button"><strong dir="ltr">{trace.trace_id}</strong><span>{trace.component} · {trace.operation}</span></button>
      <StatusBadge value={trace.ended_at === null ? "unknown" : trace.outcome} />
    </div>
    <div className="diagnostics-trace-row__meta">
      <span>{c.started}: <b>{dateTime(trace.started_at, english)}</b></span>
      <span>{c.duration}: <b>{number(trace.duration_ms, english, " ms")}</b></span>
      <span>{c.stages}: <b>{number(trace.stage_count, english)}</b></span>
      <span>{c.platform}: <b dir="ltr">{trace.platform}</b></span>
      <span>{c.status}: <b>{trace.http_status ?? "—"}</b></span>
      {trace.failure_stage && trace.ended_at !== null && isFailureOutcome(trace.outcome) && <span className="diagnostics-trace-failure">{c.failureStage}: <b dir="ltr">{trace.failure_stage}</b></span>}
      {trace.incomplete && <span className="diagnostics-badge diagnostics-badge--timeout">{c.incompleteFlag}</span>}
      {trace.dropped_count > 0 && <span>{c.dropped}: <b>{number(trace.dropped_count, english)}</b></span>}
    </div>
    <div className="diagnostics-trace-ids"><span dir="ltr">{c.requestId}: {trace.request_id}</span><span dir="ltr">{c.operationId}: {trace.operation_id}</span>{trace.user_id && <Link to={`/admin/billing/users/${encodeURIComponent(trace.user_id)}`} dir="ltr">{c.user}: {trace.user_id}</Link>}</div>
  </article>;
}

function TraceDetailView({ detail, english }: { detail: TraceDetail; english: boolean }) {
  const { c } = useTraceCopy();
  const lanes = buildTraceLanes(detail.spans);
  const backendRootOpen = lanes.some((lane) => lane.openBackendRoot);
  const { summary, trace } = detail;
  const outcome = trace.ended_at === null || backendRootOpen ? "unknown" : trace.outcome;
  const showFailureStage = trace.ended_at !== null && isFailureOutcome(trace.outcome);
  return <div className="diagnostics-stack">
    <div className="diagnostics-trace-detail-meta"><code dir="ltr">{trace.trace_id}</code><StatusBadge value={outcome} /><span>{trace.operation}</span><span dir="ltr">{trace.platform}</span><span>{dateTime(trace.started_at, english)}</span><span>{number(trace.duration_ms, english, " ms")}</span></div>
    <div className="diagnostics-trace-evidence-grid">
      <article className="diagnostics-trace-evidence"><h3>{c.evidence}</h3>
        <p>{english ? "HTTP transport" : "انتقال HTTP"}: <StatusBadge value={trace.transport_outcome ?? "unknown"} /></p>
        <p>{english ? "Business result" : "نتیجه عملیات"}: <StatusBadge value={trace.business_outcome ?? "unknown"} /></p>
        <p>{english ? "Background result" : "نتیجه کار پس‌زمینه"}: <StatusBadge value={trace.worker_outcome ?? "unknown"} /></p><p><strong>{c.cause}:</strong> {summary.cause || c.unknown}</p><p><strong>{c.confidence}:</strong> <StatusBadge value={summary.confidence} /></p><p><strong>{c.persistence}:</strong> <StatusBadge value={summary.persistence} /></p>{showFailureStage && summary.failure_stage && <p><strong>{c.failureStage}:</strong> <b dir="ltr">{summary.failure_stage}</b></p>}{!showFailureStage && summary.failure_stage && <p className="diagnostics-trace-unknown">{c.requestNotFailed}</p>}<p><strong>{c.recommendation}:</strong> {summary.recommendation || c.unknown}</p>{summary.description_fa && <p lang="fa" dir="rtl"><strong>{c.description}:</strong> {summary.description_fa}</p>}
        <h4>{c.observedStages}</h4>{summary.observed_stages.length ? <ul>{summary.observed_stages.map((stage, index) => <li key={`${stage}-${index}`} dir="ltr">{stage}</li>)}</ul> : <p>{c.unknownEvidence}</p>}
        <h4>{c.succeededStages}</h4>{summary.succeeded_stages.length ? <ul>{summary.succeeded_stages.map((stage, index) => <li key={`${stage}-${index}`} dir="ltr">{stage}</li>)}</ul> : <p>{c.unknownEvidence}</p>}
        {detail.related_issue_ids.length > 0 ? <p>{c.relatedIssues}: {detail.related_issue_ids.map((id) => <Link key={id} to={`/admin/diagnostics?tab=issues&issue=${encodeURIComponent(id)}`} dir="ltr">{id}</Link>)}</p> : <p className="diagnostics-caption">{c.noRelated}</p>}
      </article>
      <article className="diagnostics-trace-waterfall"><div className="diagnostics-card__heading"><div><h3>{c.waterfall}</h3><p className="diagnostics-caption">{c.clockNote}</p></div></div>
        {lanes.length ? lanes.map((lane) => <TraceClockLane key={lane.clockDomain} lane={lane} english={english} />) : <p className="diagnostics-empty">{c.noSpans}</p>}
        {detail.truncated && <p className="diagnostics-trace-truncated" role="note">{c.truncated}</p>}
        {backendRootOpen && <p className="diagnostics-trace-unknown" role="note">{c.openRoot}</p>}
        {trace.incomplete && <p className="diagnostics-trace-unknown" role="note">{c.incompleteUnknown}</p>}
      </article>
    </div>
  </div>;
}

interface TraceClockLaneData {
  readonly clockDomain: string;
  readonly roots: readonly TraceSpan[];
  readonly children: ReadonlyMap<TraceSpan, readonly TraceSpan[]>;
  readonly crossClockParents: ReadonlyMap<TraceSpan, TraceSpan>;
  readonly total: number;
  readonly openBackendRoot: boolean;
}

function buildTraceLanes(spans: readonly TraceSpan[]): TraceClockLaneData[] {
  const grouped = new Map<string, TraceSpan[]>();
  for (const span of spans) {
    const domain = span.clock_domain || "unknown";
    grouped.set(domain, [...(grouped.get(domain) ?? []), span]);
  }
  return [...grouped.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([clockDomain, laneSpans]) => {
    const parents = new Map<TraceSpan, TraceSpan>();
    const crossClockParents = new Map<TraceSpan, TraceSpan>();
    for (const span of laneSpans) {
      if (!span.parent_span_id) continue;
      const sameClock = laneSpans.find((candidate) => candidate.span_id === span.parent_span_id && candidate !== span);
      if (sameClock && !wouldCreateTraceCycle(span, sameClock, parents)) parents.set(span, sameClock);
      else if (!sameClock) {
        const otherClock = spans.find((candidate) => candidate.span_id === span.parent_span_id && candidate.clock_domain !== span.clock_domain);
        if (otherClock) crossClockParents.set(span, otherClock);
      }
    }
    const children = new Map<TraceSpan, TraceSpan[]>();
    for (const [span, parent] of parents) children.set(parent, [...(children.get(parent) ?? []), span]);
    const roots = laneSpans.filter((span) => !parents.has(span));
    const total = Math.max(1, ...laneSpans.map((span) => span.offset_ms + (span.duration_ms ?? 0)));
    const openBackendRoot = roots.some((span) => span.platform === "backend" && span.ended_at === null);
    return { clockDomain, roots, children, crossClockParents, total, openBackendRoot };
  });
}

function wouldCreateTraceCycle(child: TraceSpan, parent: TraceSpan, parents: ReadonlyMap<TraceSpan, TraceSpan>): boolean {
  let current: TraceSpan | undefined = parent;
  for (let depth = 0; current && depth < 64; depth += 1) {
    if (current === child) return true;
    current = parents.get(current);
  }
  return current !== undefined;
}

function isFailureOutcome(outcome: string): boolean {
  return outcome === "failure" || outcome === "blocked" || outcome === "timeout" || outcome === "cancelled";
}

function TraceClockLane({ lane, english }: { lane: TraceClockLaneData; english: boolean }) {
  const { c } = useTraceCopy();
  return <section className="diagnostics-waterfall-lane" data-clock-domain={lane.clockDomain} aria-label={`${c.clockLane}: ${lane.clockDomain}`}>
    <div className="diagnostics-waterfall-lane__heading"><strong>{c.clockLane}</strong><code dir="ltr">{lane.clockDomain}</code></div>
    {lane.clockDomain === "client" && <p className="diagnostics-waterfall-client-note" role="note">{c.clientReceiptNote}</p>}
    <div className="diagnostics-waterfall-axis" aria-hidden="true"><span>0</span><span>{number(lane.total / 2, english)}</span><span>{number(lane.total, english)} ms</span></div>
    <ol className="diagnostics-waterfall-tree">{lane.roots.map((span) => <TraceSpanRow key={`${span.clock_domain}:${span.span_id}:${span.event_id}`} span={span} depth={0} total={lane.total} english={english} childrenSpans={lane.children.get(span) ?? []} crossClockParent={lane.crossClockParents.get(span)} lane={lane} />)}</ol>
  </section>;
}

function TraceSpanRow({ span, depth, total, english, childrenSpans, crossClockParent, lane }: { span: TraceSpan; depth: number; total: number; english: boolean; childrenSpans: readonly TraceSpan[]; crossClockParent?: TraceSpan; lane: TraceClockLaneData }) {
  const { c } = useTraceCopy();
  const [expanded, setExpanded] = useState(false);
  const left = Math.max(0, Math.min(100, (span.offset_ms / total) * 100));
  const duration = span.duration_ms ?? (span.ended_at ? Math.max(0, new Date(span.ended_at).getTime() - new Date(span.started_at).getTime()) : 0);
  const width = Math.max(0.7, Math.min(100 - left, (duration / total) * 100));
  const style = { "--trace-left": `${left}%`, "--trace-width": `${width}%` } as CSSProperties;
  const visibleOutcome = span.ended_at === null ? "unknown" : span.outcome;
  const isOpenRoot = span.platform === "backend" && lane.roots.includes(span) && span.ended_at === null;
  return <li className="diagnostics-waterfall-node">
    <div className="diagnostics-waterfall-row" style={{ "--trace-depth": depth } as CSSProperties}>
      <button aria-expanded={expanded} className="diagnostics-waterfall-expand" onClick={() => setExpanded((value) => !value)} type="button"><span aria-hidden="true">{expanded ? "−" : "+"}</span><strong dir="ltr">{span.stage}</strong>{!english && stageNamesFa[span.stage] && <small lang="fa" dir="rtl">{stageNamesFa[span.stage]}</small>}<small>{span.component} · {span.operation}</small></button>
      <div className="diagnostics-waterfall-track" role="img" aria-label={`${span.stage}: ${span.offset_ms} ms, ${span.ended_at ? `${duration} ms` : c.unknown}`}><span className={`diagnostics-waterfall-bar diagnostics-waterfall-bar--${visibleOutcome}`} style={style} /></div>
      <span className="diagnostics-waterfall-duration">{span.ended_at ? number(duration, english, " ms") : c.unknown}</span>
      <StatusBadge value={visibleOutcome} />
    </div>
    {crossClockParent && <p className="diagnostics-waterfall-cross-link"><strong>{c.crossClockParent}:</strong> <code dir="ltr">{crossClockParent.span_id}</code> <span dir="ltr">{crossClockParent.clock_domain}</span> <small>{c.crossClockTiming}</small></p>}
    {expanded && <div className="diagnostics-waterfall-proof">
      <span>{c.spanId}: <b dir="ltr">{span.span_id}</b></span><span>{c.parentSpanId}: <b dir="ltr">{span.parent_span_id ?? c.unknown}</b></span>
      <span>{c.clockDomain}: <b dir="ltr">{span.clock_domain || c.unknown}</b></span><span>{c.elapsed}: {number(span.offset_ms, english)} ms</span>
      <span>{span.clock_domain === "client" ? c.receivedAt : c.started}: {dateTime(span.started_at, english)}</span><span>{span.clock_domain === "client" ? c.lastReceivedAt : c.ended}: {dateTime(span.ended_at, english)}</span><span>{c.duration}: {number(duration, english, " ms")}</span>
      <span>{c.outcome}: <StatusBadge value={visibleOutcome} /></span><span>{c.recordedCode}: <b dir="ltr">{span.error_code || c.unknown}</b></span>
      <span>{c.retryCount}: {number(span.retry_count, english)}</span>
      {span.http_status !== null && <span>{c.status}: {span.http_status}</span>}
      {span.exception_type && <span>{c.errorType}: <b dir="ltr">{span.exception_type}</b></span>}
      {span.source_location && <span>{c.source}: <b dir="ltr">{span.source_location}</b></span>}
      {crossClockParent && <span>{c.crossClockTiming}</span>}
      {span.clock_domain === "client" && <strong className="diagnostics-trace-open-note">{c.clientReceiptNote}</strong>}
      {span.ended_at === null && <strong className="diagnostics-trace-open-note">{isOpenRoot ? c.openRoot : c.openSpan}</strong>}
      <strong className="diagnostics-trace-span-assessment">{c.perSpanEvidence}</strong>
      <span><b>{c.cause}:</b> {span.exception_type && span.source_location ? `${span.exception_type} at ${span.source_location}; ${c.unknownEvidence}` : c.unknownEvidence}</span>
      <span><b>{c.recommendation}:</b> {c.perSpanRecommendation}</span>
    </div>}
    {childrenSpans.length > 0 && <ol className="diagnostics-waterfall-children">{childrenSpans.map((child) => <TraceSpanRow key={`${child.clock_domain}:${child.span_id}:${child.event_id}`} span={child} depth={depth + 1} total={total} english={english} childrenSpans={lane.children.get(child) ?? []} crossClockParent={lane.crossClockParents.get(child)} lane={lane} />)}</ol>}
  </li>;
}

function StatusBadge({ value }: { value: string }) {
  const { c } = useTraceCopy();
  const label = (c.outcomes as Readonly<Record<string, string>>)[value] ?? value.replaceAll("_", " ");
  return <span className={`diagnostics-badge diagnostics-badge--${value.replace(/[^a-z0-9_-]/giu, "-")}`}>{label}</span>;
}
