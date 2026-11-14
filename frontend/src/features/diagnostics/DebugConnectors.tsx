import { useEffect, useState } from "react";
import { request } from "../../shared/apiClient";
import { explainDebugFailure } from "./debugFailure";

interface Connector { id: string; name: string; environment: string; revoked: boolean; last_seen: string | null; capabilities: { cli_version?: string; models?: string[]; runtime_error_code?: string | null } }
interface Enrollment { id: string; token: string; environment: string; repository: string }
const base = "/api/v1/admin/diagnostics/connectors";

interface Props { english: boolean; showExecutionTarget?: boolean; selectedTarget?: string | null; onSelectTarget?: (id: string | null) => void }
export function DebugConnectors({ english, showExecutionTarget = false, selectedTarget = null, onSelectTarget }: Props) {
  const [rows, setRows] = useState<Connector[]>([]);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [location, setLocation] = useState("server");
  async function load() { setRows(await request<Connector[]>(base)); }
  useEffect(() => { void load().catch(() => setError(true)); const timer = window.setInterval(() => void load().catch(() => setError(true)), 10000); return () => window.clearInterval(timer); }, []);
  async function enroll() {
    setBusy(true); setError(false);
    try {
      const row = await request<Enrollment>(base, { method: "POST", body: JSON.stringify({ name: location === "server" ? "Germany debug runtime" : "Laptop" }) });
      // The credential is returned once and downloaded; never place it in DOM or browser storage.
      const config = { id: row.id, token: row.token, server: window.location.origin, repository_name: row.repository, environment: row.environment, repository: location === "server" ? "/state/repository" : "/absolute/path/to/fitician", workspace_root: location === "server" ? "/state/runtime" : "/absolute/path/to/private-workspaces", codex_home: location === "server" ? "/state/codex" : "/absolute/path/to/dedicated-codex-home", codex_executable: location === "server" ? "/usr/local/bin/codex" : "/absolute/path/to/pinned/codex", test_image: "" };
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
    <h3>{english ? "Enrolled debug connectors" : "اتصال‌های مستقل ایجنت"}</h3>
    {showExecutionTarget && <div className="admin-ai-setting-field">
      <label htmlFor="debug-execution-target">{english ? "Tool execution target" : "محل اجرای ابزارها"}</label>
      <select id="debug-execution-target" value={selectedTarget ?? ""} onChange={event => onSelectTarget?.(event.target.value || null)}>
        <option value="">{english ? "Analysis only — no execution target" : "فقط تحلیل؛ بدون اتصال اجرا"}</option>
        {selectedTarget && !rows.some(row => row.id === selectedTarget && !row.revoked) && <option value={selectedTarget}>{english ? "Selected target unavailable" : "اتصال منتخب در دسترس نیست"}</option>}
        {rows.filter(row => !row.revoked).map(row => <option key={row.id} value={row.id}>{row.name} · {row.last_seen && Date.now() - Date.parse(row.last_seen) < 30000 ? (english ? "Connected" : "متصل") : (english ? "Offline" : "آفلاین")}</option>)}
      </select>
      <p>{english ? "The saved target is used on subsequent turns. An offline target blocks tools; select another target explicitly to move execution." : "اتصال ذخیره‌شده در نوبت‌های بعدی استفاده می‌شود. اتصال آفلاین اجرای ابزارها را متوقف می‌کند؛ تغییر محل اجرا با انتخاب شما انجام می‌شود."}</p>
    </div>}
    <p>{english ? "The panel needs its own outbound connector. Enrollment alone does not connect a computer. Run the connector with its private file and dedicated Codex login; generation runners keep their existing isolation." : "پنل به اتصال مستقل نیاز دارد. ثبت اتصال به‌تنهایی لپ‌تاپ را متصل نمی‌کند. کلاینت را با فایل خصوصی و ورود اختصاصی Codex اجرا کنید."}</p>
    <p>{english ? "Keep the downloaded file outside Git with mode 0600. Germany: install it as the dedicated service's private connector.json. Laptop: adjust the absolute paths and pinned Codex executable. Each runtime needs its own login." : "فایل دانلودشده را با مجوز 0600 خارج از گیت نگه دارید. برای آلمان آن را در مسیر خصوصی سرویس با نام connector.json قرار دهید؛ برای لپ‌تاپ مسیرهای مطلق و فایل اجرایی ثابت Codex را تنظیم کنید. هر runtime ورود مستقل می‌خواهد."}</p>
    <label htmlFor="new-connector-location">{english ? "New connector location" : "محل اتصال جدید"}</label>
    <select id="new-connector-location" value={location} onChange={event => setLocation(event.target.value)}><option value="server">{english ? "Germany isolated server" : "سرور مستقل آلمان"}</option><option value="laptop">{english ? "Optional laptop" : "لپ‌تاپ اختیاری"}</option></select>
    <code dir="ltr" style={{ overflowWrap: "anywhere" }}>python -m app.debugging.connector --config /private/fitician-connector.json</code>
    <p><button type="button" disabled={busy} onClick={() => void enroll()}>{english ? "Enroll and download private configuration" : "ثبت و دریافت فایل خصوصی اتصال"}</button>{" "}<button type="button" onClick={() => void load().catch(() => setError(true))}>{english ? "Refresh connection status" : "تازه‌سازی وضعیت اتصال"}</button></p>
    {error && <p role="alert">{english ? "Connector request failed." : "درخواست اتصال انجام نشد."}</p>}
    {rows.map(row => <article key={row.id} style={{ overflowWrap: "anywhere" }}><strong>{row.name}</strong><p><code dir="ltr">{row.environment} · {row.capabilities.cli_version ?? "unknown"}</code></p><p>{row.revoked ? (english ? "Revoked" : "لغوشده") : !row.last_seen ? (english ? "Never connected" : "هنوز متصل نشده") : Date.now() - Date.parse(row.last_seen) < 30000 ? (english ? "Connected" : "متصل") : (english ? "Offline" : "آفلاین")}</p>{row.capabilities.runtime_error_code && <p>{explainDebugFailure(row.capabilities.runtime_error_code, english)} <code dir="ltr">{row.capabilities.runtime_error_code}</code></p>}{row.last_seen && <time>{row.last_seen}</time>}{!row.revoked && <p><button type="button" disabled={busy} onClick={() => void revoke(row.id)}>{english ? "Revoke connector" : "لغو دسترسی اتصال"}</button></p>}</article>)}
  </section>;
}
