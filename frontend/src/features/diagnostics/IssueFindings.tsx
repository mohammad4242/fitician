import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { components } from "@fitician/core";
import { request } from "../../shared/apiClient";

type Finding = components["schemas"]["FindingResponse"];
type Page = components["schemas"]["FindingsPage"];

export function IssueFindings({ issueId, occurrenceId, english }: {
  issueId: string; occurrenceId: string; english: boolean;
}) {
  const scope = `${issueId}:${occurrenceId}`;
  const [result, setResult] = useState<{ key: string; value: Page } | null>(null);
  const [failed, setFailed] = useState(false);
  const [position, setPosition] = useState({ key: "", offset: 0 });
  const offset = position.key === scope ? position.offset : 0;
  const key = `${scope}:${offset}`;
  const base = `/api/v1/admin/diagnostics/issues/${encodeURIComponent(issueId)}/findings`;
  const url = `${base}?offset=${offset}${occurrenceId ? `&occurrence_id=${encodeURIComponent(occurrenceId)}` : ""}`;
  const load = useCallback(async () => {
    const value = await request<Page>(url);
    setResult({ key, value }); setFailed(false);
  }, [url, key]);
  useEffect(() => {
    let current = true;
    const refresh = async () => {
      try {
        const value = await request<Page>(url);
        if (current) { setResult({ key, value }); setFailed(false); }
      } catch { if (current) setFailed(true); }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 10000);
    return () => { current = false; window.clearInterval(timer); };
  }, [url, key]);
  const page = result?.key === key ? result.value : null;
  const findings = page?.findings ?? [];
  const groups = [
    { title: english ? "Observed facts" : "مشاهدات ثبت‌شده", items: findings.filter(item => item.classification === "observed_fact" && !item.verification) },
    { title: english ? "Hypotheses and previous reviews" : "فرضیه‌ها و بررسی‌های قبلی", items: findings.filter(item => Boolean(item.stale && item.verification) || item.classification === "hypothesis" && !item.verification) },
    { title: english ? "Reviewed findings" : "یافته‌های بررسی‌شده", items: findings.filter(item => item.verification && !item.stale) },
    { title: english ? "Next useful checks" : "بررسی‌های بعدی", items: findings.filter(item => item.classification === "next_check") },
  ];
  return <section className="diagnostics-card" aria-label={english ? "Investigation findings" : "یافته‌های بررسی"}>
    <h3>{english ? "Investigation findings" : "یافته‌های بررسی"}</h3>
    <p>{english ? "Agent statements are proposals. A reviewed finding requires an administrator and matching failing/passing regression evidence; it does not mark deployment or resolution." : "گفتهٔ ایجنت پیشنهاد بررسی است. ثبت یافتهٔ بررسی‌شده به تأیید مدیر و مدرک تستِ شکست و موفقیت نیاز دارد؛ این تأیید به معنی استقرار یا رفع قطعی مسئله نیست."}</p>
    {!page && !failed && <p role="status">{english ? "Loading findings…" : "در حال دریافت یافته‌ها…"}</p>}
    {failed && <p role="alert">{english ? "Findings could not be refreshed. Previously loaded evidence may be stale." : "دریافت یافته‌ها انجام نشد؛ شواهد قبلی ممکن است به‌روز نباشند."}<button type="button" onClick={() => void load().catch(() => setFailed(true))}>{english ? "Retry findings" : "تلاش دوباره"}</button></p>}
    {groups.map((group, index) => <section key={group.title} style={{ marginBlock: "1rem" }}>
      <h4>{group.title}</h4>
      {!group.items.length && <p>{index === 2 ? (english ? "No reviewed finding for this evidence version." : "برای این نسخهٔ شواهد هنوز یافته‌ای تأیید نشده است.") : (english ? "No finding recorded." : "موردی ثبت نشده است.")}</p>}
      {group.items.map(item => <article key={item.id} style={{ borderBlockEnd: "1px solid var(--border-color, #ddd)", paddingBlock: "0.75rem", overflowWrap: "anywhere" }}>
        <p dir="auto">{item.text}</p>
        {item.stale && <p role="note">{english ? "Evidence changed; the previous finding needs review." : "شواهد تغییر کرده؛ بررسی قبلی نیاز به بازبینی دارد."}</p>}
        <details><summary>{english ? "Evidence and provenance" : "مدرک و منشأ یافته"}</summary>
          <p>{english ? "Model" : "مدل"}: <code dir="ltr">{item.model ?? (english ? "unknown" : "نامعلوم")}</code></p>
          <p>{english ? "Occurrence" : "رخداد"}: <code dir="ltr">{item.occurrence_id ?? "unknown"}</code></p>
          <p>{english ? "Run" : "اجرا"}: <code dir="ltr">{item.run_id}</code></p>
          <ul dir="ltr">{item.evidence_ids.map(id => <li key={id}><code>{id}</code></li>)}</ul>
          {item.verification && <><p dir="auto">{item.verification.note}</p><p><code dir="ltr">{item.verification.before_test_id} → {item.verification.after_test_id}</code></p><time>{item.verification.created_at}</time></>}
        </details>
        {item.can_verify && <FindingReview finding={item} base={base} english={english} onReviewed={load} />}
      </article>)}
    </section>)}
    {offset > 0 && <button type="button" onClick={() => setPosition({ key: scope, offset: Math.max(0, offset - 20) })}>{english ? "Previous findings page" : "صفحهٔ قبلی یافته‌ها"}</button>}
    {page?.next_offset != null && <button type="button" onClick={() => setPosition({ key: scope, offset: page.next_offset! })}>{english ? "More findings" : "یافته‌های بیشتر"}</button>}
  </section>;
}

function FindingReview({ finding, base, english, onReviewed }: {
  finding: Finding; base: string; english: boolean; onReviewed: () => Promise<void>;
}) {
  const [before, setBefore] = useState("");
  const [after, setAfter] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!before || !after || note.trim().length < 8 || busy || !finding.evidence_version) return;
    setBusy(true); setFailed(false);
    try {
      const payload = JSON.stringify({ before_test_id: before, after_test_id: after, evidence_version: finding.evidence_version, note });
      const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(payload)))].map(value => value.toString(16).padStart(2, "0")).join("");
      const storage = `debug-finding-review:${finding.id}`;
      let previous: { digest?: string; key?: string } = {};
      try { previous = JSON.parse(sessionStorage.getItem(storage) ?? "{}"); } catch { /* Ignore obsolete metadata. */ }
      const key = previous.digest === digest && previous.key ? previous.key : crypto.randomUUID();
      sessionStorage.setItem(storage, JSON.stringify({ digest, key }));
      await request(`${base}/${encodeURIComponent(finding.id)}/verify`, { method: "POST", headers: { "Idempotency-Key": key }, body: payload });
      sessionStorage.removeItem(storage);
      await onReviewed();
    } catch { setFailed(true); } finally { setBusy(false); }
  }
  return <details><summary>{english ? "Review regression evidence" : "بررسی مدارک تست"}</summary>
    <form onSubmit={event => void submit(event)} className="diagnostics-stack">
      <label>{english ? "Failing regression test" : "تست شکست‌خورده"}<select value={before} onChange={event => setBefore(event.target.value)} required><option value="">{english ? "Select evidence" : "انتخاب مدرک"}</option>{finding.test_evidence.filter(item => !item.passed).map(item => <option key={item.id} value={item.id}>{item.command} · {item.id.slice(0, 8)}</option>)}</select></label>
      <label>{english ? "Passing regression test" : "تست موفق"}<select value={after} onChange={event => setAfter(event.target.value)} required><option value="">{english ? "Select evidence" : "انتخاب مدرک"}</option>{finding.test_evidence.filter(item => item.passed).map(item => <option key={item.id} value={item.id}>{item.command} · {item.id.slice(0, 8)}</option>)}</select></label>
      <label>{english ? "What did you verify?" : "چه چیزی را بررسی و تأیید کردید؟"}<textarea value={note} onChange={event => setNote(event.target.value)} minLength={8} maxLength={2000} required /></label>
      <button type="submit" disabled={busy || !before || !after || note.trim().length < 8}>{english ? "Record reviewed finding" : "ثبت یافتهٔ بررسی‌شده"}</button>
      {failed && <p role="alert">{english ? "Review was not recorded. Evidence may have changed or the tests may not match; refresh and review again." : "تأیید ثبت نشد؛ ممکن است شواهد تغییر کرده یا تست‌ها همسان نباشند. دوباره شواهد را بررسی کنید."}</p>}
    </form>
  </details>;
}
