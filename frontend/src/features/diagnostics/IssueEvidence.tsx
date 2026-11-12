import { useEffect, useState } from "react";
import { request } from "../../shared/apiClient";
import type { DiagnosticEvent } from "./api";

interface Frame { filename?: string; function: string; lineno: number }
interface Evidence {
  evidence_id?: string;
  evidence_version?: string;
  sentry_event_id?: string | null;
  delivery?: string;
  sync_state?: string;
  sync_error?: string | null;
  external_issue_id?: string | null;
  missing: string[];
  snapshot: {
    release_commit: string | null;
    stage: string;
    component: string;
    request_id: string | null;
    operation_id: string | null;
    trace_id: string | null;
    attempt: number;
    exception: { values: { type: string; frames: Frame[] }[] };
  } | null;
}

export function IssueEvidence({ issueId, events, english }: { issueId: string; events: readonly DiagnosticEvent[]; english: boolean }) {
  const [occurrence, setOccurrence] = useState("");
  const [result, setResult] = useState<{ key: string; value: Evidence } | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const key = `${issueId}:${occurrence}`;
  useEffect(() => {
    let current = true;
    setFailure(null);
    void request<Evidence>(`/api/v1/admin/diagnostics/issues/${encodeURIComponent(issueId)}/evidence${occurrence ? `?occurrence_id=${encodeURIComponent(occurrence)}` : ""}`).then(value => {
      if (current) setResult({ key, value });
    }).catch(() => { if (current) setFailure(english ? "Evidence could not be loaded." : "دریافت شواهد انجام نشد."); });
    return () => { current = false; };
  }, [issueId, occurrence, key, english]);
  const evidence = result?.key === key ? result.value : null;
  const snapshot = evidence?.snapshot;
  return <section className="diagnostics-card">
    <h3>{english ? "Technical evidence" : "شواهد فنی"}</h3>
    <label>{english ? "Occurrence" : "رخداد منتخب"}<select value={occurrence} onChange={event => setOccurrence(event.target.value)}>
      <option value="">{english ? "Latest available evidence" : "آخرین شواهد موجود"}</option>
      {events.map(event => <option key={event.event_id} value={event.event_id}>{event.timestamp} · {event.stage}</option>)}
    </select></label>
    {failure && <p role="alert">{failure}</p>}
    {!evidence && !failure && <p role="status">{english ? "Loading evidence…" : "در حال دریافت شواهد…"}</p>}
    {evidence && !snapshot && <p>{english ? "No exception stack was recorded for this occurrence. Historical stacks cannot be recovered automatically." : "برای این رخداد stack ثبت نشده است. stack رخداد قدیمی خودکار قابل بازیابی نیست."}</p>}
    {snapshot && <>
      <p>{english ? "Sentry delivery" : "تحویل به Sentry"}: <code dir="ltr">{evidence.delivery} · {evidence.sync_state}</code></p>
      {evidence.sync_error && <p><code dir="ltr">{evidence.sync_error}</code></p>}
      <p>{english ? "Release commit" : "commit نسخه رخداد"}: <code dir="ltr">{snapshot.release_commit ?? (english ? "unknown" : "نامعلوم")}</code></p>
      <details><summary>{english ? "Exception chain and frames" : "زنجیره خطا و محل اجرای کد"}</summary>
        {snapshot.exception.values.map((exception, index) => <div key={index}>
          <strong dir="ltr">{exception.type}</strong>
          <ol dir="ltr" style={{ overflowWrap: "anywhere", paddingInlineStart: "1.5rem" }}>{exception.frames.map((frame, index) => <li key={index}>
            <code>{frame.filename ?? "unknown source"}:{frame.lineno} · {frame.function}</code>
            {frame.filename && /^app\/[A-Za-z0-9_./-]+$/.test(frame.filename) && !frame.filename.split("/").includes("..") && /^[a-f0-9]{40}$/.test(snapshot.release_commit ?? "") && <>{" "}<a href={`https://github.com/mohammad4242/fitician/blob/${snapshot.release_commit}/backend/${frame.filename}#L${frame.lineno}`} target="_blank" rel="noreferrer">{english ? "Source" : "کد"}</a></>}
          </li>)}</ol>
        </div>)}
        <dl className="diagnostics-definition-list">{["request_id", "operation_id", "trace_id", "attempt"].map(field => <div key={field}><dt>{field}</dt><dd dir="ltr">{String(snapshot[field as keyof typeof snapshot] ?? "unknown")}</dd></div>)}</dl>
        <p><code dir="ltr">{evidence.evidence_id} · {evidence.evidence_version}</code></p>
      </details>
    </>}
  </section>;
}
