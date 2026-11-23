import { useEffect, useState } from "react";
import { request } from "../../shared/apiClient";
import { explainDebugFailure } from "./debugFailure";

interface Connector { id: string; name: string; environment: string; revoked: boolean; last_seen: string | null; last_repository_probe?: { state: string; at: string; read_tool_executed: boolean; error_code?: string }; capabilities: { cli_version?: string; models?: string[]; runtime_error_code?: string | null; api_error_code?: string | null; supports_api?: boolean; execution_role?: string; repository_head?: string; repository_branch?: string } }
interface Enrollment { id: string; token: string; environment: string; repository: string }
const base = "/api/v1/admin/diagnostics/connectors";

interface Props { english: boolean; showExecutionTarget?: boolean; selectedTarget?: string | null; onSelectTarget?: (id: string | null) => void }
export function DebugConnectors({ english, showExecutionTarget = false, selectedTarget = null, onSelectTarget }: Props) {
  const [rows, setRows] = useState<Connector[]>([]);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const location = "laptop";
  const [probeStatus, setProbeStatus] = useState<Record<string, string>>({});
  async function load() { setRows(await request<Connector[]>(base)); }
  useEffect(() => { void load().catch(() => setError(true)); const timer = window.setInterval(() => void load().catch(() => setError(true)), 10000); return () => window.clearInterval(timer); }, []);
  async function enroll() {
    setBusy(true); setError(false);
    try {
      const row = await request<Enrollment>(base, { method: "POST", body: JSON.stringify({ name: "Laptop" }) });
      // The credential is returned once and downloaded; never place it in DOM or browser storage.
      const config = { id: row.id, token: row.token, server: window.location.origin, repository_name: row.repository, environment: row.environment, execution_role: "repository_worker", repository: "/absolute/path/to/fitician", workspace_root: "/absolute/path/to/private-workspaces", test_image: "", validation_images: {}, validation_policy_commit: "", repair_on_current_main: true, fetch_missing_releases: true };

      const url = URL.createObjectURL(new Blob([JSON.stringify(config, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url; link.download = "fitician-connector.json"; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      await load();
    } catch { setError(true); } finally { setBusy(false); }
  }
  async function testRepository(id: string) {
    setBusy(true);
    try {
      const probe = await request<{ id: string }>(`${base}/${encodeURIComponent(id)}/repository-probes`, { method: "POST" });
      setProbeStatus(previous => ({ ...previous, [id]: `${english ? "Queued repository check" : "بررسی مخزن در صف"}: ${probe.id}` }));
    } catch { setError(true); } finally { setBusy(false); }
  }
  async function revoke(id: string) {
    setBusy(true);
    try { await request(`${base}/${encodeURIComponent(id)}/revoke`, { method: "POST" }); await load(); }
    catch { setError(true); } finally { setBusy(false); }
  }
  return <section className="diagnostics-card">
    <h3>{english ? "Repository execution laptops" : "لپ‌تاپ‌های اجرای مخزن"}</h3>
    {showExecutionTarget && <div className="admin-ai-setting-field">
      <label htmlFor="debug-execution-target">{english ? "Tool execution target" : "محل اجرای ابزارها"}</label>
      <select id="debug-execution-target" value={selectedTarget ?? ""} onChange={event => onSelectTarget?.(event.target.value || null)}>
        <option value="">{english ? "Select explicit runtime" : "محل اجرای مشخص را انتخاب کنید"}</option>
        {selectedTarget && !rows.some(row => row.id === selectedTarget && !row.revoked && row.capabilities.execution_role === "repository_worker") && <option value={selectedTarget}>{english ? "Selected target unavailable" : "اتصال منتخب در دسترس نیست"}</option>}
        {rows.filter(row => !row.revoked && row.capabilities.execution_role === "repository_worker").map(row => <option key={row.id} value={row.id}>{row.name} · {row.last_seen && Date.now() - Date.parse(row.last_seen) < 30000 ? (english ? "Connected" : "متصل") : (english ? "Offline" : "آفلاین")}</option>)}
      </select>
      <p>{english ? "The saved target is used on subsequent turns. An offline target blocks tools; select another target explicitly to move execution." : "اتصال ذخیره‌شده در نوبت‌های بعدی استفاده می‌شود. اتصال آفلاین اجرای ابزارها را متوقف می‌کند؛ تغییر محل اجرا با انتخاب شما انجام می‌شود."}</p>
    </div>}
    <p>{english ? "Agent Service runs AI with its existing accounts. This outbound laptop worker runs repository tools only and needs no AI login." : "AI با حساب‌های موجود در Agent Service اجرا می‌شود. اتصال خروجی لپ‌تاپ فقط ابزارهای مخزن را اجرا می‌کند و ورود AI نمی‌خواهد."}</p>
    <p>{english ? "Keep the downloaded file outside Git with mode 0600. Set absolute repository and private workspace paths. Worktrees preserve your original checkout." : "فایل خصوصی را با مجوز 0600 خارج از گیت نگه دارید. مسیر مطلق مخزن و فضای خصوصی کار را تنظیم کنید؛ تغییرات در worktree جدا انجام می‌شوند."}</p>
    <label htmlFor="new-connector-location">{english ? "New connector location" : "محل اتصال جدید"}</label>
    <select id="new-connector-location" value={location} disabled><option value="laptop">{english ? "Laptop repository worker" : "لپ‌تاپ؛ اجرای ابزارهای مخزن"}</option></select>
    <code dir="ltr" style={{ overflowWrap: "anywhere" }}>python -m app.debugging.connector --config /private/fitician-connector.json</code>
    <p><button type="button" disabled={busy} onClick={() => void enroll()}>{english ? "Enroll and download private configuration" : "ثبت و دریافت فایل خصوصی اتصال"}</button>{" "}<button type="button" onClick={() => void load().catch(() => setError(true))}>{english ? "Refresh connection status" : "تازه‌سازی وضعیت اتصال"}</button></p>
    {error && <p role="alert">{english ? "Connector request failed." : "درخواست اتصال انجام نشد."}</p>}
    {rows.map(row => <article key={row.id} style={{ overflowWrap: "anywhere" }}><strong>{row.name}</strong><p><code dir="ltr">{row.environment} · {row.capabilities.execution_role ?? "legacy_runtime"} · {row.capabilities.repository_branch ?? "?"} · {row.capabilities.repository_head ?? "?"}</code></p><p>{row.revoked ? (english ? "Revoked" : "لغوشده") : !row.last_seen ? (english ? "Never connected" : "هنوز متصل نشده") : Date.now() - Date.parse(row.last_seen) < 30000 ? (english ? "Connected" : "متصل") : (english ? "Offline" : "آفلاین")}</p>{row.capabilities.runtime_error_code && <p>{explainDebugFailure(row.capabilities.runtime_error_code, english)} <code dir="ltr">{row.capabilities.runtime_error_code}</code></p>}{row.capabilities.api_error_code && <p>{explainDebugFailure(row.capabilities.api_error_code, english)} <code dir="ltr">{row.capabilities.api_error_code}</code></p>}{row.capabilities.supports_api && <p>{english ? "Dedicated model API verified" : "اتصال API اختصاصی مدل تأیید شد"}</p>}{row.last_repository_probe && <p>{english ? "Last repository check" : "آخرین بررسی مخزن"}: <bdi>{row.last_repository_probe.at}</bdi> · {row.last_repository_probe.state === "completed" && row.last_repository_probe.read_tool_executed && !row.last_repository_probe.error_code ? (english ? "Source read verified" : "خواندن کد تأیید شد") : row.last_repository_probe.error_code ?? row.last_repository_probe.state}</p>}{row.capabilities.execution_role === "repository_worker" && !row.revoked && <p><button type="button" disabled={busy} onClick={() => void testRepository(row.id)}>{english ? "Test laptop connection" : "تست اتصال لپ‌تاپ"}</button> {probeStatus[row.id]}</p>}{row.last_seen && <time>{row.last_seen}</time>}{!row.revoked && <p><button type="button" disabled={busy} onClick={() => void revoke(row.id)}>{english ? "Revoke connector" : "لغو دسترسی اتصال"}</button></p>}</article>)}
  </section>;
}
