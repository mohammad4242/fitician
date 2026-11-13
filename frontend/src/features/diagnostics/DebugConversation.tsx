import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { request } from "../../shared/apiClient";

interface Run { id: string; state: string; error_code: string | null; config: { primary_model_id?: string; agent_model_id?: string; connector_name?: string | null }; evidence_id: string | null; occurrence_id?: string | null }
interface Message { id: string; role: string; content: string; created_at: string }
interface Conversation { messages: Message[]; runs: Run[]; next_cursor: string | null }
const activeStates = new Set(["queued", "investigating", "editing", "testing", "awaiting_authorization", "deploying", "verifying"]);

function executionBlocker(code: string | null, english: boolean): string | null {
  switch (code) {
    case "execution_target_offline":
      return english ? "The selected execution target is offline. Check its connection." : "اتصال اجرای منتخب آفلاین است. اتصال آن را بررسی کنید.";
    case "workspace_capacity_reached":
    case "repository_capacity_reached":
      return english ? "Execution capacity is full. Check free disk and retained repair workspaces." : "ظرفیت فضای اجرای ایجنت پر است. دیسک آزاد و فضای تعمیرهای نگه‌داری‌شده را بررسی کنید.";
    case "exact_release_commit_required":
    case "release_commit_not_available":
      return english ? "The exact failing source is unavailable. Check its release and commit access." : "نسخهٔ دقیق خطادار برای بررسی آماده نیست. شناسهٔ انتشار و دسترسی به commit را بررسی کنید.";
    case "workspace_not_clean":
    case "workspace_identity_mismatch":
    case "workspace_release_mismatch":
    case "workspace_branch_mismatch":
    case "workspace_branch_not_owned":
      return english ? "Workspace identity or changes need review. Existing work was preserved." : "نسخه یا تغییرات فضای کار به بررسی نیاز دارد. کار موجود حفظ شده است.";
    case "interrupted_call_requires_new_run":
      return english ? "The previous execution was interrupted. Review its recorded actions before a new run." : "اجرای قبلی قطع شده است. پیش از شروع دوباره، فعالیت‌های ثبت‌شدهٔ آن را بررسی کنید.";
    default:
      return null;
  }
}

export function DebugConversation({ issueId, english, occurrenceId = "" }: { issueId: string; english: boolean; occurrenceId?: string }) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [older, setOlder] = useState<Message[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [action, setAction] = useState("analyze");
  const [error, setError] = useState(false);
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
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!content.trim() || sending) return;
    setSending(true); setError(false);
    try {
      const payload = JSON.stringify({ content, action, occurrence_id: occurrenceId || null });
      const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(payload)))].map(value => value.toString(16).padStart(2, "0")).join("");
      const storageKey = `debug-submission:${issueId}`;
      let previous: { digest?: string; key?: string } = {};
      try { previous = JSON.parse(sessionStorage.getItem(storageKey) ?? "{}"); } catch { /* Invalid stale storage is ignored. */ }
      const key = previous.digest === digest && previous.key ? previous.key : crypto.randomUUID();
      sessionStorage.setItem(storageKey, JSON.stringify({ digest, key }));
      await request<Run>(`${base}/messages`, { method: "POST", headers: { "Idempotency-Key": key }, body: payload });
      sessionStorage.removeItem(storageKey);
      setContent(""); await load();
    } catch { setError(true); } finally { setSending(false); }
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
    } catch { setError(true); }
  }
  const messages = [...older, ...(conversation?.messages ?? [])].filter((message, index, all) => all.findIndex(other => other.id === message.id) === index);
  return <section className="diagnostics-card">
    <h3>{english ? "Conversation with debug_agent" : "گفت‌وگو با debug_agent"}</h3>
    <p>{english ? "Analysis uses the configured model and selected evidence. Model statements do not establish a confirmed cause. Execution and deployment require configured capabilities." : "تحلیل با مدل تنظیم‌شده و شواهد این issue انجام می‌شود. گفته مدل به‌تنهایی علت قطعی را اثبات نمی‌کند. اجرا و استقرار به قابلیت متصل و مجوز مشخص نیاز دارند."}</p>
    <p>{english ? "Selected occurrence" : "رخداد منتخب"}: <code dir="ltr">{occurrenceId || (english ? "Latest available evidence" : "آخرین شواهد موجود")}</code></p>
    {cursor && <button type="button" onClick={() => void loadOlder()}>{english ? "Older messages" : "پیام‌های قدیمی‌تر"}</button>}
    <div aria-live="polite">{messages.map(message => <article key={message.id} style={{ borderBlockEnd: "1px solid var(--border-color, #ddd)", paddingBlock: "1rem" }}>
      <strong>{message.role === "assistant" ? "debug_agent" : message.role === "system" ? (english ? "System" : "سیستم") : (english ? "Administrator" : "مدیر")}</strong>
      <time style={{ display: "block", fontSize: "0.8rem" }}>{message.created_at}</time>
      <p dir="auto" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{message.content}</p>
    </article>)}</div>
    {conversation?.runs.slice(0, 5).map(run => <p key={run.id} dir={english ? "ltr" : "rtl"} style={{ overflowWrap: "anywhere" }}><code>{run.state}</code> · <code dir="ltr">{run.config.primary_model_id ?? run.config.agent_model_id ?? "unconfigured"}</code>{run.config.connector_name && <> · {english ? "Execution target" : "محل اجرا"}: <bdi>{run.config.connector_name}</bdi></>}{executionBlocker(run.error_code, english) && <> · {executionBlocker(run.error_code, english)}</>}{run.error_code && <> · <code>{run.error_code}</code></>}{run.occurrence_id && <> · {english ? "Occurrence" : "رخداد"}: <code>{run.occurrence_id}</code></>}{run.evidence_id && <> · <code>{run.evidence_id}</code></>}</p>)}
    {conversation?.runs.slice(0, 5).map(run => <RunProgress key={run.id} base={base} run={run} english={english} />)}
    {error && <p role="alert">{english ? "The request could not be completed. You can retry; repeated submissions use the same request identity." : "درخواست انجام نشد. می‌توانید دوباره تلاش کنید؛ ارسال تکراری با همان شناسه پیگیری می‌شود."}</p>}
    <form onSubmit={event => void submit(event)}>
      <label>{english ? "Requested action" : "درخواست مجاز"}<select value={action} onChange={event => setAction(event.target.value)}><option value="analyze">{english ? "Investigate, read only" : "بررسی فقط‌خواندنی"}</option><option value="prepare_fix">{english ? "Prepare and test a fix in an isolated branch" : "آماده‌سازی و آزمون اصلاح در شاخهٔ جدا"}</option></select></label>
      <label>{english ? "Your message" : "پیام شما"}<textarea value={content} onChange={event => setContent(event.target.value)} maxLength={8000} rows={4} /></label>
      <button type="submit" disabled={sending || Boolean(active) || !content.trim()}>{english ? "Send for analysis" : "ارسال برای بررسی"}</button>
      {active && <button type="button" onClick={() => void cancel()}>{english ? "Cancel run" : "لغو اجرا"}</button>}
    </form>
  </section>;
}


interface ProgressEvent { id?: string; sequence: number; kind: string; payload: { tool?: string; mode?: string; model?: string; status?: string; pr_url?: string; commit?: string; output?: string; provenance?: string } }
function RunProgress({ base, run, english }: { base: string; run: Run; english: boolean }) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  useEffect(() => {
    let current = true;
    let cursor = 0;
    async function refresh() {
      try {
        const page = await request<{ events: ProgressEvent[]; next_cursor: number }>(`${base}/runs/${run.id}/events?after=${cursor}`);
        if (!current) return;
        cursor = page.next_cursor;
        setEvents(previous => [...previous, ...page.events].filter((item, index, all) => all.findIndex(other => other.sequence === item.sequence) === index).slice(-200));
      } catch { /* Conversation polling retains the actual durable run state. */ }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => { current = false; window.clearInterval(timer); };
  }, [base, run.id]);
  return <details><summary>{english ? "Recorded execution activity" : "فعالیت اجرایی ثبت‌شده"} · <code>{run.id.slice(0, 8)}</code></summary><ol dir="ltr" style={{ overflowWrap: "anywhere" }}>{events.map(event => <li key={event.sequence}><code>{event.kind} {event.payload.tool ?? event.payload.mode ?? event.payload.model ?? ""} {event.payload.status ?? ""} {event.payload.commit ?? ""}</code>{event.payload.pr_url && /^https:\/\/github\.com\/mohammad4242\/fitician\/pull\/[0-9]+$/.test(event.payload.pr_url) && <a href={event.payload.pr_url} target="_blank" rel="noreferrer"> PR</a>}{event.payload.output && <details><summary>{event.payload.provenance === "server_observation" ? (english ? "Recorded server observations; current health is unverified" : "مشاهدات ثبت‌شدهٔ سرور؛ سلامت فعلی تأیید نشده است") : (english ? "Tool evidence" : "مدرک ابزار")} · <code>{event.id}</code></summary><pre dir="ltr" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{event.payload.output}</pre></details>}</li>)}</ol></details>;
}
