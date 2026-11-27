import { useEffect, useState } from "react";
import { request } from "../../shared/apiClient";

interface Health {
  external_states: Record<string, number>;
  native_discovery: {
    project: string; environment: string; state: "stale" | "catching_up" | "observed";
    last_error_code: string | null; last_success_at: string | null;
    watermark: string | null; imported_count: number;
  }[];
}

export function SentryHealth({ english }: { english: boolean }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let current = true;
    setFailed(false);
    void request<Health>("/api/v1/admin/diagnostics/sentry-health").then(value => {
      if (current) setHealth(value);
    }).catch(() => { if (current) setFailed(true); });
    return () => { current = false; };
  }, [revision]);
  const labels = english ? { stale: "Stale or unavailable", catching_up: "Catching up", observed: "Recent scan observed" } : { stale: "قدیمی یا در دسترس نیست", catching_up: "در حال دریافت عقب‌ماندگی", observed: "پویش اخیر ثبت شده" };
  return <section className="diagnostics-card">
    <h3>{english ? "Sentry synchronization health" : "سلامت همگام‌سازی Sentry"}</h3>
    <button type="button" onClick={() => setRevision(value => value + 1)}>{english ? "Refresh" : "تازه‌سازی"}</button>
    {failed && <p role="alert">{english ? "Sentry health could not be loaded." : "دریافت وضعیت Sentry انجام نشد."}</p>}
    {!health && !failed && <p role="status">{english ? "Loading…" : "در حال دریافت…"}</p>}
    {health && <>
      <p>{english ? "Registered event delivery states" : "وضعیت تحویل رخدادهای ثبت‌شده"}</p>
      <ul dir="ltr">{Object.entries(health.external_states).map(([state, count]) => <li key={state}>{state}: {count}</li>)}</ul>
      {health.native_discovery.length === 0 && <p>{english ? "No native discovery worker observation is available." : "هنوز مشاهده‌ای از worker کشف crash بومی ثبت نشده است."}</p>}
      {health.native_discovery.map(scope => <article key={`${scope.project}:${scope.environment}`} style={{ overflowWrap: "anywhere" }}>
        <p><code dir="ltr">{scope.project} · {scope.environment}</code>: {labels[scope.state]} <code dir="ltr">({scope.state})</code></p>
        {scope.last_error_code && <p><code dir="ltr">{scope.last_error_code}</code></p>}
        <p>{english ? "Imported occurrences" : "رخدادهای دریافت‌شده"}: {scope.imported_count}</p>
        <p>{english ? "Last successful page / scanned through" : "آخرین صفحه موفق / پویش تا"}: <code dir="ltr">{scope.last_success_at ?? "unknown"} / {scope.watermark ?? "unknown"}</code></p>
      </article>)}
      <p>{english ? "A successful scan does not prove every SDK event was delivered. Missing capture and old events may remain unavailable." : "پویش موفق، دریافت همه خطاهای SDK را ثابت نمی‌کند؛ ثبت ناقص و رخدادهای قدیمی ممکن است در دسترس نباشند."}</p>
    </>}
  </section>;
}
