import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { request } from "../../shared/apiClient";

interface Run { id: string; state: string; error_code: string | null; config: { primary_model_id?: string; agent_model_id?: string }; evidence_id: string | null }
interface Message { id: string; role: string; content: string; created_at: string }
interface Conversation { messages: Message[]; runs: Run[]; next_cursor: string | null }
const activeStates = new Set(["queued", "investigating", "editing", "testing", "awaiting_authorization", "deploying", "verifying"]);

export function DebugConversation({ issueId, english }: { issueId: string; english: boolean }) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [older, setOlder] = useState<Message[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [content, setContent] = useState("");
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
      const payload = JSON.stringify({ content, action: "analyze" });
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
    {cursor && <button type="button" onClick={() => void loadOlder()}>{english ? "Older messages" : "پیام‌های قدیمی‌تر"}</button>}
    <div aria-live="polite">{messages.map(message => <article key={message.id} style={{ borderBlockEnd: "1px solid var(--border-color, #ddd)", paddingBlock: "1rem" }}>
      <strong>{message.role === "assistant" ? "debug_agent" : (english ? "Administrator" : "مدیر")}</strong>
      <time style={{ display: "block", fontSize: "0.8rem" }}>{message.created_at}</time>
      <p dir="auto" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{message.content}</p>
    </article>)}</div>
    {conversation?.runs.slice(0, 5).map(run => <p key={run.id} dir="auto"><code>{run.state}</code> · <code dir="ltr">{run.config.primary_model_id ?? run.config.agent_model_id ?? "unconfigured"}</code>{run.error_code && <> · <code>{run.error_code}</code></>}{run.evidence_id && <> · <code>{run.evidence_id}</code></>}</p>)}
    {error && <p role="alert">{english ? "The request could not be completed. You can retry; repeated submissions use the same request identity." : "درخواست انجام نشد. می‌توانید دوباره تلاش کنید؛ ارسال تکراری با همان شناسه پیگیری می‌شود."}</p>}
    <form onSubmit={event => void submit(event)}>
      <label>{english ? "Your message" : "پیام شما"}<textarea value={content} onChange={event => setContent(event.target.value)} maxLength={8000} rows={4} /></label>
      <button type="submit" disabled={sending || Boolean(active) || !content.trim()}>{english ? "Send for analysis" : "ارسال برای بررسی"}</button>
      {active && <button type="button" onClick={() => void cancel()}>{english ? "Cancel run" : "لغو اجرا"}</button>}
    </form>
  </section>;
}
