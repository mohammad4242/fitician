import { createCommunicationApi, createMessageRequestId, mergeConversationLatest, type Conversation, type ConversationKind } from "@fitician/core";
import { useEffect, useMemo, useRef, useState } from "react";
import { AppState, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { AppIcon, Button, Card, TextField } from "../ui/components";
import { getTextDirectionStyle, languageForDirection } from "../ui/rtl";
import { fiticianTokens } from "../ui/tokens";
export function ConversationPanel({ kind, reviewId, planId, initiallyOpen = false }: { initiallyOpen?: boolean; kind: ConversationKind; reviewId?: string; planId?: string }) {
  const auth = useMobileAuth();
  const api = useMemo(() => createCommunicationApi(auth.request), [auth.request]);
  const identity = auth.user?.id;
  const en = languageForDirection() === "en";
  const l = (fa: string, english: string) => en ? english : fa;
  const direction = en ? "ltr" : "rtl";
  const textStyle = { ...getTextDirectionStyle(direction), fontFamily: en ? fiticianTokens.typography.fontFamily.bodyEnglish : fiticianTokens.typography.fontFamily.bodyPersian };
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
        if (epoch.current === current) { setData(previous => mergeConversationLatest(previous, loaded)); setError(""); }
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
      if (epoch.current === current) setData(previous => mergeConversationLatest(previous, loaded));
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
  return <Card direction={direction} style={styles.container} testID="conversation-panel">
    <Pressable accessibilityRole="button" accessibilityState={{ expanded: open }}
      accessibilityLabel={l("گفت‌وگو درباره برنامه", "Program conversation")}
      accessibilityHint={data?.unread_count ? l(`${data.unread_count} پیام خوانده‌نشده`, `${data.unread_count} unread messages`) : undefined}
      onPress={() => setOpen(value => !value)} style={({ pressed }) => [styles.toggle, pressed && styles.pressed]}>
      <View style={styles.icon}><AppIcon name="feedback" color={fiticianTokens.colors.aqua} size={20} /></View>
      <Text style={[styles.title, textStyle]}>{l("گفت‌وگو درباره برنامه", "Program conversation")}</Text>
      {!!data?.unread_count && <View style={styles.unreadBadge}><Text style={[styles.unreadText, textStyle]}>{data.unread_count.toLocaleString(en ? "en-US" : "fa-IR")}</Text></View>}
      <AppIcon name={open ? "chevronUp" : "chevronDown"} color={fiticianTokens.colors.muted} size={20} style={styles.chevron} />
    </Pressable>
    {open && <View style={styles.content}>
      {error && <View style={styles.error}><Text accessibilityRole="alert" style={[styles.errorText, textStyle]}>{error}</Text><Button variant="ghost" label={l("تلاش دوباره", "Retry")} onPress={() => setAttempt(value => value + 1)} /></View>}
      {!data && !error && <Text accessibilityRole="text" style={[styles.noticeText, textStyle]}>{l("در حال دریافت گفت‌وگو…", "Loading conversation…")}</Text>}
      {data?.available === false && <View style={styles.locked}><AppIcon name="feedback" size={20} color={fiticianTokens.colors.muted} /><Text style={[styles.noticeText, styles.lockedText, textStyle]}>{kind === "workout"
        ? l("ارسال پیام پس از تخصیص مربی برای برنامه‌ی شما فعال می‌شود.", "Messaging is available when a coach is assigned to your program.")
        : l("ارسال پیام پس از تخصیص متخصص این برنامه فعال می‌شود.", "Messaging is available when a specialist is assigned to this program.")}</Text></View>}
      {data?.available && <>
        {data.older_cursor && <Button variant="ghost" label={l("پیام‌های قبلی", "Older messages")} onPress={() => void older()} />}
        {data.messages.length > 0 ? <ScrollView nestedScrollEnabled style={styles.messagesRegion} contentContainerStyle={styles.messages}>
          {data.messages.map(message => <View key={message.id} style={[styles.bubble, message.sender_id === data.viewer_id ? styles.ownBubble : styles.otherBubble]}>
            <Text style={[styles.sender, textStyle]}>{message.sender_id === data.viewer_id ? l("شما", "You") : l("طرف گفت‌وگو", "Participant")}</Text>
            <Text style={[styles.messageText, { fontFamily: textStyle.fontFamily, writingDirection: "auto", textAlign: "auto" }]}>{message.body}</Text>
            <Text style={[styles.timestamp, textStyle]}>{new Date(message.created_at).toLocaleString(en ? "en-US" : "fa-IR")}</Text>
          </View>)}
        </ScrollView> : <Text style={[styles.noticeText, textStyle]}>{l("پرسشت درباره این برنامه را اینجا بنویس.", "Ask a question about this program here.")}</Text>}
        <View style={styles.composer}>
          <Text style={[styles.sender, textStyle]}>{l("متن پیام", "Message")}</Text>
          <TextField accessibilityLabel={l("متن پیام", "Message")} value={draft} multiline maxLength={2000} textDirection="auto" textAlignVertical="top" editable={!busy} style={styles.input} onChangeText={setDraft} />
          <View style={styles.sendAction}><Button label={busy ? l("در حال ارسال…", "Sending…") : l("ارسال", "Send")} disabled={busy || !draft.trim()} onPress={() => void send()} /></View>
        </View>
      </>}
    </View>}
  </Card>;
}

const t = fiticianTokens;
const styles = StyleSheet.create({
  container: { padding: 0, minWidth: 0, overflow: "hidden" },
  toggle: { flexDirection: "row", alignItems: "center", gap: t.spacing[3], padding: t.spacing[4], minHeight: 64 },
  pressed: { backgroundColor: t.colors.surfaceInteractive },
  icon: { width: 36, height: 36, alignItems: "center", justifyContent: "center", backgroundColor: t.colors.aquaAtmosphere, borderRadius: t.radii.small },
  title: { flex: 1, flexShrink: 1, color: t.colors.ink, fontSize: t.typography.fontSize.body, fontWeight: "700" },
  unreadBadge: { minWidth: 24, minHeight: 24, paddingHorizontal: t.spacing[2], alignItems: "center", justifyContent: "center", borderRadius: t.radii.pill, backgroundColor: t.colors.aqua },
  unreadText: { color: t.colors.canvas, fontSize: t.typography.fontSize.xs, fontWeight: "700" },
  chevron: { flexShrink: 0 },
  content: { borderTopWidth: 1, borderTopColor: t.colors.line, padding: t.spacing[3], gap: t.spacing[3] },
  locked: { flexDirection: "row", alignItems: "center", gap: t.spacing[3] },
  lockedText: { flex: 1, flexShrink: 1 },
  noticeText: { color: t.colors.muted, fontSize: t.typography.fontSize.sm, lineHeight: 24 },
  messagesRegion: { maxHeight: 400 },
  messages: { gap: t.spacing[3], paddingVertical: t.spacing[1] },
  bubble: { maxWidth: "88%", minWidth: 0, padding: t.spacing[3], borderWidth: 1, borderColor: t.colors.line, borderRadius: t.radii.large, gap: t.spacing[1] },
  ownBubble: { alignSelf: "flex-start", backgroundColor: t.colors.teal, borderColor: t.colors.lineStrong, borderTopStartRadius: t.radii.small },
  otherBubble: { alignSelf: "flex-end", backgroundColor: t.colors.surfaceRaised, borderTopEndRadius: t.radii.small },
  sender: { color: t.colors.muted, fontSize: t.typography.fontSize.xs },
  messageText: { color: t.colors.ink, fontSize: t.typography.fontSize.body, lineHeight: 26, flexShrink: 1 },
  timestamp: { color: t.colors.muted, fontSize: t.typography.fontSize.xs, marginTop: t.spacing[1] },
  composer: { borderTopWidth: 1, borderTopColor: t.colors.line, paddingTop: t.spacing[4], gap: t.spacing[2] },
  input: { minHeight: 104, backgroundColor: t.colors.surfaceSubtle },
  sendAction: { alignSelf: "flex-end", minWidth: 96 },
  error: { gap: t.spacing[2], padding: t.spacing[3], borderRadius: t.radii.small, backgroundColor: t.colors.dangerSurface },
  errorText: { color: t.colors.danger, fontSize: t.typography.fontSize.sm, lineHeight: 24 },
});
