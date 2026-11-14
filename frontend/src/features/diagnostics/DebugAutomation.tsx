import { useEffect, useState } from "react";
import type { components } from "@fitician/core";
import { request } from "../../shared/apiClient";
import { DeploymentRequest, DeploymentReview } from "./DebugDeployment";
import { explainDebugFailure } from "./debugFailure";

type Operation = components["schemas"]["OperationResponse"];
type Availability = components["schemas"]["AutomationAvailability"];
interface Worker { id: string; name: string; environment: string; revoked: boolean; connected: boolean; capabilities: { github_authenticated?: boolean; workflow_installed?: boolean; error_code?: string | null } }
const root = "/api/v1/admin/diagnostics";
const active = new Set(["queued", "preparing", "dispatching", "uncertain", "running", "awaiting_authorization", "deploying", "verifying"]);
const codeStyle = { overflowWrap: "anywhere", whiteSpace: "normal" } as const;

export function DebugAutomationSetup({ english }: { english: boolean }) {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  async function load() {
    const rows = await request<Worker[]>(`${root}/automation-workers`);
    if (!Array.isArray(rows)) throw new Error("Invalid worker response");
    setWorkers(rows);
  }
  useEffect(() => {
    let current = true;
    const refresh = () => { if (current) void load().catch(() => { if (current) setError(true); }); };
    refresh(); const timer = window.setInterval(refresh, 10000);
    return () => { current = false; window.clearInterval(timer); };
  }, []);
  async function enroll() {
    setBusy(true); setError(false);
    try {
      const row = await request<{ id: string; token: string; environment: string; repository_name: string }>(`${root}/automation-workers`, { method: "POST", body: JSON.stringify({ name: "Germany GitHub Actions broker" }) });
      const config = { id: row.id, token: row.token, server: window.location.origin, repository_name: row.repository_name, environment: row.environment };
      const url = URL.createObjectURL(new Blob([JSON.stringify(config, null, 2)], { type: "application/json" }));
      const link = document.createElement("a"); link.href = url; link.download = "fitician-automation-worker.json"; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      await load();
    } catch { setError(true); } finally { setBusy(false); }
  }
  async function revoke(id: string) {
    setBusy(true);
    try { await request(`${root}/automation-workers/${encodeURIComponent(id)}/revoke`, { method: "POST" }); await load(); }
    catch { setError(true); } finally { setBusy(false); }
  }
  return <section className="diagnostics-card" dir={english ? "ltr" : "rtl"} style={{ minWidth: 0, overflowWrap: "anywhere" }}>
    <h3>{english ? "Controlled GitHub Actions connection" : "اتصال کنترل‌شدهٔ GitHub Actions"}</h3>
    <p>{english ? "The Germany broker uses its own enrollment and scoped GitHub credential. Selected-model execution and CI have separate permissions." : "broker آلمان اتصال و دسترسی محدود GitHub مستقل دارد. مجوز اجرای مدل و مجوز CI جدا ثبت می‌شوند."}</p>
    <button type="button" disabled={busy || workers.some(row => !row.revoked)} onClick={() => void enroll()}>{english ? "Enroll Germany CI broker" : "ثبت اتصال broker آلمان"}</button>
    <p>{english ? "Install the downloaded configuration as the service's private worker.json with mode 0600. Configure its GitHub access separately in the server secret store." : "فایل دانلودشده را با نام worker.json و دسترسی 0600 در تنظیمات خصوصی سرویس ثبت کنید. دسترسی GitHub در مخزن امن سرور تنظیم می‌شود."}</p>
    {!workers.length && <p>{english ? "No CI broker is enrolled." : "هنوز broker مربوط به CI ثبت نشده است."}</p>}
    {workers.map(row => <article key={row.id}><strong>{row.name}</strong> · <bdi>{row.environment}</bdi>
      <p>{row.revoked ? (english ? "Revoked" : "دسترسی لغو شده") : row.connected ? (english ? "Panel connection active" : "اتصال پنل برقرار است") : (english ? "Offline" : "آفلاین")}</p>
      <p>{row.capabilities.github_authenticated ? (english ? "GitHub authentication checked" : "ورود GitHub بررسی شده") : (english ? "GitHub authentication unverified" : "ورود GitHub تأیید نشده")}</p>
      <p>{row.capabilities.workflow_installed ? (english ? "Validation workflow available" : "workflow آزمون در دسترس است") : (english ? "Validation workflow unavailable" : "workflow آزمون در دسترس نیست")}</p>
      {row.capabilities.error_code && <p>{explainDebugFailure(row.capabilities.error_code, english)} <code dir="ltr" style={codeStyle}>{row.capabilities.error_code}</code></p>}
      {!row.revoked && <p><button type="button" disabled={busy} onClick={() => void revoke(row.id)}>{english ? "Revoke CI broker" : "لغو دسترسی broker"}</button></p>}
    </article>)}
    {error && <p role="status">{english ? "The CI connection could not be updated." : "خواندن یا تغییر اتصال CI انجام نشد."}</p>}
  </section>;
}

function stateText(row: Operation, english: boolean): string {
  if (row.kind === "deploy" && row.state === "succeeded") return english ? "Deployed; business resolution unverified" : "منتشر شد؛ رفع مسئله هنوز تأیید نشده";
  const labels: Record<string, [string, string]> = {
    queued: ["Queued", "در صف"], preparing: ["Preparing test snapshot", "آماده‌سازی نسخهٔ آزمون"],
    dispatching: ["Dispatching CI request", "ارسال درخواست CI"], uncertain: ["Dispatch confirmation pending", "نتیجهٔ ارسال هنوز مشخص نیست"],
    running: ["CI is pending or running", "در انتظار یا در حال اجرای CI"],
    succeeded: [row.kind === "validate" ? "Selected tests passed" : "Operation completed", row.kind === "validate" ? "آزمون‌های انتخابی گذشتند" : "عملیات پایان یافت"],
    failed: ["Execution failed", "اجرای عملیات ناموفق بود"], blocked: ["Connection or access required", "نیازمند اتصال یا دسترسی"],
    cancelled: ["Cancelled", "لغو شد"], awaiting_authorization: ["Awaiting authorization", "منتظر تأیید انتشار"],
    deploying: ["Deploying", "در حال انتشار"], verifying: ["Verifying outcome", "در حال بررسی نتیجه"],
  };
  return labels[row.state]?.[english ? 0 : 1] ?? row.state;
}

export function DebugOperations({ issueId, occurrenceId, english }: { issueId: string; occurrenceId: string; english: boolean }) {
  const [rows, setRows] = useState<Operation[]>([]);
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const base = `${root}/issues/${encodeURIComponent(issueId)}`;
  async function reloadOperations() {
    const page = await request<{ operations: Operation[] }>(`${base}/operations`);
    setRows(page.operations);
  }
  useEffect(() => {
    let current = true;
    async function refresh() {
      try {
        const [page, status] = await Promise.all([request<{ operations: Operation[] }>(`${base}/operations`), request<Availability>(`${root}/automation-status`)]);
        if (!Array.isArray(page.operations) || typeof status.connected !== "boolean") throw new Error("Invalid CI response");
        if (current) { setRows(page.operations); setAvailability(status); setError(false); }
      } catch { if (current) setError(true); }
    }
    void refresh(); const timer = window.setInterval(() => void refresh(), 3000);
    return () => { current = false; window.clearInterval(timer); };
  }, [base]);
  async function probe() {
    if (!occurrenceId || busy) return;
    setBusy(true); setError(false);
    try {
      const keyName = `debug-ci-probe:${issueId}:${occurrenceId}`;
      const key = sessionStorage.getItem(keyName) ?? crypto.randomUUID();
      sessionStorage.setItem(keyName, key);
      await request(`${base}/automation-probe`, { method: "POST", headers: { "Idempotency-Key": key }, body: JSON.stringify({ occurrence_id: occurrenceId }) });
      sessionStorage.removeItem(keyName);
    } catch { setError(true); } finally { setBusy(false); }
  }
  async function cancel(id: string) {
    setBusy(true);
    try {
      const row = await request<Operation>(`${base}/operations/${encodeURIComponent(id)}/cancel`, { method: "POST" });
      setRows(previous => previous.map(item => item.id === row.id ? row : item));
    } catch { setError(true); } finally { setBusy(false); }
  }
  return <section className="diagnostics-card" dir={english ? "ltr" : "rtl"} style={{ minWidth: 0, overflowWrap: "anywhere" }}>
    <h3>{english ? "Tests and repair operations" : "آزمون‌ها و عملیات اصلاح"}</h3>
    <p>{english ? "Resolution requires reproducing the failing scenario and recording verification evidence." : "تأیید رفع خطا به بازآزمایی سناریوی خطادار و ثبت شواهد نیاز دارد."}</p>
    <p>{availability?.live_validation_verified ? (english ? "Current CI policy verified by a completed test" : "اتصال CI برای نسخهٔ فعلی با نتیجهٔ آزمون تأیید شده است") : (english ? "Current CI connection is not yet verified" : "اتصال CI نسخهٔ فعلی هنوز تأیید نشده است")}</p>
    <button type="button" disabled={busy || !occurrenceId || !availability?.configured} onClick={() => void probe()}>{english ? "Test CI connection" : "آزمایش اتصال CI"}</button>
    <p>{english ? "The connection check uses isolated tests. It does not request model analysis." : "آزمایش اتصال با تست‌های جدا انجام می‌شود؛ تحلیل مدل درخواست نمی‌شود."}</p>
    {!rows.length && <p>{english ? "No recorded CI or repair operation." : "عملیات CI یا اصلاحی ثبت نشده است."}</p>}
    {rows.map(row => {
      const workflow = row.result.workflow_run_id;
      const commit = row.result.candidate_commit;
      const validation = row.result.validation;
      const count = validation && typeof validation === "object" && "exercised" in validation && typeof validation.exercised === "number" ? validation.exercised : null;
      return <article key={row.id} style={{ paddingBlock: "1rem", borderBlockEnd: "1px solid var(--border-color, #ddd)", minWidth: 0 }}>
        <strong>{row.kind === "deploy" ? (english ? "Controlled deployment" : "انتشار کنترل‌شده") : row.kind === "observe" ? (english ? "Read-only server observations" : "بررسی فقط‌خواندنی سرور") : row.kind === "publish_pr" ? (english ? "GitHub repair proposal" : "پیشنهاد اصلاح در GitHub") : row.purpose === "connection_check" ? (english ? "CI connection check" : "آزمایش اتصال CI") : (english ? "Repair validation" : "آزمون اصلاح")}</strong>
        <p>{stateText(row, english)} · <bdi>{row.profile}</bdi> · <bdi>{row.environment}</bdi></p>
        <p>{english ? "Occurrence" : "رخداد"}: <code dir="ltr" style={codeStyle}>{row.occurrence_id ?? "unknown"}</code>{row.occurrence_id === occurrenceId && <> · {english ? "Selected" : "منتخب"}</>}</p>
        {typeof commit === "string" && /^[a-f0-9]{40}$/.test(commit) && <p>{english ? "Tested candidate" : "نسخهٔ آزمون"}: <a href={`https://github.com/mohammad4242/fitician/commit/${commit}`} target="_blank" rel="noreferrer"><code dir="ltr" style={codeStyle}>{commit}</code></a></p>}
        {typeof workflow === "number" && Number.isSafeInteger(workflow) && workflow > 0 && <p><a href={`https://github.com/mohammad4242/fitician/actions/runs/${workflow}`} target="_blank" rel="noreferrer">GitHub Actions</a></p>}
        {count !== null && <p>{english ? "Tests exercised" : "تست‌های اجراشده"}: {count}</p>}
        {row.kind === "publish_pr" && typeof row.result.pr_url === "string" && /^https:\/\/github\.com\/mohammad4242\/fitician\/pull\/[1-9][0-9]*$/.test(row.result.pr_url) && <>
          <p><a href={row.result.pr_url} target="_blank" rel="noreferrer">{english ? "View PR" : "مشاهدهٔ PR"}</a></p>
          <p>{english ? "This PR does not mean deployed or verified resolved." : "این PR به معنی انتشار یا رفع تأییدشدهٔ خطا نیست."}</p>
        </>}
        {row.error_code && <p>{explainDebugFailure(row.error_code, english)} <code dir="ltr" style={codeStyle}>{row.error_code}</code></p>}
        {row.kind === "publish_pr" && row.state === "succeeded" && row.occurrence_id === occurrenceId && <DeploymentRequest publication={row} observations={rows} issueId={issueId} english={english} onUpdated={reloadOperations} />}
        {row.kind === "deploy" && <DeploymentReview operation={row} issueId={issueId} english={english} onUpdated={reloadOperations} />}
        {row.cancel_requested && <p>{english ? "Cancellation requested; waiting for confirmation" : "لغو درخواست شده؛ منتظر تأیید نتیجه"}</p>}
        {(active.has(row.state) || row.state === "awaiting_authorization") && <button type="button" disabled={busy || row.cancel_requested} onClick={() => void cancel(row.id)}>{english ? "Cancel operation" : "لغو عملیات"}</button>}
        {row.kind === "observe" && row.result.observation !== undefined && <details><summary>{english ? "Verified workflow evidence; business outcome unverified" : "مدرک workflow؛ نتیجهٔ کسب‌وکار هنوز تأیید نشده"}</summary><pre dir="ltr" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(row.result.observation, null, 2)}</pre></details>}
        {validation !== undefined && <details><summary>{english ? "Technical test evidence" : "مدرک فنی آزمون"}</summary><pre dir="ltr" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(validation, null, 2)}</pre></details>}
      </article>;
    })}
    {error && <p role="status">{english ? "CI state could not be refreshed or changed. Retrying keeps the request identity." : "خواندن یا تغییر وضعیت CI انجام نشد. تکرار درخواست با همان شناسه پیگیری می‌شود."}</p>}
  </section>;
}
