import { createCommunicationApi, createMessageRequestId, type Conversation, type ConversationKind } from "@fitician/core";
import { useEffect, useMemo, useRef, useState } from "react";
import { AppState, Text, View } from "react-native";
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { Button, Card, TextField } from "../ui/components";
import { languageForDirection } from "../ui/rtl";
import { fiticianTokens } from "../ui/tokens";
export function ConversationPanel({ kind, reviewId, planId, initiallyOpen = false }: { initiallyOpen?: boolean; kind: ConversationKind; reviewId?: string; planId?: string }) {
  const auth = useMobileAuth();
  const api = useMemo(() => createCommunicationApi(auth.request), [auth.request]);
  const identity = auth.user?.id;
  const en = languageForDirection() === "en";
  const l = (fa: string, english: string) => en ? english : fa;
  const [data, setData] = useState<Conversation | null>(null);
  const [draft, setDraft] = useState("");
  const [open, setOpen] = useState(initiallyOpen);
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
        if (epoch.current === current) { setData(previous => previous?.review_id === loaded.review_id ? { ...loaded, older_cursor: previous.messages.length ? previous.older_cursor : loaded.older_cursor, messages: [...previous.messages.filter(message => !loaded.messages.some(next => next.id === message.id)), ...loaded.messages] } : loaded); setError(""); }
      } catch {
        if (epoch.current === current) { setError(en ? "Could not load conversation." : "دریافت گفت‌وگو ناموفق بود."); }
      }
    };
    void load();
    const timer = setInterval(() => { if (AppState.currentState === "active") void load(); }, 10000);
    return () => { epoch.current = current + 1; clearInterval(timer); };
  }, [api, identity, kind, reviewId, planId, attempt, en]);
  useEffect(() => {
    const last = data?.messages.at(-1);
    const current = epoch.current;
    if (!open || !last || !data?.review_id || !data.unread_count) return;
    void api.readConversation(kind, data.review_id, last.id).then(() => {
      if (epoch.current === current) setData(previous => previous && previous.messages.at(-1)?.id === last.id ? { ...previous, unread_count: 0 } : previous);
    }).catch(() => undefined);
  }, [api, open, data, kind]);
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
      if (epoch.current === current) setData(previous => previous?.review_id === loaded.review_id ? { ...loaded, older_cursor: previous.messages.length ? previous.older_cursor : loaded.older_cursor, messages: [...previous.messages.filter(message => !loaded.messages.some(next => next.id === message.id)), ...loaded.messages] } : loaded);
    } catch {
      if (epoch.current === current) setError(sent ? l("پیام ارسال شد؛ تاریخچه به‌روز نشد.", "Message sent; history could not refresh.") : l("ارسال ناموفق؛ دوباره تلاش کن.", "Send failed; retry."));
    } finally { if (epoch.current === current) { sending.current = false; setBusy(false); } }
  }
  async function older() {
    if (!data?.older_cursor || !data.review_id) return;
    const current = epoch.current;
    try {
      const loaded = await api.conversation(kind, { reviewId: data.review_id }, data.older_cursor);
      if (epoch.current === current) setData(previous => previous ? { ...previous, older_cursor: loaded.older_cursor, messages: [...loaded.messages.filter(m => !previous.messages.some(p => p.id === m.id)), ...previous.messages] } : loaded);
    } catch { if (epoch.current === current) setError(l("دریافت پیام‌های قبلی ناموفق بود.", "Could not load older messages.")); }
  }
  if (!identity) return null;
  return <Card><View style={{ gap: fiticianTokens.spacing[2] }}>
    <Button label={`${l("گفت‌وگو درباره برنامه", "Program conversation")}${data?.unread_count ? ` (${data.unread_count})` : ""}`} variant="secondary" onPress={() => setOpen(value => !value)} />
    {open && <>
      {error && <><Text accessibilityRole="alert" style={{ color: fiticianTokens.colors.danger }}>{error}</Text><Button label={l("تلاش دوباره", "Retry")} onPress={() => setAttempt(value => value + 1)} /></>}
      {!data?.available && <Text style={{ color: fiticianTokens.colors.ink }}>{l("ارسال پیام پس از تخصیص متخصص این برنامه فعال می‌شود.", "Messaging is available when a specialist is assigned to this program.")}</Text>}
      {data?.older_cursor && <Button variant="ghost" label={l("پیام‌های قبلی", "Older messages")} onPress={() => void older()} />}
      {data?.messages.map(message => <View key={message.id}><Text style={{ color: fiticianTokens.colors.aqua }}>{message.sender_id === data.viewer_id ? l("شما", "You") : l("طرف گفت‌وگو", "Participant")}</Text><Text style={{ color: fiticianTokens.colors.ink }}>{message.body}</Text><Text style={{ color: fiticianTokens.colors.ink }}>{new Date(message.created_at).toLocaleString(en ? "en-US" : "fa-IR")}</Text></View>)}
      <TextField accessibilityLabel={l("متن پیام", "Message")} label={l("متن پیام", "Message")} value={draft} multiline maxLength={2000} editable={data?.available === true && !busy} onChangeText={setDraft} />
      <Button label={busy ? l("در حال ارسال…", "Sending…") : l("ارسال", "Send")} disabled={!data?.available || busy || !draft.trim()} onPress={() => void send()} />
    </>}
  </View></Card>;
}
