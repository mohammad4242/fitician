import { useEffect, useState } from "react";
import { request } from "../../shared/apiClient";

interface Connector { id: string; name: string; environment: string; revoked: boolean; last_seen: string | null; capabilities: { cli_version?: string; models?: string[] } }
interface Enrollment { id: string; token: string; environment: string; repository: string }
const base = "/api/v1/admin/diagnostics/connectors";

export function DebugConnectors({ english }: { english: boolean }) {
  const [rows, setRows] = useState<Connector[]>([]);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  async function load() { setRows(await request<Connector[]>(base)); }
  useEffect(() => { void load().catch(() => setError(true)); const timer = window.setInterval(() => void load().catch(() => setError(true)), 10000); return () => window.clearInterval(timer); }, []);
  async function enroll() {
    setBusy(true); setError(false);
    try {
      const row = await request<Enrollment>(base, { method: "POST", body: JSON.stringify({ name: "Laptop" }) });
      // The credential is returned once and downloaded; never place it in DOM or browser storage.
      const config = { id: row.id, token: row.token, server: window.location.origin, repository_name: row.repository, environment: row.environment, repository: "/home/mohammad/project/fitician", workspace_root: "/home/mohammad/project/fitician/var/debug-agent", codex_home: "/home/mohammad/project/fitician/var/debug-agent/codex", test_image: "" };
      const url = URL.createObjectURL(new Blob([JSON.stringify(config, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url; link.download = "fitician-connector.json"; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      await load();
    } catch { setError(true); } finally { setBusy(false); }
  }
  async function revoke(id: string) {
    setBusy(true);
    try { await request(`${base}/${encodeURIComponent(id)}/revoke`, { method: "POST" }); await load(); }
    catch { setError(true); } finally { setBusy(false); }
  }
  return <section className="diagnostics-card">
    <h3>{english ? "Enrolled debug connectors" : "اتصال مستقل ایجنت به لپ‌تاپ"}</h3>
    <p>{english ? "The panel needs its own outbound connector. Enrollment alone does not connect a computer. Run the connector with its private file and dedicated Codex login; generation runners keep their existing isolation." : "پنل به اتصال مستقل نیاز دارد. ثبت اتصال به‌تنهایی لپ‌تاپ را متصل نمی‌کند. کلاینت را با فایل خصوصی و ورود اختصاصی Codex اجرا کنید."}</p>
    <p>{english ? "Keep the downloaded file outside Git with mode 0600. Adjust repository paths, authenticate the dedicated runtime, and set a pinned test image before starting the client." : "فایل دانلودشده را با مجوز 0600 خارج از گیت نگه دارید. مسیر پروژه، ورود runtime و تصویر ثابت آزمون را پیش از اجرای کلاینت تنظیم کنید."}</p>
    <code dir="ltr" style={{ overflowWrap: "anywhere" }}>python -m app.debugging.connector --config /private/fitician-connector.json</code>
    <p><button type="button" disabled={busy} onClick={() => void enroll()}>{english ? "Enroll and download private configuration" : "ثبت و دریافت فایل خصوصی اتصال"}</button>{" "}<button type="button" onClick={() => void load().catch(() => setError(true))}>{english ? "Refresh connection status" : "تازه‌سازی وضعیت اتصال"}</button></p>
    {error && <p role="alert">{english ? "Connector request failed." : "درخواست اتصال انجام نشد."}</p>}
    {rows.map(row => <article key={row.id} style={{ overflowWrap: "anywhere" }}><strong>{row.name}</strong><p><code dir="ltr">{row.environment} · {row.capabilities.cli_version ?? "unknown"}</code></p><p>{row.revoked ? (english ? "Revoked" : "لغوشده") : !row.last_seen ? (english ? "Never connected" : "هنوز متصل نشده") : Date.now() - Date.parse(row.last_seen) < 30000 ? (english ? "Connected" : "متصل") : (english ? "Offline" : "آفلاین")}</p>{row.last_seen && <time>{row.last_seen}</time>}{!row.revoked && <p><button type="button" disabled={busy} onClick={() => void revoke(row.id)}>{english ? "Revoke connector" : "لغو دسترسی اتصال"}</button></p>}</article>)}
  </section>;
}
