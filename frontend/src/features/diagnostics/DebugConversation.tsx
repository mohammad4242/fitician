import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { request } from "../../shared/apiClient";
import { explainDebugFailure } from "./debugFailure";

interface Run { id: string; message_id?: string; action?: string; state: string; error_code: string | null; config: { primary_model_id?: string; agent_model_id?: string; connector_name?: string | null; runtime_mode?: "real" | "mock" }; evidence_id: string | null; occurrence_id?: string | null }
interface Message { id: string; run_id?: string | null; role: string; content: string; created_at: string }
interface Conversation { messages: Message[]; runs: Run[]; next_cursor: string | null }
const activeStates = new Set(["queued", "investigating", "editing", "testing", "awaiting_authorization", "deploying", "verifying"]);


export function DebugConversation({ issueId, english, occurrenceId = "" }: { issueId: string; english: boolean; occurrenceId?: string }) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [older, setOlder] = useState<Message[]>([]);
  const [olderRuns, setOlderRuns] = useState<Run[]>([]);
  const updateHistoricalRun = useCallback((updated: Run) => {
    setOlderRuns(current => current.map(run => run.id === updated.id ? updated : run));
  }, []);
  const [cursor, setCursor] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [inspectCode, setInspectCode] = useState(false);
  const [error, setError] = useState(false);
  const [privatePayloadRejected, setPrivatePayloadRejected] = useState(false);
  const [sending, setSending] = useState(false);
  const base = `/api/v1/admin/diagnostics/issues/${encodeURIComponent(issueId)}`;
  const load = useCallback(async () => {
    const value = await request<Conversation>(`${base}/conversation`);
    setConversation(value);
    setCursor(current => older.length ? current : value.next_cursor);
  }, [base, older.length]);
  useEffect(() => {
    let current = true;
    const poll = () => { if (current) void load().catch(() => { if (current) setError(true); }); };
    poll();
    const interval = window.setInterval(poll, 2000);
    return () => { current = false; window.clearInterval(interval); };
  }, [load]);
  const active = conversation?.runs.find(run => activeStates.has(run.state));
  const activeId = active?.id;
  useEffect(() => {
    if (!activeId || typeof EventSource === "undefined") return;
    const stream = new EventSource(`${base}/runs/${activeId}/stream`, { withCredentials: true });
    stream.onmessage = () => { void load().catch(() => setError(true)); };
    return () => { stream.close(); };
  }, [activeId, base, load]);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const action = (event.nativeEvent as SubmitEvent).submitter?.getAttribute("value") === "prepare_fix"
      ? "prepare_fix" : "analyze";
    const prompt = action === "prepare_fix"
      ? (english ? "Fix the issue and run tests." : "این مشکل را اصلاح کن و تست بگیر.")
      : (english ? "Explain the issue." : "این مشکل را توضیح بده.");
    void send(action, content.trim() || prompt, occurrenceId, action === "analyze" && !inspectCode);
  }

  async function send(action: "analyze" | "prepare_fix", message: string, occurrence: string | null, evidenceOnly: boolean) {
    if (sending || active) return;
    setSending(true); setError(false); setPrivatePayloadRejected(false);
    try {
      const payload = JSON.stringify({ content: message, action, occurrence_id: occurrence || null, ...(evidenceOnly ? { evidence_only: true } : {}) });
      const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(payload)))].map(value => value.toString(16).padStart(2, "0")).join("");
      const storageKey = `debug-submission:${issueId}`;
      let previous: { digest?: string; key?: string } = {};
      try { previous = JSON.parse(sessionStorage.getItem(storageKey) ?? "{}"); } catch { /* Invalid stale storage is ignored. */ }
      const key = previous.digest === digest && previous.key ? previous.key : crypto.randomUUID();
      sessionStorage.setItem(storageKey, JSON.stringify({ digest, key }));
      await request<Run>(`${base}/messages`, { method: "POST", headers: { "Idempotency-Key": key }, body: payload });
      sessionStorage.removeItem(storageKey);
      setContent(""); await load();
    } catch (cause) {
      setPrivatePayloadRejected(typeof cause === "object" && cause !== null && "code" in cause && cause.code === "sensitive_message_rejected");
      setError(true);
    } finally { setSending(false); }
  }
  async function cancel() {
    if (!active) return;
    try { await request(`${base}/runs/${active.id}/cancel`, { method: "POST" }); await load(); }
    catch { setError(true); }
  }
  async function loadOlder() {
    if (!cursor) return;
    try {
      const result = await request<Conversation>(`${base}/conversation?before=${encodeURIComponent(cursor)}`);
      setOlder(current => [...result.messages, ...current]); setCursor(result.next_cursor);
      setOlderRuns(current => [...result.runs, ...current].filter((run, index, all) => all.findIndex(other => other.id === run.id) === index));
    } catch { setError(true); }
  }
  const messages = [...older, ...(conversation?.messages ?? [])].filter((message, index, all) => all.findIndex(other => other.id === message.id) === index);
  const runs = [...(conversation?.runs ?? []), ...olderRuns].filter((run, index, all) => all.findIndex(other => other.id === run.id) === index);
  const linkedRun = (message: Message) => runs.find(run => run.id === message.run_id || run.message_id === message.id);
  const requestState = (run: Run) => {
    const message = messages.find(item => item.role === "user" && linkedRun(item)?.id === run.id);
    const hasTargetBlocker = ["execution_target_offline", "execution_target_not_authorized", "execution_target_changed", "repository_worker_required", "local_connector_not_configured"].includes(run.error_code ?? "");
    return <RunState key={run.id} base={base} run={run} english={english} autoLoad={runs.indexOf(run) < 5}
      onRunUpdate={updateHistoricalRun}
      onExplain={hasTargetBlocker && message && !active && !sending
        ? () => void send("analyze", english ? "Explain this occurrence from its recorded evidence." : "این رخداد را با شواهد ثبت‌شده توضیح بده.", run.occurrence_id ?? null, true)
        : undefined} />;
  };
  return <section className="diagnostics-card diagnostics-status-form debug-chat" dir={english ? "ltr" : "rtl"}>
    <h3>{english ? "Debug assistant" : "دستیار بررسی و رفع خطا"}</h3>
    {cursor && <button className="diagnostics-button diagnostics-button--quiet" type="button" onClick={() => void loadOlder()}>{english ? "Older messages" : "پیام‌های قدیمی‌تر"}</button>}
    <div className="debug-chat-history" aria-live="polite">{messages.map(message => {
      const run = linkedRun(message);
      return <article key={message.id} className="debug-chat-message" data-role={message.role}>
        <strong>{message.role === "assistant" ? (english ? "Debug assistant" : "دستیار بررسی خطا") : message.role === "system" ? (english ? "System" : "سیستم") : (english ? "Administrator" : "مدیر")}</strong>
        <p dir="auto">{message.content}</p>
        {message.role === "user" && run && requestState(run)}
        {message.role === "assistant" && (run
          ? <details><summary>{english ? "Reply details" : "جزئیات پاسخ"}</summary>
            <p><code dir="ltr">{modelName(run)}</code>{run.occurrence_id && <> · <code dir="ltr">{run.occurrence_id}</code></>}</p>
            <time dir="ltr">{message.created_at}</time>
          </details>
          : <small>{english ? "The model and occurrence for this historical reply are unknown." : "مدل و رخداد این پاسخ قدیمی مشخص نیست."}</small>)}
        {message.role === "assistant" && run?.config.runtime_mode === "mock" && <p>{mockLabel(english)}</p>}
      </article>;
    })}
    {runs.filter(run => !messages.some(message => message.role === "user" && linkedRun(message)?.id === run.id)).map(requestState)}
    </div>
    {error && <p role="alert">{privatePayloadRejected ? (english ? "Remove private payloads and reference evidence IDs. This message was not stored or sent to the model." : "اطلاعات خصوصی را حذف کنید و به شناسهٔ شواهد ارجاع بدهید.") : (english ? "The request could not be completed. You can retry." : "درخواست انجام نشد. دوباره تلاش کنید.")}</p>}
    <form onSubmit={submit}>
      <label>{english ? "Your message" : "سؤال شما (اختیاری)"}<textarea dir="auto" value={content} onChange={event => setContent(event.target.value)} maxLength={8000} rows={2} placeholder={english ? "Ask about this occurrence" : "دربارهٔ این رخداد بپرسید"} /></label>
      <div className="debug-chat-actions">
        <button className="diagnostics-button" type="submit" value="analyze" disabled={sending || Boolean(active)}>{english ? "Explain the issue" : "مشکل را توضیح بده"}</button>
        <button className="diagnostics-button diagnostics-button--quiet" type="submit" value="prepare_fix" disabled={sending || Boolean(active)}>{english ? "Fix it and run tests" : "اصلاحش کن و تست بگیر"}</button>
      </div>
      <label className="debug-chat-scope"><input type="checkbox" checked={inspectCode} onChange={event => setInspectCode(event.target.checked)} />{english ? "Use the selected laptop to inspect code when explaining" : "برای توضیح، کد را روی لپ‌تاپ منتخب بررسی کن"}</label>
      {active && <button className="diagnostics-button diagnostics-button--quiet" type="button" onClick={() => void cancel()}>{english ? "Cancel run" : "لغو اجرا"}</button>}
    </form>
  </section>;
}

const runLabels: Record<string, [string, string]> = {
  queued: ["Queued", "در صف"], investigating: ["Investigating", "در حال بررسی"],
  editing: ["Editing", "در حال اصلاح"], testing: ["Running tests", "در حال اجرای تست"],
  awaiting_authorization: ["Awaiting approval", "منتظر تأیید"], deploying: ["Deploying", "در حال انتشار"],
  verifying: ["Verifying", "در حال تأیید"], completed: ["Answered", "پاسخ ثبت شد"],
  blocked: ["Blocked", "متوقف شده"], failed: ["Failed", "ناموفق"], cancelled: ["Cancelled", "لغو شده"],
};

function modelName(run: Run) {
  return run.config.agent_model_id ?? run.config.primary_model_id;
}

function mockLabel(english: boolean) {
  return english ? "MOCK — no model or tools executed" : "آزمایشی (MOCK) · مدل و ابزار اجرا نشد";
}

function RunState({ onExplain, ...props }: Parameters<typeof RunProgress>[0] & { onExplain?: () => void }) {
  const { run, english } = props;
  const reason = explainDebugFailure(run.error_code, english);
  return <div className="debug-chat-run" data-state={run.state}>
    <strong>{runLabels[run.state]?.[english ? 0 : 1] ?? (english ? "Unknown state" : "وضعیت نامشخص")}</strong>
    {run.error_code && <p>{reason ?? (english ? "See execution details for the error code." : "کد خطا را در جزئیات اجرا ببینید.")}</p>}
    {run.config.runtime_mode === "mock" && <p>{mockLabel(english)}</p>}
    {onExplain && <button className="diagnostics-button diagnostics-button--quiet" type="button" onClick={onExplain}>{english ? "Explain from evidence" : "با شواهد توضیح بده"}</button>}
    <RunProgress {...props} />
  </div>;
}

interface ProgressEvent { id?: string; sequence: number; kind: string; payload: { tool?: string; mode?: string; model?: string; status?: string; pr_url?: string; commit?: string; output?: string; provenance?: string; service_request_id?: string } }
function RunProgress({ base, run, english, autoLoad = true, onRunUpdate }: { base: string; run: Run; english: boolean; autoLoad?: boolean; onRunUpdate: (run: Run) => void }) {
  const [expanded, setExpanded] = useState(false);
  const enabled = expanded || autoLoad || activeStates.has(run.state);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [received, setReceived] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    let current = true;
    let cursor = 0;
    async function refresh() {
      try {
        const page = await request<{ run?: Run; events: ProgressEvent[]; next_cursor: number }>(`${base}/runs/${run.id}/events?after=${cursor}`);
        if (!current) return;
        cursor = page.next_cursor;
        setReceived(true);
        if (page.run) onRunUpdate(page.run);
        setEvents(previous => [...previous, ...page.events].filter((item, index, all) => all.findIndex(other => other.sequence === item.sequence) === index).slice(-200));
      } catch { /* Conversation polling retains the actual durable run state. */ }
    }
    void refresh();
    const timer = activeStates.has(run.state) ? window.setInterval(() => void refresh(), 2000) : null;
    return () => { current = false; if (timer !== null) window.clearInterval(timer); };
  }, [base, run.id, run.state, enabled, onRunUpdate]);
  const recentChange = [...events].reverse().find(event => event.kind === "tool_completed" &&
    event.payload.tool === "fitician_write_file");
  const localTest = [...events].reverse().find(event => event.sequence > (recentChange?.sequence ?? 0) &&
    event.kind === "tool_completed" && ["fitician_run_tests", "fitician_validate"].includes(event.payload.tool ?? ""));
  let passed: boolean | undefined;
  try {
    const value = JSON.parse(localTest?.payload.output ?? "null")?.passed;
    if (typeof value === "boolean") passed = value;
  } catch { /* Unstructured legacy output remains available below. */ }
  return <>
    {passed !== undefined && <p>{passed ? (english ? "Laptop tests passed" : "تست‌های لپ‌تاپ موفق بود") : (english ? "Laptop tests failed" : "تست‌های لپ‌تاپ ناموفق بود")}</p>}
    {received && run.state === "completed" && run.action === "prepare_fix" && passed === undefined &&
      !events.some(event => event.kind === "automation_progress") &&
      <p>{english ? "No test result was recorded for this request." : "برای این درخواست نتیجهٔ تست ثبت نشده است."}</p>}
    <details onToggle={event => setExpanded(event.currentTarget.open)}>
      <summary>{english ? "Execution details" : "جزئیات اجرا"}</summary>
      <div className="debug-chat-identifiers" dir="ltr">
        {[run.id, modelName(run), run.config.connector_name, run.error_code, run.occurrence_id, run.evidence_id].filter(Boolean).map((value, index) => <code key={index}>{value}</code>)}
      </div>
      <ol dir="ltr">{events.map(event => <li key={event.sequence}>
        <code>{event.kind} {event.payload.tool ?? event.payload.mode ?? event.payload.model ?? ""} {event.payload.status ?? ""} {event.payload.commit ?? ""} {event.payload.service_request_id ?? ""}</code>
        {event.payload.pr_url && /^https:\/\/github\.com\/mohammad4242\/fitician\/pull\/[0-9]+$/.test(event.payload.pr_url) && <a href={event.payload.pr_url} target="_blank" rel="noreferrer"> PR</a>}
        {event.payload.output && <details><summary>{event.payload.provenance === "server_observation" ? (english ? "Recorded server observations; current health is unverified" : "مشاهدات ثبت‌شدهٔ سرور؛ سلامت فعلی تأیید نشده است") : (english ? "Tool evidence" : "مدرک ابزار")} · <code>{event.id}</code></summary><pre dir="ltr">{event.payload.output}</pre></details>}
      </li>)}</ol>
    </details>
  </>;
}
