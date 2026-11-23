import { useState } from "react";
import type { FormEvent } from "react";
import type { components } from "@fitician/core";

import { request } from "../../shared/apiClient";

type Operation = components["schemas"]["OperationResponse"];
type Updated = () => void | Promise<void>;
const root = "/api/v1/admin/diagnostics/issues/";
const object = (value: unknown): Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};

function identity(storage: string, body: string): string {
  let previous: { body?: string; key?: string } = {};
  try { previous = JSON.parse(sessionStorage.getItem(storage) ?? "{}"); } catch { /* Obsolete metadata. */ }
  if (previous.body === body && previous.key) return previous.key;
  const key = crypto.randomUUID();
  // Only public artifact/operation identifiers, never credentials or conversation text.
  sessionStorage.setItem(storage, JSON.stringify({ key, body }));
  return key;
}

export function DeploymentRequest({ publication, observations, issueId, english, onUpdated }: {
  publication: Operation; observations: Operation[]; issueId: string; english: boolean; onUpdated: Updated;
}) {
  const [observation, setObservation] = useState("");
  const [ci, setCi] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const eligible = observations.filter(row => row.kind === "observe" && row.state === "succeeded"
    && row.occurrence_id === publication.occurrence_id && object(row.result.observation).complete === true);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !eligible.some(row => row.id === observation) || !/^[1-9][0-9]{0,14}$/.test(ci)) return;
    setBusy(true); setFailed(false);
    const body = JSON.stringify({ publication_id: publication.id, observation_id: observation, ci_run_id: Number(ci) });
    try {
      const key = identity(`debug-deploy-preview:${issueId}:${publication.id}`, body);
      await request(`${root}${encodeURIComponent(issueId)}/deployments`, { method: "POST", headers: { "Idempotency-Key": key }, body });
      await onUpdated();
    } catch { setFailed(true); } finally { setBusy(false); }
  }
  return <details><summary>{english ? "Prepare deployment preview" : "آماده‌سازی پیش‌نمایش انتشار"}</summary>
    <p>{english ? "The repair must be reviewed and merged, with successful release CI for the exact current main commit. This request does not authorize deployment." : "اصلاح باید بررسی و ادغام شده باشد و CI انتشار برای همان commit فعلی main موفق باشد. این درخواست مجوز انتشار نیست."}</p>
    <form onSubmit={event => void submit(event)} className="diagnostics-stack">
      <label>{english ? "Recent target observation" : "مشاهدهٔ تازهٔ محیط مقصد"}<select value={observation} required onChange={event => setObservation(event.target.value)}><option value="">{english ? "Select environment evidence" : "انتخاب مدرک محیط"}</option>{eligible.map(row => <option key={row.id} value={row.id}>{row.target_environment} · {row.created_at}</option>)}</select></label>
      {!eligible.length && <p>{english ? "Ask the agent to collect a recent server observation for this occurrence first." : "ابتدا از ایجنت بخواهید برای این رخداد مشاهدهٔ تازهٔ سرور ثبت کند."}</p>}
      <label>{english ? "Successful release CI run ID" : "شناسهٔ اجرای موفق CI انتشار"}<input dir="ltr" inputMode="numeric" pattern="[1-9][0-9]{0,14}" value={ci} required onChange={event => setCi(event.target.value)} /></label>
      <button type="submit" disabled={busy || !observation || !ci}>{english ? "Check merged repair and release artifact" : "بررسی اصلاح ادغام‌شده و artifact انتشار"}</button>
      {failed && <p role="alert">{english ? "Preview unavailable. Check merged PR, exact CI artifact, recent target evidence and broker access." : "پیش‌نمایش آماده نشد؛ PR ادغام‌شده، artifact آزموده‌شده، تازگی مدرک محیط و اتصال broker را بررسی کنید."}</p>}
    </form>
  </details>;
}

export function DeploymentReview({ operation, issueId, english, onUpdated }: {
  operation: Operation; issueId: string; english: boolean; onUpdated: Updated;
}) {
  const [acceptedHash, setAcceptedHash] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const preview = object(operation.result.preview);
  const manifest = object(preview.manifest);
  const hash = typeof operation.result.preview_sha256 === "string" ? operation.result.preview_sha256 : "";
  async function authorize() {
    if (busy || !hash || acceptedHash !== hash || operation.state !== "awaiting_authorization") return;
    setBusy(true); setFailed(false);
    const body = JSON.stringify({ preview_sha256: hash });
    try {
      const key = identity(`debug-deploy-grant:${issueId}:${operation.id}`, body);
      await request(`${root}${encodeURIComponent(issueId)}/deployments/${encodeURIComponent(operation.id)}/authorize`, { method: "POST", headers: { "Idempotency-Key": key }, body });
      await onUpdated();
    } catch { setFailed(true); } finally { setBusy(false); }
  }
  if (!hash) return <p>{english ? "Release artifact validation pending." : "بررسی artifact انتشار در انتظار اجراست."}</p>;
  return <section style={{ minWidth: 0, overflowWrap: "anywhere" }}>
    <p>{english ? "Target environment" : "محیط مقصد"}: <bdi>{operation.target_environment}</bdi></p>
    <p>{english ? "Exact release commit" : "commit دقیق انتشار"}: <code dir="ltr">{String(manifest.commit ?? "unknown")}</code></p>
    <p>{english ? "Manifest SHA-256" : "SHA-256 فایل manifest"}: <code dir="ltr">{String(preview.manifest_sha256 ?? "unknown")}</code></p>
    <details><summary>{english ? "Tested image digests" : "digest تصاویر آزموده‌شده"}</summary><pre dir="ltr" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(manifest.images, null, 2)}</pre></details>
    <p>{english ? "GitHub owner approval remains required. Authorization expires after 30 minutes. Changed target identity or artifacts are rejected. Schema changes require the separate reviewed migration process." : "تأیید مالک در GitHub همچنان لازم است. مجوز پس از ۳۰ دقیقه منقضی می‌شود؛ تغییر محیط یا artifact آن را نامعتبر می‌کند. تغییر schema به مسیر جداگانهٔ migration بررسی‌شده نیاز دارد."}</p>
    {operation.state === "awaiting_authorization" && <>
      <label><input type="checkbox" checked={acceptedHash === hash} onChange={event => setAcceptedHash(event.target.checked ? hash : "")} />{english ? "I reviewed this exact artifact and target environment." : "این artifact دقیق و محیط مقصد را بررسی کردم."}</label>
      <p><button type="button" disabled={busy || acceptedHash !== hash} onClick={() => void authorize()}>{english ? "Authorize this artifact for this environment" : "مجوز انتشار همین artifact در همین محیط"}</button></p>
    </>}
    {failed && <p role="alert">{english ? "Authorization was not recorded. Refresh target and artifact evidence; retry preserves the request identity." : "مجوز ثبت نشد؛ مدرک محیط و artifact را تازه کنید. تکرار همان درخواست شناسه را حفظ می‌کند."}</p>}
    {operation.result.deployed === true && <p>{english ? "Running images verified. The failing business scenario still needs verification." : "تصاویر در حال اجرا بررسی شدند؛ سناریوی خطادار هنوز نیازمند بازآزمایی است."}</p>}
  </section>;
}

export function ReleaseReplayRequest({ deployment, observations, issueId, english, onUpdated }: {
  deployment: Operation; observations: Operation[]; issueId: string; english: boolean; onUpdated: Updated;
}) {
  const [observation, setObservation] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const eligible = observations.filter(row => row.kind === "observe" && row.state === "succeeded"
    && row.occurrence_id === deployment.occurrence_id && row.target_environment === deployment.target_environment
    && object(row.result.observation).complete === true);
  if (deployment.state !== "succeeded" || deployment.result.deployed !== true) return null;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !eligible.some(row => row.id === observation)) return;
    setBusy(true); setFailed(false);
    const body = JSON.stringify({ observation_id: observation });
    try {
      const key = identity(`debug-release-replay:${issueId}:${deployment.id}`, body);
      await request(`${root}${encodeURIComponent(issueId)}/deployments/${encodeURIComponent(deployment.id)}/replay`, {
        method: "POST", headers: { "Idempotency-Key": key }, body,
      });
      await onUpdated();
    } catch { setFailed(true); } finally { setBusy(false); }
  }
  return <details>
    <summary>{english ? "Replay the deployed commit's regression tests" : "بازآزمایی تست‌های اصلاح روی commit منتشرشده"}</summary>
    <p>{english ? "Runs the published repair's test scope in isolated GitHub Actions at the deployed source commit. This does not prove the production business outcome, execute production requests or resolve this issue." : "همان تست‌های اصلاح در GitHub Actions جداگانه و روی commit منتشرشده اجرا می‌شوند. این نتیجه، تأیید رفتار واقعی تولید یا رفع مسئله نیست؛ در تولید درخواستی اجرا نمی‌شود."}</p>
    <form onSubmit={event => void submit(event)} className="diagnostics-stack">
      <label>{english ? "Matching fresh server evidence" : "مدرک تازهٔ همان محیط"}<select required value={observation} onChange={event => setObservation(event.target.value)}>
        <option value="">{english ? "Select evidence" : "انتخاب مدرک"}</option>
        {eligible.map(row => <option key={row.id} value={row.id}>{row.target_environment} · {row.created_at}</option>)}
      </select></label>
      <button type="submit" disabled={busy || !observation}>{english ? "Run isolated replay in GitHub Actions" : "اجرای بازآزمایی جدا در GitHub Actions"}</button>
      {failed && <p role="alert">{english ? "Replay could not be queued. Check fresh matching images and broker access; retry keeps the request identity." : "بازآزمایی ثبت نشد؛ مدرک تازهٔ تصاویر و دسترسی broker را بررسی کنید. تکرار درخواست شناسه را حفظ می‌کند."}</p>}
    </form>
  </details>;
}
