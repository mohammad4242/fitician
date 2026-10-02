import { useEffect, useId, useRef, useState } from "react";
import { createMessageRequestId, mergeConversationLatest, type Conversation, type ConversationKind } from "@fitician/core";
import { useTranslation } from "react-i18next";
import { useAuthIdentity } from "../auth/AuthContext";
import { communicationApi as api } from "./api";
import { AppIcon } from "../../shared/AppIcon";
import "./conversationPanel.css";
export function ConversationPanel({ kind, reviewId, planId, initiallyOpen = false }: { initiallyOpen?: boolean; kind: ConversationKind; reviewId?: string; planId?: string }) {
  const panelId = useId();
  const identity = useAuthIdentity();
  const en = useTranslation().i18n.resolvedLanguage === "en";
  const l = (fa: string, english: string) => en ? english : fa;
  const [data, setData] = useState<Conversation | null>(null);
  const [open, setOpen] = useState(initiallyOpen);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const pending = useRef<{ body: string; id: string } | null>(null);
  const sending = useRef(false);
  const epoch = useRef(0);
  const target = useRef("");
  useEffect(() => {
    const current = ++epoch.current;
    const key = JSON.stringify([identity, kind, reviewId, planId]);
    if (target.current !== key) { setData(null); setDraft(""); pending.current = null; target.current = key; }
    setError(""); setBusy(false); sending.current = false;
    if (!identity) return;
    const load = async () => {
      try {
        const loaded = await api.conversation(kind, { reviewId, planId });
        if (epoch.current !== current) return;
        setData(previous => mergeConversationLatest(previous, loaded)); setError("");
      } catch {
        if (epoch.current === current) { setError(en ? "Could not load conversation; retry." : "دریافت گفت‌وگو ناموفق؛ دوباره تلاش کن."); }
      }
    };
    void load();
    const timer = setInterval(() => { if (document.visibilityState !== "hidden") void load(); }, 10000);
    return () => { epoch.current = current + 1; clearInterval(timer); };
  }, [identity, kind, reviewId, planId, attempt, en]);
  useEffect(() => {
    const last = data?.messages.at(-1);
    const current = epoch.current;
    if (!open || !last || !data?.review_id || !data.unread_count) return;
    void api.readConversation(kind, data.review_id, last.id).then(() => {
      if (epoch.current === current) setData(previous => previous && previous.messages.at(-1)?.id === last.id ? { ...previous, unread_count: 0 } : previous);
    }).catch(() => undefined);
  }, [open, data, kind]);
  async function send() {
    const body = draft.trim();
    if (!body || !data?.available || !data.review_id || sending.current) return;
    const current = epoch.current;
    sending.current = true; setBusy(true); setError("");
    if (pending.current?.body !== body) pending.current = { body, id: createMessageRequestId() };
    let sent = false;
    try {
      await api.send(kind, data.review_id, body, pending.current.id);
      if (epoch.current !== current) return;
      sent = true; setDraft(""); pending.current = null;
      const loaded = await api.conversation(kind, { reviewId: data.review_id });
      if (epoch.current === current) setData(previous => mergeConversationLatest(previous, loaded));
    } catch {
      if (epoch.current === current) setError(sent ? l("پیام ارسال شد؛ تاریخچه به‌روز نشد.", "Message sent; history could not refresh.") : l("ارسال ناموفق؛ دوباره تلاش کن.", "Send failed; retry."));
    } finally {
      if (epoch.current === current) { sending.current = false; setBusy(false); }
    }
  }
  async function older() {
    if (!data?.older_cursor || !data.review_id) return;
    const current = epoch.current;
    try {
      const older = await api.conversation(kind, { reviewId: data.review_id }, data.older_cursor);
      if (epoch.current === current) setData(previous => previous ? { ...previous, older_cursor: older.older_cursor, messages: [...older.messages.filter(m => !previous.messages.some(p => p.id === m.id)), ...previous.messages] } : older);
    } catch { if (epoch.current === current) setError(l("دریافت پیام‌های قبلی ناموفق بود.", "Could not load older messages.")); }
  }
  if (!identity) return null;
  return <section className="conversation-panel" dir={en ? "ltr" : "rtl"} aria-label={l("گفت‌وگو درباره برنامه", "Program conversation")}>
    <button type="button" className="conversation-panel__toggle" aria-expanded={open} aria-controls={panelId}
      aria-label={l("گفت‌وگو درباره برنامه", "Program conversation")}
      aria-describedby={data?.unread_count ? `${panelId}-unread` : undefined} onClick={() => setOpen(value => !value)}>
      <span className="conversation-panel__icon"><AppIcon name="feedback" /></span>
      <span className="conversation-panel__title">{l("گفت‌وگو درباره برنامه", "Program conversation")}</span>
      {!!data?.unread_count && <span id={`${panelId}-unread`} className="conversation-panel__unread" aria-label={l(`${data.unread_count} پیام خوانده‌نشده`, `${data.unread_count} unread messages`)}>{data.unread_count.toLocaleString(en ? "en-US" : "fa-IR")}</span>}
      <span className={`conversation-panel__chevron${open ? " conversation-panel__chevron--open" : ""}`}><AppIcon name="chevron" /></span>
    </button>
    {open && <div id={panelId} className="conversation-panel__content">
      {error && <div className="conversation-panel__error" role="alert"><p>{error}</p><button type="button" onClick={() => setAttempt(value => value + 1)}>{l("تلاش دوباره", "Retry")}</button></div>}
      {!data && !error && <p className="conversation-panel__notice" role="status">{l("در حال دریافت گفت‌وگو…", "Loading conversation…")}</p>}
      {data?.available === false && <div className="conversation-panel__notice"><AppIcon name="feedback" /><p>{kind === "workout"
        ? l("ارسال پیام پس از تخصیص مربی برای برنامه‌ی شما فعال می‌شود.", "Messaging is available when a coach is assigned to your program.")
        : l("ارسال پیام پس از تخصیص متخصص این برنامه فعال می‌شود.", "Messaging is available when a specialist is assigned to this program.")}</p></div>}
      {data?.available && <>
        {data.older_cursor && <button type="button" className="conversation-panel__older" onClick={() => void older()}>{l("پیام‌های قبلی", "Older messages")}</button>}
        <ol className="conversation-panel__messages" aria-label={l("پیام‌های برنامه", "Program messages")}>
          {data.messages.map(message => <li key={message.id} className={`conversation-panel__bubble conversation-panel__bubble--${message.sender_id === data.viewer_id ? "own" : "other"}`}>
            <span className="conversation-panel__sender">{message.sender_id === data.viewer_id ? l("شما", "You") : l("طرف گفت‌وگو", "Participant")}</span>
            <p dir="auto">{message.body}</p>
            <time dateTime={message.created_at}>{new Date(message.created_at).toLocaleString(en ? "en-US" : "fa-IR")}</time>
          </li>)}
        </ol>
        {data.messages.length === 0 && <p className="conversation-panel__empty">{l("پرسشت درباره این برنامه را اینجا بنویس.", "Ask a question about this program here.")}</p>}
        <div className="conversation-panel__composer">
          <label htmlFor={`${panelId}-draft`}>{l("متن پیام", "Message")}</label>
          <textarea id={`${panelId}-draft`} dir="auto" rows={3} value={draft} maxLength={2000} disabled={busy} onChange={event => setDraft(event.target.value)} />
          <button type="button" className="conversation-panel__send" disabled={busy || !draft.trim()} onClick={() => void send()}>{busy ? l("در حال ارسال…", "Sending…") : l("ارسال", "Send")}</button>
        </div>
      </>}
    </div>}
  </section>;
}
