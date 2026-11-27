import { useEffect, useRef, useState } from "react";
import { request } from "../../shared/apiClient";

interface Props { english: boolean; onCaptured: (issueId: string, occurrenceId: string) => void }
interface Result { issue_id: string; event_id: string; delivery: string }
const path = "/api/v1/admin/diagnostics/synthetic-probe";
const storageKey = "fitician:diagnostics:synthetic-probe";

export function SyntheticProbe({ english, onCaptured }: Props) {
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const inFlight = useRef(false);
  useEffect(() => {
    let active = true;
    void request<{ enabled: boolean }>(path).then(policy => {
      if (active) setEnabled(policy.enabled === true);
    }).catch(() => { if (active) setEnabled(false); });
    return () => { active = false; };
  }, []);
  async function capture() {
    if (inFlight.current || finished) return;
    inFlight.current = true; setBusy(true);
    try {
      const identity = sessionStorage.getItem(storageKey) ?? crypto.randomUUID();
      sessionStorage.setItem(storageKey, identity);
      const result = await request<Result>(path, { method: "POST", headers: { "Idempotency-Key": identity } });
      sessionStorage.removeItem(storageKey);
      setNotice(english ? "Local occurrence recorded; Sentry ingestion remains unconfirmed." : "رخداد محلی ثبت شد؛ دریافت آن در Sentry هنوز تأیید نشده است.");
      setFinished(true);
      onCaptured(result.issue_id, result.event_id);
    } catch {
      setNotice(english ? "Capture could not be confirmed. Check recorded evidence before retrying; the request identity is retained." : "نتیجهٔ ثبت تأیید نشد. پیش از تلاش دوباره شواهد ثبت‌شده را بررسی کنید؛ شناسهٔ درخواست نگه داشته شده است.");
      setFinished(true);
    } finally { setBusy(false); inFlight.current = false; }
  }
  if (!enabled) return null;
  return <section className="diagnostics-card">
    <button type="button" disabled={busy || finished} onClick={() => void capture()}>{english ? "Record a controlled test error" : "ثبت خطای آزمایشی کنترل‌شده"}</button>
    <p>{english ? "This creates a labeled synthetic occurrence without changing business data. It does not prove model execution or notification delivery." : "یک رخداد با برچسب آزمایشی ثبت می‌شود و دادهٔ تجاری تغییر نمی‌کند. این آزمون اجرای مدل یا تحویل پیامک را تأیید نمی‌کند."}</p>
    {notice && <p role="status">{notice}</p>}
  </section>;
}
