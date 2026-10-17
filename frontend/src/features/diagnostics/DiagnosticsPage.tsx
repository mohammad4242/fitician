import { formatTehranDateTimeForLocale } from "@fitician/core";
import { useCallback, useEffect, useMemo, useState, type FormEvent, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { AuthenticatedHeader } from "../../shared/AuthenticatedHeader";
import { AppErrorNotice } from "../../shared/AppErrorNotice";
import {
  getDiagnosticAlerts,
  getDiagnosticInfrastructure,
  type InfrastructureSnapshot,
  getDiagnosticEvents,
  getDiagnosticGenerations,
  getDiagnosticIssue,
  getDiagnosticIssues,
  getDiagnosticsOverview,
  updateDiagnosticIssue,
  type DiagnosticAlert,
  type DiagnosticEvent,
  type DiagnosticGenerationMetrics,
  type DiagnosticIssue,
  type DiagnosticIssueDetail,
  type DiagnosticIssueFilters,
  type DiagnosticOverview,
  type DiagnosticStatus,
} from "./api";
import "./diagnostics.css";

const tabs = ["overview", "issues", "events", "generations", "infrastructure", "alerts"] as const;
type DiagnosticTab = (typeof tabs)[number];
const hoursChoices = [1, 24, 168, 720] as const;

const words = {
  fa: {
    title: "لاگینگ و دیباگینگ",
    intro: "نشانه‌های فنی ثبت‌شده را بررسی و دسته‌بندی کن. گزارش‌ها ممکن است ناقص باشند و علت قطعی را نشان ندهند.",
    overview: "نمای کلی", issues: "مسئله‌ها", events: "رویدادها", generations: "تولید برنامه", infrastructure: "زیرساخت", alerts: "هشدارها",
    hours: "بازه زمانی", hour: "۱ ساعت", day: "۲۴ ساعت", week: "۷ روز", month: "۳۰ روز",
    failures: "رخدادهای خطا", criticalFailures: "خطاهای بحرانی", newIssues: "مسئله‌های جدید", affectedUsers: "کاربران متأثر", errorRate: "نرخ خطای سرور",
    eventCount: "رویدادهای بازه", issueCount: "مسئله‌های دیده‌شده در بازه", httpSuccess: "پاسخ‌های موفق HTTP", httpFailure: "پاسخ‌های ناموفق HTTP",
    trend: "روند خطاها و عملیات", trendNote: "نمودار از تمام نتایج ثبت‌شده در بازهٔ انتخاب‌شده محاسبه می‌شود.",
    platforms: "تفکیک پلتفرم‌ها", sample: "ثبت‌شده در بازه: {{count}} رویداد", noEvents: "در این صفحه رویدادی ثبت نشده است.",
    older: "قدیمی‌تر", newer: "جدیدتر", unknown: "نامشخص", infraNote: "نتایج probe و وضعیت صف‌ها فقط شواهد عملیاتی محدود هستند؛ دسترسی به سرویس موفقیت عملیات تجاری را ثابت نمی‌کند.",
    latestInfraEvents: "رویدادهای ثبت‌شده با برچسب زیرساخت", category: "دسته", operation: "عملیات", stage: "مرحله", status: "وضعیت", severity: "شدت", platform: "پلتفرم",
    component: "بخش", code: "کد خطا", requestId: "شناسه درخواست", userId: "شناسه کاربر", version: "نسخه", build: "ساخت", errorType: "نوع خطا", source: "محل ثبت", lastSeen: "آخرین مشاهده", firstSeen: "نخستین مشاهده", count: "تعداد", regressions: "بازگشت پس از رفع", lastAlert: "آخرین هشدار", time: "زمان", outcome: "نتیجه", duration: "مدت (میلی‌ثانیه)", issue: "مسئله", reason: "دلیل",
    loading: "در حال دریافت داده‌های عیب‌یابی…", loadFailed: "داده‌ها دریافت نشدند.", retry: "تلاش دوباره", emptyIssues: "مسئله‌ای با این فیلترها پیدا نشد.", emptyEvents: "رویدادی با این فیلترها پیدا نشد.", emptyAlerts: "هشداری ثبت نشده است.", emptyGenerations: "رویداد تولیدی در این بازه ثبت نشده است.",
    previous: "قبلی", next: "بعدی", filters: "فیلترها", applyFilters: "اعمال فیلترها", clearFilters: "پاک‌کردن فیلترها", search: "جست‌وجوی کد خطا", sort: "مرتب‌سازی", lastSeenSort: "آخرین مشاهده", firstSeenSort: "نخستین مشاهده", countSort: "بیشترین تکرار", severitySort: "شدت",
    all: "همه", new: "جدید", investigating: "در حال بررسی", resolved: "رفع‌شده", ignored: "نادیده‌گرفته‌شده", critical: "بحرانی", error: "خطا", warning: "هشدار", info: "اطلاعاتی", likely: "محتمل", confirmed: "تأییدشده",
    backToIssues: "بازگشت به فهرست مسئله‌ها", issueDetail: "جزئیات مسئله", confidence: "میزان اطمینان", confidenceUnknown: "نامشخص: شواهد کافی برای تعیین علت وجود ندارد.", confidenceLikely: "محتمل: شواهد به یک ارتباط احتمالی اشاره می‌کنند، اما علت تأیید نشده است.", confidenceConfirmed: "تأییدشده: این دسته‌بندی بر پایه شواهد بررسی‌شده ثبت شده است.", confidenceCaution: "میزان اطمینان، علت قطعی را به‌تنهایی ثابت نمی‌کند.", taxonomy: "راهنمای دسته‌بندی", timeline: "رویدادهای اخیر", history: "تاریخچه وضعیت و یادداشت‌ها", updateStatus: "ثبت تغییر وضعیت", note: "یادداشت مدیر (اختیاری)", notePlaceholder: "دلیل بررسی یا تغییر وضعیت را بنویس…", save: "ثبت", saving: "در حال ثبت…", saved: "تغییر وضعیت ثبت شد.", noHistory: "تغییری در وضعیت ثبت نشده است.", noTimeline: "رویدادی برای این مسئله ثبت نشده است.", recentBuilds: "نسخه‌ها و ساخت‌های اخیر", relatedRequest: "دیدن رویدادهای همین درخواست", viewUser: "نمایش کاربر", viewIssue: "نمایش مسئله", noBuild: "نسخه یا شماره ساخت ثبت نشده است.",
    generationsHeading: "نتیجه تولید برنامه‌ها", generationNote: "نسبت موفقیت فقط از رویدادهای پایانی ثبت‌شده محاسبه شده است.", terminal: "رویدادهای پایانی", successes: "موفق یا استفاده مجدد", successRate: "نرخ موفقیت ثبت‌شده", noDenominator: "محاسبه نمی‌شود؛ رویداد پایانی ثبت نشده است.",
    statusUnknown: "وضعیت نامشخص", filteredPage: "فیلترها از API اعمال شده‌اند. صفحه‌بندی بر اساس تعداد ردیف‌های برگشتی است.", pager: "صفحه‌بندی", requestFilter: "شناسه درخواست", issueFilter: "شناسه مسئله", operationId: "شناسه عملیات", userFilter: "شناسه کاربر", errorCodeFilter: "کد خطا", versionFilter: "نسخه", statusFilter: "وضعیت", categoryFilter: "دسته", severityFilter: "شدت", platformFilter: "پلتفرم", componentFilter: "بخش",
    categories: { application_bug: "خطای برنامه", api_failure: "خطای درخواست API", database_failure: "خطای پایگاه داده", infrastructure_failure: "خطای زیرساخت", provider_failure: "خطای سرویس‌دهنده", engine_validation: "اعتبارسنجی تولید", invalid_input: "ورودی نامعتبر", business_rejection: "رد عملیات", quota_limit: "سقف استفاده", safety_restriction: "محدودیت ایمنی", auth_failure: "خطای احراز هویت", client_runtime: "خطای زمان اجرای برنامه", job_failure: "خطای کار پس‌زمینه", interrupted: "عملیات متوقف‌شده", unknown: "دسته‌بندی نامشخص" },
    categoryNotes: { application_bug: "رفتار خطادار از بخش برنامه ثبت شده است.", api_failure: "درخواست به یک API با خطا پایان یافته است.", database_failure: "رویداد به پایگاه داده نسبت داده شده است.", infrastructure_failure: "رویداد با زیرساخت مرتبط شده است.", provider_failure: "رویداد از مسیر یک سرویس‌دهنده آمده است.", engine_validation: "خروجی تولیدشده از بررسی اعتبارسنجی عبور نکرده است.", invalid_input: "ورودی با قرارداد مورد انتظار سازگار نبوده است.", business_rejection: "قواعد کسب‌وکار عملیات را نپذیرفته‌اند.", quota_limit: "سقف استفاده مانع ادامه عملیات شده است.", safety_restriction: "محدودیت ایمنی اعمال شده است.", auth_failure: "احراز هویت یا دسترسی درخواست با خطا روبه‌رو شده است.", client_runtime: "خطایی از زمان اجرای برنامه ثبت شده است.", job_failure: "یک کار پس‌زمینه با خطا پایان یافته است.", interrupted: "عملیات پیش از پایان متوقف شده است.", unknown: "سامانه دسته‌بندی مشخصی برای این رویداد ثبت نکرده است." },
    outcomes: { success: "موفق", failure: "ناموفق", timeout: "پایان مهلت", cancelled: "لغوشده", reused: "استفاده مجدد", pending_review: "در انتظار بررسی", blocked: "مسدودشده", started: "آغازشده", stage: "مرحله‌ای", unknown: "نامشخص" },
    alertReasons: { new_critical: "خطای بحرانی تازه", error_threshold: "تکرار خطا از آستانه گذشت", unknown: "دلیل ثبت‌شده" },
  },
  en: {
    title: "Logging & Debugging",
    intro: "Review and classify recorded technical signals. Reports may be incomplete and do not establish a root cause.",
    overview: "Overview", issues: "Issues", events: "Events", generations: "Generations", infrastructure: "Infrastructure", alerts: "Alerts",
    hours: "Time window", hour: "1 hour", day: "24 hours", week: "7 days", month: "30 days",
    failures: "Recorded failures", criticalFailures: "Critical failures", newIssues: "New issues", affectedUsers: "Affected users", errorRate: "Server error rate",
    eventCount: "Events in window", issueCount: "Issues seen in window", httpSuccess: "Successful HTTP responses", httpFailure: "Failed HTTP responses",
    trend: "Operation trend", trendNote: "Computed from all recorded outcomes in the selected window.",
    platforms: "Platforms in recent page", sample: "Recorded in window: {{count}} outcomes", noEvents: "No events were returned for this page.",
    older: "Older", newer: "Newer", unknown: "Unknown", infraNote: "Read-only probes and durable queue counts are limited operational evidence. Reachability does not prove a successful business operation.",
    latestInfraEvents: "Events tagged as infrastructure", category: "Category", operation: "Operation", stage: "Stage", status: "Status", severity: "Severity", platform: "Platform",
    component: "Component", code: "Error code", requestId: "Request ID", userId: "User ID", version: "Version", build: "Build", errorType: "Error type", source: "Source", lastSeen: "Last seen", firstSeen: "First seen", count: "Count", regressions: "Regressions", lastAlert: "Last alert", time: "Time", outcome: "Outcome", duration: "Duration (ms)", issue: "Issue", reason: "Reason",
    loading: "Loading diagnostics…", loadFailed: "The data could not be loaded.", retry: "Try again", emptyIssues: "No issues match these filters.", emptyEvents: "No events match these filters.", emptyAlerts: "No alerts have been recorded.", emptyGenerations: "No generation events were recorded in this window.",
    previous: "Previous", next: "Next", filters: "Filters", applyFilters: "Apply filters", clearFilters: "Clear filters", search: "Search error code", sort: "Sort", lastSeenSort: "Last seen", firstSeenSort: "First seen", countSort: "Most occurrences", severitySort: "Severity",
    all: "All", new: "New", investigating: "Investigating", resolved: "Resolved", ignored: "Ignored", critical: "Critical", error: "Error", warning: "Warning", info: "Info", likely: "Likely", confirmed: "Confirmed",
    backToIssues: "Back to issues", issueDetail: "Issue details", confidence: "Confidence", confidenceUnknown: "Unknown: there is not enough evidence to identify a cause.", confidenceLikely: "Likely: evidence suggests a possible relation, but the cause is unconfirmed.", confidenceConfirmed: "Confirmed: this classification is recorded from reviewed evidence.", confidenceCaution: "Confidence alone does not establish a root cause.", taxonomy: "Classification guide", timeline: "Recent events", history: "Status history and notes", updateStatus: "Record status change", note: "Admin note (optional)", notePlaceholder: "Add context for this review or status change…", save: "Save", saving: "Saving…", saved: "Status change recorded.", noHistory: "No status changes have been recorded.", noTimeline: "No events have been recorded for this issue.", recentBuilds: "Recent versions and builds", relatedRequest: "View events for this request", viewUser: "View user", viewIssue: "View issue", noBuild: "No version or build was recorded.",
    generationsHeading: "Program generation outcomes", generationNote: "Success rates use recorded terminal events only.", terminal: "Terminal events", successes: "Successful or reused", successRate: "Recorded success rate", noDenominator: "Not calculated; no terminal events were recorded.",
    statusUnknown: "Status unknown", filteredPage: "Filters are applied by the API. Pages advance by the number of returned rows.", pager: "Pagination", requestFilter: "Request ID", issueFilter: "Issue ID", operationId: "Operation ID", userFilter: "User ID", errorCodeFilter: "Error code", versionFilter: "Version", statusFilter: "Status", categoryFilter: "Category", severityFilter: "Severity", platformFilter: "Platform", componentFilter: "Component",
    categories: { application_bug: "Application bug", api_failure: "API failure", database_failure: "Database failure", infrastructure_failure: "Infrastructure failure", provider_failure: "Provider failure", engine_validation: "Generation validation", invalid_input: "Invalid input", business_rejection: "Business rejection", quota_limit: "Quota limit", safety_restriction: "Safety restriction", auth_failure: "Authentication failure", client_runtime: "Client runtime", job_failure: "Background job failure", interrupted: "Interrupted", unknown: "Unknown category" },
    categoryNotes: { application_bug: "A failure was recorded in application code.", api_failure: "An API request ended with an error.", database_failure: "The event is classified as database-related.", infrastructure_failure: "The event is classified as infrastructure-related.", provider_failure: "The event came through a provider path.", engine_validation: "Generated output did not pass validation.", invalid_input: "Input did not match the expected contract.", business_rejection: "Business rules rejected the operation.", quota_limit: "A usage limit prevented the operation.", safety_restriction: "A safety restriction was applied.", auth_failure: "Request authentication or access failed.", client_runtime: "A client runtime error was recorded.", job_failure: "A background job ended with an error.", interrupted: "The operation stopped before completion.", unknown: "No category was recorded for this event." },
    outcomes: { success: "Success", failure: "Failure", timeout: "Timeout", cancelled: "Cancelled", reused: "Reused", pending_review: "Pending review", blocked: "Blocked", started: "Started", stage: "Stage", unknown: "Unknown" },
    alertReasons: { new_critical: "New critical issue", error_threshold: "Error threshold reached", unknown: "Recorded reason" },
  },
} as const;

type Copy = (typeof words)["en"];

function useCopy() {
  const { i18n } = useTranslation();
  const english = i18n.resolvedLanguage === "en";
  return { c: (english ? words.en : words.fa) as Copy, english, locale: english ? "en" as const : "fa" as const };
}

function safeTab(value: string | null, search: URLSearchParams): DiagnosticTab {
  if (tabs.includes(value as DiagnosticTab)) return value as DiagnosticTab;
  if (search.has("issue")) return "issues";
  if (search.has("request_id")) return "events";
  return "overview";
}

function useRemote<T>(load: () => Promise<T>, key: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    void load().then((result) => {
      if (active) { setData(result); setError(null); }
    }).catch((cause: unknown) => {
      if (active) setError(cause);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [key, load, retry]);
  return { data, error, loading, retry: () => setRetry((value) => value + 1) };
}

function dateTime(value: string | null | undefined, english: boolean): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return formatTehranDateTimeForLocale(parsed.toISOString(), english ? "en-US" : "fa-IR");
}

function number(value: number, english: boolean): string {
  return value.toLocaleString(english ? "en-US" : "fa-IR");
}

function lookup<T extends string>(map: Readonly<Record<string, string>>, value: T): string {
  return map[value] ?? value.replaceAll("_", " ");
}

function setParam(search: URLSearchParams, key: string, value: string | null): URLSearchParams {
  const next = new URLSearchParams(search);
  if (value === null || value === "") next.delete(key);
  else next.set(key, value);
  return next;
}

export function DiagnosticsPage() {
  const { c, english } = useCopy();
  const [search, setSearch] = useSearchParams();
  const tab = safeTab(search.get("tab"), search);
  const hoursRaw = Number(search.get("hours") ?? 24);
  const hours = hoursChoices.includes(hoursRaw as (typeof hoursChoices)[number]) ? hoursRaw : 24;

  const selectTab = (nextTab: DiagnosticTab) => {
    const next = setParam(search, "tab", nextTab);
    setSearch(next);
  };
  const onTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const right = english ? 1 : -1;
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (index + right + tabs.length) % tabs.length;
    else if (event.key === "ArrowLeft") nextIndex = (index - right + tabs.length) % tabs.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = tabs.length - 1;
    if (nextIndex !== null) {
      event.preventDefault();
      const nextTab = tabs[nextIndex]!;
      selectTab(nextTab);
      document.getElementById(`diagnostics-tab-${nextTab}`)?.focus();
    }
  };
  const onHours = (value: number) => {
    const next = setParam(search, "hours", value === 24 ? null : String(value));
    setSearch(next);
  };

  return (
    <>
    <AuthenticatedHeader />
    <main className="diagnostics-page">
      <div className="diagnostics-page__inner">
        <header className="diagnostics-hero">
          <div className="diagnostics-hero__mark" aria-hidden="true"><span /></div>
          <div className="diagnostics-hero__copy">
            <p className="diagnostics-kicker">FITICIAN / OPERATIONS</p>
            <h1>{c.title}</h1>
            <p>{c.intro}</p>
          </div>
          {(tab === "overview" || tab === "generations") && (
            <label className="diagnostics-window">
              <span>{c.hours}</span>
              <select aria-label={c.hours} onChange={(event) => onHours(Number(event.currentTarget.value))} value={hours}>
                <option value={1}>{c.hour}</option><option value={24}>{c.day}</option><option value={168}>{c.week}</option><option value={720}>{c.month}</option>
              </select>
            </label>
          )}
        </header>

        <div className="diagnostics-tabs" role="tablist" aria-label={c.title}>
          {tabs.map((name, index) => (
            <button
              aria-controls={`diagnostics-panel-${name}`}
              aria-selected={tab === name}
              className="diagnostics-tab"
              id={`diagnostics-tab-${name}`}
              key={name}
              onClick={() => selectTab(name)}
              onKeyDown={(event) => onTabKeyDown(event, index)}
              role="tab"
              tabIndex={tab === name ? 0 : -1}
              type="button"
            >{c[name]}</button>
          ))}
        </div>

        <section aria-labelledby={`diagnostics-tab-${tab}`} className="diagnostics-panel" id={`diagnostics-panel-${tab}`} role="tabpanel" tabIndex={0}>
          {tab === "overview" && <OverviewPanel hours={hours} />}
          {tab === "issues" && <IssuesPanel search={search} setSearch={setSearch} />}
          {tab === "events" && <EventsPanel search={search} setSearch={setSearch} />}
          {tab === "generations" && <GenerationsPanel hours={hours} />}
          {tab === "infrastructure" && <InfrastructurePanel search={search} setSearch={setSearch} />}
          {tab === "alerts" && <AlertsPanel search={search} setSearch={setSearch} />}
        </section>
      </div>
    </main>
    </>
  );
}

function StatusMessage({ loading, error, retry }: { loading: boolean; error: unknown; retry: () => void }) {
  const { c, locale } = useCopy();
  if (loading) return <p className="diagnostics-state" role="status">{c.loading}</p>;
  if (error !== null) return (
    <div className="diagnostics-error">
      <AppErrorNotice audience="admin" context="generic" error={error} locale={locale} />
      <button className="diagnostics-button diagnostics-button--quiet" onClick={retry} type="button">{c.retry}</button>
    </div>
  );
  return null;
}

function OverviewPanel({ hours }: { hours: number }) {
  const { c, english } = useCopy();
  const overviewLoad = useCallback(() => getDiagnosticsOverview(hours), [hours]);
  const overview = useRemote<DiagnosticOverview>(overviewLoad, `overview-${hours}`);
  return (
    <div id="diagnostics-overview-content" className="diagnostics-stack">
      <StatusMessage loading={overview.loading} error={overview.error} retry={overview.retry} />
      {overview.data && (
        <>
          <div className="diagnostics-metrics">
            <MetricCard label={c.failures} value={number(overview.data.failure_count, english)} tone="coral" />
            <MetricCard label={c.criticalFailures} value={number(overview.data.critical_count, english)} tone="coral" />
            <MetricCard label={c.newIssues} value={number(overview.data.new_issue_count, english)} tone="saffron" />
            <MetricCard label={c.affectedUsers} value={number(overview.data.affected_users, english)} tone="quiet" />
            <MetricCard label={c.errorRate} value={overview.data.error_rate === null ? "—" : `${Math.round(overview.data.error_rate * 1000) / 10}%`} tone="quiet" />
            <MetricCard label={c.eventCount} value={number(overview.data.event_count, english)} tone="aqua" />
            <MetricCard label={c.issueCount} value={number(overview.data.issue_count, english)} tone="saffron" />
            <MetricCard label={c.httpSuccess} value={number(overview.data.http_response_count.success, english)} tone="quiet" />
            <MetricCard label={c.httpFailure} value={number(overview.data.http_response_count.failure, english)} tone="coral" />
          </div>
          <div className="diagnostics-grid diagnostics-grid--overview">
            <section className="diagnostics-card diagnostics-chart-card">
              <div className="diagnostics-card__heading"><div><p className="diagnostics-label">01 / SIGNAL</p><h2>{c.trend}</h2></div><span className="diagnostics-sample">{c.sample.replace("{{count}}", number((overview.data.trend ?? []).reduce((sum, point) => sum + point.count, 0), english))}</span></div>
              <EventTrend data={overview.data.trend ?? []} hours={hours} />
              <p className="diagnostics-caption">{c.trendNote}</p>
            </section>
            <section className="diagnostics-card diagnostics-platform-card">
              <div className="diagnostics-card__heading"><div><p className="diagnostics-label">02 / CLIENT MIX</p><h2>{c.platforms}</h2></div></div>
              <p className="diagnostics-caption">{c.sample.replace("{{count}}", number((overview.data.trend ?? []).reduce((sum, point) => sum + point.count, 0), english))}</p>
              <PlatformMix data={overview.data.platforms ?? []} />
            </section>
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone: string }) {
  return <article className={`diagnostics-metric diagnostics-metric--${tone}`}><span>{label}</span><strong>{value}</strong><i aria-hidden="true" /></article>;
}

function EventTrend({ data, hours }: { data: readonly { readonly timestamp: string; readonly count: number }[]; hours: number }) {
  const { c, english } = useCopy();
  const points = useMemo(() => {
    const bins = Array.from({ length: 12 }, () => 0);
    const windowMs = hours * 3_600_000;
    const start = Date.now() - windowMs;
    for (const point of data) {
      const timestamp = Date.parse(point.timestamp);
      if (!Number.isFinite(timestamp)) continue;
      const index = Math.max(0, Math.min(11, Math.floor((timestamp - start) / windowMs * 12)));
      bins[index] = bins[index]! + point.count;
    }
    return bins;
  }, [data, hours]);
  const max = Math.max(1, ...points);
  const coordinates = points.map((value, index) => ({ x: english ? 24 + index * (672 / Math.max(1, points.length - 1)) : 696 - index * (672 / Math.max(1, points.length - 1)), y: 158 - value / max * 122, value }));
  const line = coordinates.map(({ x, y }, index) => `${index === 0 ? "M" : "L"}${x},${y}`).join(" ");
  const area = `${line} L${coordinates.at(-1)?.x ?? 695},166 L${coordinates[0]?.x ?? 24},166 Z`;
  return (
    <div className="diagnostics-trend">
      <svg aria-label={`${c.trend}: ${c.sample.replace("{{count}}", number(data.reduce((sum, point) => sum + point.count, 0), english))}`} className="diagnostics-trend__svg" role="img" viewBox="0 0 720 192">
        <title>{c.trend}</title>
        {[36, 97, 158].map((y) => <line className="diagnostics-trend__grid" key={y} x1="24" x2="696" y1={y} y2={y} />)}
        <path className="diagnostics-trend__area" d={area} />
        <path className="diagnostics-trend__line" d={line} />
        {coordinates.map(({ x, y, value }, index) => <circle aria-label={`${index + 1}: ${number(value, english)}`} className="diagnostics-trend__point" key={x} r="3.5" cx={x} cy={y} />)}
      </svg>
      <div className="diagnostics-trend__axis"><span>{c.older}</span><span>{c.newer}</span></div>
      {data.length === 0 && <p className="diagnostics-empty">{c.noEvents}</p>}
    </div>
  );
}

function PlatformMix({ data }: { data: readonly { readonly platform: string; readonly count: number }[] }) {
  const { c, english } = useCopy();
  const total = data.reduce((sum, row) => sum + row.count, 0);
  if (!total) return <p className="diagnostics-empty">{c.noEvents}</p>;
  return <ul className="diagnostics-platform-list">{data.map(({platform, count}) => <li key={platform}><span>{platform.replaceAll("_", " ")}</span><strong>{number(count, english)}</strong><small>{Math.round(count * 100 / total)}%</small></li>)}</ul>;
}

function queryValue(search: URLSearchParams, key: string): string | undefined {
  const value = search.get(key)?.trim();
  return value ? value : undefined;
}

function IssuesPanel({ search, setSearch }: { search: URLSearchParams; setSearch: (next: URLSearchParams) => void }) {
  const { c } = useCopy();
  const issueId = search.get("issue");
  const offset = Math.max(0, Number(search.get("offset") ?? 0) || 0);
  const filters = useMemo<DiagnosticIssueFilters>(() => ({
    limit: 20, hours: Number(search.get("hours") ?? 24),
    offset,
    platform: queryValue(search, "platform"),
    component: queryValue(search, "component"),
    severity: queryValue(search, "severity"),
    category: queryValue(search, "category"),
    status: queryValue(search, "status"),
    error_code: queryValue(search, "error_code"),
    user_id: queryValue(search, "user_id"),
    request_id: queryValue(search, "request_id"),
    version: queryValue(search, "version"),
    q: queryValue(search, "q"),
    sort: (search.get("sort") as DiagnosticIssueFilters["sort"]) || "last_seen",
  }), [offset, search]);
  const loadIssues = useCallback(() => getDiagnosticIssues(filters), [filters]);
  const list = useRemote<DiagnosticIssue[]>(loadIssues, JSON.stringify(filters));
  const [detailRetry, setDetailRetry] = useState(0);
  const loadDetail = useCallback(() => issueId ? getDiagnosticIssue(issueId) : Promise.resolve(null), [issueId]);
  const detail = useRemote<DiagnosticIssueDetail | null>(loadDetail, `issue-${issueId ?? "none"}-${detailRetry}`);
  const changeSearch = (patch: Record<string, string | null>, clearIssue = false) => {
    const next = new URLSearchParams(search);
    next.set("tab", "issues");
    if (clearIssue) next.delete("issue");
    for (const [key, value] of Object.entries(patch)) {
      if (value === null || value === "") next.delete(key); else next.set(key, value);
    }
    setSearch(next);
  };
  const onFilter = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = new URLSearchParams(search);
    next.set("tab", "issues"); next.delete("issue"); next.delete("offset");
    for (const key of ["q", "platform", "component", "severity", "category", "status", "error_code", "user_id", "request_id", "version", "sort"]) {
      const value = String(form.get(key) ?? "").trim();
      if (value && !(key === "sort" && value === "last_seen")) next.set(key, value); else next.delete(key);
    }
    setSearch(next);
  };

  return (
    <div className="diagnostics-stack">
      {issueId ? (
        <>
          <button className="diagnostics-button diagnostics-button--quiet diagnostics-back" onClick={() => changeSearch({}, true)} type="button">← {c.backToIssues}</button>
          <StatusMessage loading={detail.loading} error={detail.error} retry={detail.retry} />
          {detail.data && <IssueDetail detail={detail.data} onSaved={() => setDetailRetry((value) => value + 1)} />}
        </>
      ) : (
        <>
          <form className="diagnostics-card diagnostics-filters" onSubmit={onFilter}>
            <div className="diagnostics-card__heading"><div><p className="diagnostics-label">03 / TRIAGE</p><h2>{c.issues}</h2></div><span className="diagnostics-caption">{c.filteredPage}</span></div>
            <div className="diagnostics-filter-grid">
              <Field label={c.search} name="q" defaultValue={search.get("q") ?? ""} />
              <SelectField label={c.platformFilter} name="platform" value={search.get("platform") ?? ""} options={platformOptions()} />
              <Field label={c.componentFilter} name="component" defaultValue={search.get("component") ?? ""} />
              <SelectField label={c.severityFilter} name="severity" value={search.get("severity") ?? ""} options={severityOptions(c)} />
              <SelectField label={c.categoryFilter} name="category" value={search.get("category") ?? ""} options={categoryOptions(c)} />
              <SelectField label={c.statusFilter} name="status" value={search.get("status") ?? ""} options={statusOptions(c)} />
              <Field label={c.errorCodeFilter} name="error_code" defaultValue={search.get("error_code") ?? ""} />
              <Field label={c.userFilter} name="user_id" defaultValue={search.get("user_id") ?? ""} dir="ltr" />
              <Field label={c.requestFilter} name="request_id" defaultValue={search.get("request_id") ?? ""} dir="ltr" />
              <Field label={c.versionFilter} name="version" defaultValue={search.get("version") ?? ""} dir="ltr" />
              <SelectField label={c.sort} name="sort" value={search.get("sort") ?? "last_seen"} options={[["last_seen", c.lastSeenSort], ["first_seen", c.firstSeenSort], ["count", c.countSort], ["severity", c.severitySort]]} />
            </div>
            <div className="diagnostics-filter-actions"><button className="diagnostics-button" type="submit">{c.applyFilters}</button><button className="diagnostics-button diagnostics-button--quiet" type="button" onClick={() => changeSearch({ q: null, platform: null, component: null, severity: null, category: null, status: null, error_code: null, user_id: null, request_id: null, version: null, sort: null, offset: null })}>{c.clearFilters}</button></div>
          </form>
          <StatusMessage loading={list.loading} error={list.error} retry={list.retry} />
          {list.data && (
            <>
              <IssueTable issues={list.data} onOpen={(id) => changeSearch({ issue: id }, false)} />
              {list.data.length === 0 && <p className="diagnostics-empty">{c.emptyIssues}</p>}
              <Pager offset={offset} size={list.data.length} step={20} onMove={(value) => changeSearch({ offset: String(value) })} />
            </>
          )}
        </>
      )}
    </div>
  );
}

function IssueTable({ issues, onOpen }: { issues: readonly DiagnosticIssue[]; onOpen: (id: string) => void }) {
  const { c, english } = useCopy();
  return (
    <div className="diagnostics-table-wrap"><table className="diagnostics-table">
      <thead><tr><th>{c.issue}</th><th>{c.status}</th><th>{c.severity}</th><th>{c.count}</th><th>{c.platform}</th><th>{c.lastSeen}</th></tr></thead>
      <tbody>{issues.map((issue) => <tr key={issue.id}>
        <td><button className="diagnostics-link-button" onClick={() => onOpen(issue.id)} type="button"><strong>{categoryLabel(c, issue.category)}</strong><small dir="ltr">{issue.error_code}</small><small>{issue.component} · {issue.operation} · {issue.stage}</small></button></td>
        <td><StatusBadge value={issue.status} /></td><td><StatusBadge value={issue.severity} /></td><td>{number(issue.count, english)}</td><td dir="ltr">{issue.platform}</td><td>{dateTime(issue.last_seen, english)}</td>
      </tr>)}</tbody>
    </table></div>
  );
}

function IssueDetail({ detail, onSaved }: { detail: DiagnosticIssueDetail; onSaved: () => void }) {
  const { c, english, locale } = useCopy();
  const { issue, events, status_history: history } = detail;
  const [status, setStatus] = useState<DiagnosticStatus>(issue.status);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => { setStatus(issue.status); }, [issue.id, issue.status]);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setSaving(true); setSaveError(null); setSaved(false);
    void updateDiagnosticIssue(issue.id, status, note).then(() => {
      setSaved(true); setNote(""); onSaved();
    }).catch((error: unknown) => setSaveError(error)).finally(() => setSaving(false));
  };
  const versions = [...new Set(events.flatMap((event) => [event.version, event.build].filter((value): value is string => Boolean(value))))];
  const confidenceDescription = issue.confidence === "unknown" ? c.confidenceUnknown : issue.confidence === "likely" ? c.confidenceLikely : c.confidenceConfirmed;
  return (
    <div className="diagnostics-stack">
      <section className="diagnostics-card diagnostics-issue-hero">
        <div><p className="diagnostics-label">{issue.component} / {issue.operation} / {issue.stage}</p><h2>{categoryLabel(c, issue.category)}</h2><p>{categoryNote(c, issue.category)}</p></div>
        <div className="diagnostics-badge-pair"><StatusBadge value={issue.severity} /><StatusBadge value={issue.status} /></div>
      </section>
      <div className="diagnostics-detail-grid">
        <section className="diagnostics-card diagnostics-classification">
          <h3>{c.taxonomy}</h3>
          <p>{c.confidence}: <StatusBadge value={issue.confidence} /></p>
          <p>{confidenceDescription}</p><small>{c.confidenceCaution}</small>
          <dl className="diagnostics-definition-list">
            <div><dt>{c.code}</dt><dd dir="ltr">{issue.error_code}</dd></div>
            <div><dt>{c.errorType}</dt><dd dir="ltr">{issue.exception_type ?? "—"}</dd></div>
            <div><dt>{c.source}</dt><dd dir="ltr">{issue.source_location ?? "—"}</dd></div>
            <div><dt>{c.platform}</dt><dd dir="ltr">{issue.platform}</dd></div>
            <div><dt>{c.firstSeen}</dt><dd>{dateTime(issue.first_seen, english)}</dd></div>
            <div><dt>{c.lastSeen}</dt><dd>{dateTime(issue.last_seen, english)}</dd></div>
            <div><dt>{c.count}</dt><dd>{number(issue.count, english)}</dd></div>
            <div><dt>{c.regressions}</dt><dd>{number(issue.regression_count, english)}</dd></div>
          </dl>
        </section>
        <section className="diagnostics-card diagnostics-status-form">
          <h3>{c.updateStatus}</h3>
          <form onSubmit={submit}>
            <label>{c.status}<select aria-label={c.status} value={status} onChange={(event) => setStatus(event.currentTarget.value as DiagnosticStatus)}>{statusOptions(c).filter(([value]) => value !== "").map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label>{c.note}<textarea maxLength={1000} onChange={(event) => setNote(event.currentTarget.value)} placeholder={c.notePlaceholder} value={note} /></label>
            <button className="diagnostics-button" disabled={saving} type="submit">{saving ? c.saving : c.save}</button>
          </form>
          {saveError !== null && <AppErrorNotice audience="admin" context="generic" error={saveError} locale={locale} />}
          {saved && <p className="diagnostics-saved" role="status">{c.saved}</p>}
        </section>
      </div>
      <section className="diagnostics-card">
        <div className="diagnostics-card__heading"><div><p className="diagnostics-label">04 / HISTORY</p><h3>{c.timeline}</h3></div><span className="diagnostics-caption">{c.recentBuilds}: {versions.length ? versions.join(" · ") : c.noBuild}</span></div>
        {events.length === 0 ? <p className="diagnostics-empty">{c.noTimeline}</p> : <EventTimeline events={events} />}
      </section>
      <section className="diagnostics-card">
        <h3>{c.history}</h3>
        {history.length === 0 ? <p className="diagnostics-empty">{c.noHistory}</p> : <ol className="diagnostics-history">{history.map((item) => <li key={item.id}>
          <time>{dateTime(item.created_at, english)}</time><strong><StatusBadge value={item.previous_status} /> → <StatusBadge value={item.new_status} /></strong>
          {item.note && <p>{item.note}</p>}
          {item.actor_user_id && <Link to={`/admin/billing/users/${encodeURIComponent(item.actor_user_id)}`}>{c.viewUser}: {item.actor_user_id}</Link>}
        </li>)}</ol>}
      </section>
    </div>
  );
}

function EventTimeline({ events }: { events: readonly DiagnosticEvent[] }) {
  const { c, english } = useCopy();
  return <ol className="diagnostics-timeline">{events.map((event) => (
    <li key={event.event_id}>
      <i aria-hidden="true" />
      <div className="diagnostics-timeline__content">
        <div className="diagnostics-timeline__top"><time>{dateTime(event.timestamp, english)}</time><StatusBadge value={event.outcome} /></div>
        <strong>{event.component} · {event.operation} · {event.stage}</strong>
        <span dir="ltr">{event.error_code} · {event.http_status ?? "—"}</span>
        <div className="diagnostics-inline-meta">
          <span>{c.platform}: <b dir="ltr">{event.platform}</b></span>
          <span>{c.build}: <b dir="ltr">{event.build ?? "—"}</b></span>
          <span>{c.version}: <b dir="ltr">{event.version ?? "—"}</b></span>
          {event.resource_id && <span>{english ? "Resource" : "منبع مرتبط"}: <Link dir="ltr" to={`/admin/diagnostics?tab=events&resource_id=${encodeURIComponent(event.resource_id)}`}>{event.resource_id}</Link></span>}
          {event.input_fingerprint && <span>{english ? "Input fingerprint" : "اثر انگشت ورودی"}: <code dir="ltr">{event.input_fingerprint}</code></span>}
          {event.duration_ms !== null && <span>{c.duration}: <b>{number(event.duration_ms, english)}</b></span>}
        </div>
        {event.request_id && <Link to={`/admin/diagnostics?tab=events&request_id=${encodeURIComponent(event.request_id)}`}>{c.relatedRequest}: <span dir="ltr">{event.request_id}</span></Link>}
        {event.user_id && <Link to={`/admin/billing/users/${encodeURIComponent(event.user_id)}`}>{c.viewUser}: <span dir="ltr">{event.user_id}</span></Link>}
      </div>
    </li>
  ))}</ol>;
}

function EventsPanel({ search, setSearch }: { search: URLSearchParams; setSearch: (next: URLSearchParams) => void }) {
  const { c } = useCopy();
  const offset = Math.max(0, Number(search.get("offset") ?? 0) || 0);
  const filters = useMemo(() => ({
    limit: 50, offset, hours: Number(search.get("hours") ?? 24),
    user_id: queryValue(search, "user_id"), request_id: queryValue(search, "request_id"),
    resource_id: queryValue(search, "resource_id"),
    operation_id: queryValue(search, "operation_id"), issue_id: queryValue(search, "issue_id"),
    platform: queryValue(search, "platform"),
  }), [offset, search]);
  const load = useCallback(() => getDiagnosticEvents(filters), [filters]);
  const result = useRemote<DiagnosticEvent[]>(load, JSON.stringify(filters));
  const apply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const next = new URLSearchParams(search); next.set("tab", "events"); next.delete("offset");
    for (const key of ["platform", "user_id", "request_id", "operation_id", "resource_id", "issue_id"]) {
      const value = String(values.get(key) ?? "").trim();
      if (value) next.set(key, value); else next.delete(key);
    }
    setSearch(next);
  };
  const move = (nextOffset: number) => { const next = setParam(search, "offset", String(nextOffset)); next.set("tab", "events"); setSearch(next); };
  return <div className="diagnostics-stack">
    <form className="diagnostics-card diagnostics-filters diagnostics-filters--compact" onSubmit={apply}>
      <div className="diagnostics-card__heading"><div><p className="diagnostics-label">05 / RAW EVENTS</p><h2>{c.events}</h2></div></div>
      <div className="diagnostics-filter-grid">
        <SelectField label={c.platformFilter} name="platform" value={search.get("platform") ?? ""} options={platformOptions()} />
        <Field label={c.userFilter} name="user_id" defaultValue={search.get("user_id") ?? ""} dir="ltr" />
        <Field label={c.requestFilter} name="request_id" defaultValue={search.get("request_id") ?? ""} dir="ltr" />
        <Field label={c.operationId} name="operation_id" defaultValue={search.get("operation_id") ?? ""} dir="ltr" />
        <Field label={c.issueFilter} name="issue_id" defaultValue={search.get("issue_id") ?? ""} dir="ltr" />
      </div>
      <button className="diagnostics-button" type="submit">{c.applyFilters}</button>
    </form>
    <StatusMessage loading={result.loading} error={result.error} retry={result.retry} />
    {result.data && <>
      <p className="diagnostics-caption">{c.filteredPage}</p>
      <EventTable events={result.data} />
      {result.data.length === 0 && <p className="diagnostics-empty">{c.emptyEvents}</p>}
      <Pager offset={offset} size={result.data.length} step={50} onMove={move} />
    </>}
  </div>;
}

function EventTable({ events }: { events: readonly DiagnosticEvent[] }) {
  const { c, english } = useCopy();
  return <div className="diagnostics-table-wrap"><table className="diagnostics-table diagnostics-events-table">
    <thead><tr><th>{c.time}</th><th>{c.issue}</th><th>{c.code}</th><th>{c.operation}</th><th>{c.platform}</th><th>{c.requestId}</th><th>{c.userId}</th><th>{c.build}</th><th>{c.outcome}</th></tr></thead>
    <tbody>{events.map((event) => <tr key={event.event_id}>
      <td>{dateTime(event.timestamp, english)}</td>
      <td>{event.issue_id ? <Link to={`/admin/diagnostics?tab=issues&issue=${encodeURIComponent(event.issue_id)}`}>{c.viewIssue}</Link> : "—"}</td>
      <td><code dir="ltr">{event.error_code}</code><small>{event.exception_type ?? "—"}</small></td>
      <td><strong>{event.component}</strong><small>{event.operation} · {event.stage}</small></td>
      <td dir="ltr">{event.platform}</td>
      <td>{event.request_id ? <Link to={`/admin/diagnostics?tab=events&request_id=${encodeURIComponent(event.request_id)}`} dir="ltr">{event.request_id}</Link> : "—"}</td>
      <td>{event.user_id ? <Link to={`/admin/billing/users/${encodeURIComponent(event.user_id)}`} dir="ltr">{event.user_id}</Link> : "—"}</td>
      <td dir="ltr">{event.version ?? "—"}{event.build ? ` / ${event.build}` : ""}</td>
      <td><StatusBadge value={event.outcome} /></td>
    </tr>)}</tbody>
  </table></div>;
}

function GenerationsPanel({ hours }: { hours: number }) {
  const { c, english } = useCopy();
  const load = useCallback(() => getDiagnosticGenerations(hours), [hours]);
  const result = useRemote<DiagnosticGenerationMetrics>(load, `generation-${hours}`);
  return <div className="diagnostics-stack">
    <div className="diagnostics-card__heading"><div><p className="diagnostics-label">06 / GENERATION</p><h2>{c.generationsHeading}</h2></div></div>
    <p className="diagnostics-caption">{c.generationNote}</p>
    <StatusMessage loading={result.loading} error={result.error} retry={result.retry} />
    {result.data && result.data.operations.length === 0 && <p className="diagnostics-empty">{c.emptyGenerations}</p>}
    {result.data && <section className="diagnostics-card"><h3>{english ? "Quota records and incomplete attempts" : "ثبت سهمیه و تلاش‌های ناتمام"}</h3><dl className="diagnostics-infra-meta">{Object.entries(result.data.quota_integrity ?? {}).map(([key, value]) => <div key={key}><dt>{english ? key.replaceAll("_", " ") : ({charges: "مصرف ثبت‌شده", pending_reservations: "رزرو در انتظار تأیید", unresolved_resources: "ارجاع نیازمند بررسی"}[key] ?? key)}</dt><dd>{number(value, english)}</dd></div>)}<div><dt>{english ? "Unconfirmed outcomes" : "نتیجهٔ نامشخص"}</dt><dd>{number(result.data.incomplete_attempts ?? 0, english)}</dd></div></dl></section>}
    {result.data && (result.data.engine_versions ?? []).length > 0 && <section className="diagnostics-card"><h3>{english ? "Engine version outcomes" : "نتایج نسخه‌های موتور"}</h3><div className="diagnostics-table-wrap"><table className="diagnostics-table"><thead><tr><th>{c.operation}</th><th>{c.version}</th><th>{c.outcome}</th><th>{c.count}</th></tr></thead><tbody>{result.data.engine_versions.map((row) => <tr key={`${row.operation}-${row.version}-${row.outcome}`}><td dir="ltr">{row.operation}</td><td dir="ltr">{row.version}</td><td>{lookup(c.outcomes, row.outcome)}</td><td>{number(row.count, english)}</td></tr>)}</tbody></table></div></section>}
    {result.data && (result.data.failure_reasons ?? []).length > 0 && <section className="diagnostics-card"><h3>{english ? "Failure reasons" : "دلایل شکست"}</h3><ul>{result.data.failure_reasons.map((item) => <li key={`${item.operation}-${item.error_code}`}><Link to={`/admin/diagnostics?tab=issues&error_code=${encodeURIComponent(item.error_code)}`} dir="ltr">{item.error_code}</Link> · {number(item.count, english)}</li>)}</ul></section>}
    {result.data && <div className="diagnostics-generation-grid">{result.data.operations.map((item) => (
      <article className="diagnostics-card diagnostics-generation" key={item.operation}>
        <p className="diagnostics-label">{item.operation === "workout_generation" ? (english ? "WORKOUT" : "تمرین") : item.operation === "nutrition_generation" ? (english ? "NUTRITION" : "تغذیه") : item.operation}</p>
        <h3>{item.operation.replaceAll("_", " ")}</h3>
        <div className="diagnostics-generation__totals"><div><span>{c.terminal}</span><strong>{number(item.terminal_count, english)}</strong></div><div><span>{c.successes}</span><strong>{number(item.success_count, english)}</strong></div></div>
        <div className="diagnostics-generation__rate"><span>{c.successRate}</span><strong>{item.success_rate === null ? "—" : `${number(Math.round(item.success_rate * 100), english)}%`}</strong></div>
        {item.success_rate === null && <p className="diagnostics-caption">{c.noDenominator}</p>}
        <ul>{Object.entries(item.outcomes).map(([outcome, count]) => <li key={outcome}><span>{lookup(c.outcomes, outcome)}</span><strong>{number(count, english)}</strong></li>)}</ul>
      </article>
    ))}</div>}
  </div>;
}

function InfrastructurePanel({ search, setSearch }: { search: URLSearchParams; setSearch: (next: URLSearchParams) => void }) {
  const { c, english } = useCopy();
  const overviewLoad = useCallback(() => getDiagnosticInfrastructure(), []);
  const offset = Math.max(0, Number(search.get("offset") ?? 0) || 0);
  const eventsLoad = useCallback(() => getDiagnosticEvents({ limit: 50, offset, platform: "infrastructure" }), [offset]);
  const summary = useRemote<InfrastructureSnapshot>(overviewLoad, "infrastructure-summary");
  const events = useRemote<DiagnosticEvent[]>(eventsLoad, `infrastructure-events-${offset}`);
  const move = (nextOffset: number) => { const next = setParam(search, "offset", String(nextOffset)); next.set("tab", "infrastructure"); setSearch(next); };
  return <div className="diagnostics-stack">
    <section className="diagnostics-card diagnostics-infra-status">
      <div><p className="diagnostics-label">07 / INFRASTRUCTURE SIGNAL</p><h2>{c.infrastructure}</h2><p>{c.infraNote}</p></div>
      <strong className="diagnostics-unknown"><i aria-hidden="true" />{c.statusUnknown}</strong>
    </section>
    <StatusMessage loading={summary.loading} error={summary.error} retry={summary.retry} />
    {summary.data && <>
      <div className="diagnostics-generation-grid">{summary.data.signals.map((signal) => <article className="diagnostics-card" key={signal.component}><h3 dir="ltr">{signal.component.replaceAll("_", " ")}</h3><StatusBadge value={signal.status}/><p dir="ltr">{signal.evidence}</p><time>{dateTime(signal.observed_at, english)}</time></article>)}</div>
      <section className="diagnostics-card"><h3>{english ? "Durable job states" : "وضعیت پایدار کارها"}</h3>{Object.entries(summary.data.queues).map(([name, counts]) => <div key={name}><strong dir="ltr">{name}</strong><ul>{Object.entries(counts).map(([state, count]) => <li key={state}><span dir="ltr">{state}</span>: {number(count, english)}</li>)}</ul></div>)}</section>
    </>}

    <div className="diagnostics-card__heading"><h3>{c.latestInfraEvents}</h3></div>
    <StatusMessage loading={events.loading} error={events.error} retry={events.retry} />
    {events.data && <>
      <EventTable events={events.data} />
      {events.data.length === 0 && <p className="diagnostics-empty">{c.noEvents}</p>}
      <Pager offset={offset} size={events.data.length} step={50} onMove={move} />
    </>}
  </div>;
}

function AlertsPanel({ search, setSearch }: { search: URLSearchParams; setSearch: (next: URLSearchParams) => void }) {
  const { c, english } = useCopy();
  const offset = Math.max(0, Number(search.get("offset") ?? 0) || 0);
  const load = useCallback(() => getDiagnosticAlerts(50, offset), [offset]);
  const result = useRemote<DiagnosticAlert[]>(load, `alerts-${offset}`);
  const move = (nextOffset: number) => { const next = setParam(search, "offset", String(nextOffset)); next.set("tab", "alerts"); setSearch(next); };
  return <div className="diagnostics-stack">
    <div className="diagnostics-card__heading"><div><p className="diagnostics-label">08 / ALERTING</p><h2>{c.alerts}</h2></div></div>
    <StatusMessage loading={result.loading} error={result.error} retry={result.retry} />
    {result.data && result.data.length === 0 && <p className="diagnostics-empty">{c.emptyAlerts}</p>}
    {result.data && result.data.length > 0 && <div className="diagnostics-alert-list">{result.data.map((alert) => (
      <article className="diagnostics-card diagnostics-alert" key={alert.id}>
        <span className="diagnostics-alert__pulse" aria-hidden="true" />
        <div><p className="diagnostics-label">{dateTime(alert.created_at, english)}</p><h3>{lookup(c.alertReasons, alert.reason)}</h3><code dir="ltr">{alert.reason}</code></div>
        <Link className="diagnostics-button diagnostics-button--quiet" to={`/admin/diagnostics?tab=issues&issue=${encodeURIComponent(alert.issue_id)}`}>{c.viewIssue}</Link>
      </article>
    ))}</div>}
    <Pager offset={offset} size={result.data?.length ?? 0} step={50} onMove={move} />
  </div>;
}

function Pager({ offset, size, step, onMove }: { offset: number; size: number; step: number; onMove: (offset: number) => void }) {
  const { c } = useCopy();
  return <nav aria-label={c.pager} className="diagnostics-pager">
    <button className="diagnostics-button diagnostics-button--quiet" disabled={offset <= 0} onClick={() => onMove(Math.max(0, offset - step))} type="button">{c.previous}</button>
    <span>{size === 0 ? "0" : `${offset + 1}–${offset + size}`}</span>
    <button className="diagnostics-button diagnostics-button--quiet" disabled={size < step} onClick={() => onMove(offset + step)} type="button">{c.next}</button>
  </nav>;
}

function StatusBadge({ value }: { value: string }) {
  const { c } = useCopy();
  return <span className={`diagnostics-badge diagnostics-badge--${value.replace(/[^a-z0-9_-]/giu, "-")}`}>{typeof c[value as keyof typeof c] === "string" ? String(c[value as keyof typeof c]) : value.replaceAll("_", " ")}</span>;
}

function Field({ label, name, defaultValue, dir }: { label: string; name: string; defaultValue: string; dir?: "ltr" }) {
  return <label className="diagnostics-field">{label}<input dir={dir} defaultValue={defaultValue} name={name} /></label>;
}

function SelectField({ label, name, value, options }: { label: string; name: string; value: string; options: readonly (readonly [string, string])[] }) {
  const { c } = useCopy();
  return <label className="diagnostics-field">{label}<select defaultValue={value} key={`${name}-${value}`} name={name}><option value="">{c.all}</option>{options.map(([optionValue, optionLabel]) => <option key={optionValue} value={optionValue}>{optionLabel}</option>)}</select></label>;
}

function platformOptions(): readonly (readonly [string, string])[] {
  return ["web", "ios_pwa", "android", "ios", "backend", "worker", "database", "infrastructure", "unknown"].map((value) => [value, value.replaceAll("_", " ")] as const);
}

function severityOptions(c: Copy): readonly (readonly [string, string])[] {
  return [["critical", c.critical], ["error", c.error], ["warning", c.warning], ["info", c.info]];
}

function statusOptions(c: Copy): readonly (readonly [string, string])[] {
  return [["", c.all], ["new", c.new], ["investigating", c.investigating], ["resolved", c.resolved], ["ignored", c.ignored]];
}

function categoryOptions(c: Copy): readonly (readonly [string, string])[] {
  return Object.entries(c.categories).map(([value, label]) => [value, label] as const);
}

function categoryLabel(c: Copy, category: string): string {
  return lookup(c.categories, category);
}

function categoryNote(c: Copy, category: string): string {
  return lookup(c.categoryNotes, category);
}
