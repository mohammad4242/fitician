import { useEffect, useState } from "react";
import { request } from "../../shared/apiClient";

interface Attempt { id: string; state: string; started_at: string; provider_message_id: string | null; error_code: string | null }
interface Delivery { id: string; issue_id: string; state: string; occurrence_total: number; provider_message_id: string | null; error_code: string | null; attempts: Attempt[] }
interface Snapshot { items: Delivery[]; next_offset: number | null; configuration: { enabled: boolean; recipient_configured: boolean; provider_configured: boolean; cooldown_seconds: number; min_interval_seconds: number; max_per_hour: number } }

export function NotificationDeliveries({ english, issueId }: { english: boolean; issueId?: string }) {
  const [page, setPage] = useState<{ endpoint: string; value: Snapshot } | null>(null);
  const [error, setError] = useState(false);
  const [offset, setOffset] = useState(0);
  const endpoint = `/api/v1/admin/diagnostics/notification-deliveries?limit=20&offset=${offset}${issueId ? `&issue_id=${encodeURIComponent(issueId)}` : ""}`;
  useEffect(() => {
    let current = true;
    async function load() {
      try {
        const value = await request<Snapshot>(endpoint);
        if (current && value) { setPage({ endpoint, value }); setError(false); }
      } catch { if (current) setError(true); }
    }
    void load();
    const timer = window.setInterval(() => void load(), 15000);
    return () => { current = false; window.clearInterval(timer); };
  }, [endpoint]);
  const data = page?.endpoint === endpoint ? page.value : null;
  const labels: Record<string, string> = english ? {
    queued: "Queued for aggregation", sending: "Sending", retrying: "Safe retry scheduled",
    accepted: "Accepted; delivery unconfirmed", provider_delivered: "Delivered by provider",
    failed: "Send rejected", delivery_failed: "Delivery failed", uncertain: "Outcome unknown; no automatic resend",
    suppressed: "Suppressed after issue closure",
  } : {
    queued: "در صف تجمیع", sending: "در حال ارسال", retrying: "تلاش مجاز بعدی زمان‌بندی شد",
    accepted: "پذیرفته‌شده؛ تحویل هنوز تأیید نشده", provider_delivered: "تحویل گزارش‌شده توسط FarazSMS",
    failed: "ارسال رد شد", delivery_failed: "تحویل ناموفق", uncertain: "نتیجه نامشخص؛ بدون ارسال دوبارهٔ خودکار",
    suppressed: "پس از بسته‌شدن خطا لغو شد",
  };
  return <section className="diagnostics-card" style={{ overflowWrap: "anywhere" }}>
    <h3>{english ? "FarazSMS alerts" : "هشدارهای پیامکی FarazSMS"}</h3>
    <p>{english ? "SMS contains a short Persian summary and an authenticated issue link. Technical evidence stays in this panel." : "پیامک فقط خلاصهٔ فارسی و لینک نیازمند ورود دارد. شواهد فنی در همین پنل می‌مانند."}</p>
    {error && <p role="status">{english ? "Notification status unavailable" : "وضعیت پیامک فعلاً در دسترس نیست"}</p>}
    {data && <>
      <p>{data.configuration.enabled ? (english ? "Sending option enabled; worker execution is required." : "گزینهٔ ارسال روشن است؛ اجرای worker جداگانه لازم است.") : (english ? "Automatic sending disabled" : "ارسال خودکار غیرفعال است")}</p>
      {(!data.configuration.recipient_configured || !data.configuration.provider_configured) && <p>{english ? "Private destination or provider configuration is incomplete." : "تنظیم امن مقصد یا سرویس‌دهنده کامل نیست."}</p>}
      <p>{english ? "Per-issue cooldown (seconds)" : "فاصلهٔ ارسال برای هر خطا (ثانیه)"}: {data.configuration.cooldown_seconds} · {english ? "Hourly maximum" : "سقف ساعتی"}: {data.configuration.max_per_hour}</p>
      {data.items.map(item => <article key={item.id} style={{ paddingBlock: "0.75rem", borderBlockEnd: "1px solid var(--border-color, #ddd)" }}>
        <strong>{labels[item.state] ?? item.state}</strong>
        <p>{english ? "Total occurrences" : "کل رخدادها"}: {item.occurrence_total}</p>
        {!issueId && <a href={`/admin/diagnostics?tab=issues&issue=${encodeURIComponent(item.issue_id)}`}>{english ? "Issue details" : "جزئیات خطا"}</a>}
        {item.provider_message_id && <p>{english ? "Provider reference" : "شناسهٔ سرویس‌دهنده"}: <code dir="ltr">{item.provider_message_id}</code></p>}
        {item.error_code && <p dir="ltr"><code>{item.error_code}</code></p>}
        {item.attempts.length > 0 && <details><summary>{english ? "Dispatch history" : "تاریخچهٔ ارسال"}</summary><ul>{item.attempts.map(attempt => <li key={attempt.id}>{labels[attempt.state] ?? attempt.state} · <time dir="ltr">{attempt.started_at}</time>{attempt.error_code && <> · <code dir="ltr">{attempt.error_code}</code></>}</li>)}</ul></details>}
      </article>)}
      {data.items.length === 0 && <p>{english ? "No SMS dispatch recorded" : "ارسال پیامکی ثبت نشده است"}</p>}
      {(offset > 0 || data.next_offset !== null) && <nav>
        <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>{english ? "Previous" : "قبلی"}</button>
        <button type="button" disabled={data.next_offset === null} onClick={() => setOffset(data.next_offset ?? offset)}>{english ? "Next" : "بعدی"}</button>
      </nav>}
    </>}
  </section>;
}
