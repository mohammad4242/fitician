import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Constants from "expo-constants";
import { useRouter } from "expo-router";
import {
  createMessageRequestId,
  createSupportApi,
  helpCategories,
  helpCategoryLabels,
  searchHelp,
  supportCategories,
  supportCategoryLabels,
  supportContacts,
  supportCopy,
  supportStatusLabels,
  mergeSupportMessages,
  type HelpCategory,
  type SupportCategory,
  type SupportDetail,
  type SupportTicket,
  type SupportMetadata,
} from "@fitician/core";
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { Button } from "../ui/components/Button";
import { Card } from "../ui/components/Card";
import { TextField } from "../ui/components/Input";
import { Screen } from "../ui/layout";
import { getTextDirectionStyle } from "../ui/rtl";
import { useMemberFeatureLanguage } from "../ui/useMemberFeatureLanguage";
import { fiticianTokens as tokens } from "../ui/tokens";
export function SupportScreen({
  mode = "home",
  ticketId,
}: {
  mode?: "home" | "tickets" | "new" | "detail";
  ticketId?: string;
}) {
  const auth = useMobileAuth(),
    router = useRouter(),
    api = useMemo(() => createSupportApi(auth.request), [auth.request]),
    [language, changeLanguage] = useMemberFeatureLanguage(),
    c = supportCopy[language],
    direction = language === "fa" ? "rtl" : "ltr",
    text = getTextDirectionStyle(direction);
  const [query, setQuery] = useState(""),
    [helpCategory, setHelpCategory] = useState<HelpCategory>(),
    [expanded, setExpanded] = useState<string | null>(null),
    [category, setCategory] = useState<SupportCategory>("technical"),
    [subject, setSubject] = useState(""),
    [body, setBody] = useState(""),
    [tickets, setTickets] = useState<SupportTicket[]>([]),
    [detail, setDetail] = useState<SupportDetail | null>(null),
    [cursor, setCursor] = useState<string | null>(null),
    [loading, setLoading] = useState(mode === "tickets" || mode === "detail"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(false);
  const epoch = useRef(0),
    mounted = useRef(true),
    sending = useRef(false),
    pending = useRef<{
      key: string;
      id: string;
      metadata: SupportMetadata;
    } | null>(null);
  const load = useCallback(
    async (before?: string) => {
      if (mode !== "tickets" && mode !== "detail") return;
      const generation = ++epoch.current;
      setLoading(true);
      setError(false);
      try {
        if (mode === "tickets") {
          const page = await api.list({ before });
          if (generation !== epoch.current) return;
          setTickets((prev) =>
            before
              ? [
                  ...new Map(
                    [...prev, ...page.items].map((t) => [t.id, t]),
                  ).values(),
                ]
              : page.items,
          );
          setCursor(page.older_cursor);
        } else if (ticketId) {
          const next = await api.detail(ticketId, before);
          if (generation !== epoch.current) return;
          setDetail((prev) =>
            before && prev
              ? {
                  ...next,
                  messages: mergeSupportMessages(next.messages, prev.messages),
                }
              : next,
          );
          const last = next.messages.at(-1);
          if (last) void api.read(ticketId, last.id).catch(() => undefined);
        }
      } catch {
        if (generation === epoch.current) setError(true);
      } finally {
        if (generation === epoch.current) setLoading(false);
      }
    },
    [api, mode, ticketId],
  );
  useEffect(() => {
    mounted.current = true;
    setTickets([]);
    setDetail(null);
    setBody("");
    setSubject("");
    pending.current = null;
    void load();
    return () => {
      mounted.current = false;
      epoch.current++;
    };
  }, [load, auth.user?.id]);
  async function send() {
    if (sending.current || !body.trim() || (mode === "new" && !subject.trim()))
      return;
    const key = JSON.stringify([
      mode,
      ticketId,
      category,
      subject.trim(),
      body.trim(),
    ]);
    if (pending.current?.key !== key)
      pending.current = {
        key,
        id: createMessageRequestId(),
        metadata: {
          platform:
            Platform.OS === "ios"
              ? "ios"
              : Platform.OS === "android"
                ? "android"
                : "web",
          locale: language,
          app_version: Constants.expoConfig?.version?.slice(0, 40) ?? null,
          build_version: Constants.nativeBuildVersion?.slice(0, 40) ?? null,
        },
      };
    const generation = epoch.current;
    sending.current = true;
    setBusy(true);
    setError(false);
    try {
      if (mode === "new") {
        const created = await api.create({
          category,
          subject: subject.trim(),
          description: body.trim(),
          request_id: pending.current.id,
          metadata: pending.current.metadata,
        });
        if (mounted.current && generation === epoch.current)
          router.replace({
            pathname: "/member/support-ticket/[ticketId]",
            params: { ticketId: created.id },
          });
      } else if (ticketId) {
        const message = await api.reply(
          ticketId,
          body.trim(),
          pending.current.id,
        );
        if (mounted.current && generation === epoch.current) {
          setDetail((prev) =>
            prev
              ? {
                  ...prev,
                  ticket: {
                    ...prev.ticket,
                    status: "open",
                    last_activity_at: message.created_at,
                  },
                  messages: mergeSupportMessages(prev.messages, [message]),
                }
              : prev,
          );
          setBody("");
          pending.current = null;
          void load();
        }
      }
    } catch {
      if (mounted.current && generation === epoch.current) setError(true);
    } finally {
      sending.current = false;
      if (mounted.current && generation === epoch.current) setBusy(false);
    }
  }
  const stamp = (value: string) =>
    new Intl.DateTimeFormat(language, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  const paragraph = (value: string, key?: string) => (
    <Text key={key} style={[styles.text, text]}>
      {value}
    </Text>
  );
  return (
    <Screen
      keyboardAware
      contentWidth="reading"
      contentContainerStyle={{ direction }}
    >
      <View style={styles.stack}>
        <Button
          variant="ghost"
          label={language === "fa" ? "English" : "فارسی"}
          onPress={() => changeLanguage(language === "fa" ? "en" : "fa")}
        />
        <Text accessibilityRole="header" style={[styles.title, text]}>
          {mode === "home"
            ? c.hero
            : mode === "tickets"
              ? c.tickets
              : mode === "new"
                ? c.create
                : (detail?.ticket.subject ?? c.title)}
        </Text>
        <View style={[styles.row, { direction }]}>
          <Button
            variant="ghost"
            label={c.help}
            onPress={() => router.push("/member/support")}
          />
          <Button
            variant="ghost"
            label={c.tickets}
            onPress={() => router.push("/member/support-tickets")}
          />
        </View>
        {error && (
          <Card direction={direction}>
            <Text accessibilityRole="alert" style={[styles.text, text]}>
              {c.error}
            </Text>
            {mode === "tickets" || mode === "detail" ? (
              <Button label={c.retry} onPress={() => void load()} />
            ) : null}
          </Card>
        )}
        {loading && (
          <ActivityIndicator
            accessibilityLabel={c.loading}
            color={tokens.colors.aqua}
          />
        )}
        {mode === "home" && (
          <>
            <TextField
              labelDirection={direction}
              label={c.search}
              value={query}
              onChangeText={setQuery}
              textDirection={direction}
            />
            <View style={[styles.row, { direction }]}>
              <Button
                variant="ghost"
                label={c.all}
                accessibilityState={{ selected: !helpCategory }}
                onPress={() => setHelpCategory(undefined)}
              />
              {helpCategories.map((id) => (
                <Button
                  key={id}
                  variant="ghost"
                  label={helpCategoryLabels[language][id]}
                  accessibilityState={{ selected: helpCategory === id }}
                  onPress={() => setHelpCategory(id)}
                />
              ))}
            </View>
            {!searchHelp(language, query, helpCategory).length &&
              paragraph(c.noResults)}
            {searchHelp(language, query, helpCategory).map((a) => (
              <Card key={a.id} direction={direction}>
                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{ expanded: expanded === a.id }}
                  onPress={() => setExpanded(expanded === a.id ? null : a.id)}
                  style={styles.article}
                >
                  <Text style={[styles.subtitle, text]}>
                    {a.content[language].title}
                  </Text>
                </Pressable>
                {expanded === a.id &&
                  a.content[language].paragraphs.map((p, i) =>
                    paragraph(p, `${a.id}-${i}`),
                  )}
              </Card>
            ))}
            <Button
              label={c.create}
              onPress={() => router.push("/member/support-new")}
            />
            <Card direction={direction}>
              {paragraph(c.title)}
              <Button
                variant="ghost"
                label={supportContacts.email}
                onPress={() =>
                  void Linking.openURL(`mailto:${supportContacts.email}`).catch(
                    () => setError(true),
                  )
                }
              />
              <Button
                variant="ghost"
                label={supportContacts.instagramHandle}
                onPress={() =>
                  void Linking.openURL(supportContacts.instagramUrl).catch(() =>
                    setError(true),
                  )
                }
              />
            </Card>
          </>
        )}
        {mode === "tickets" && (
          <>
            <Button
              label={c.create}
              onPress={() => router.push("/member/support-new")}
            />
            {!loading && !error && !tickets.length && (
              <Card direction={direction}>
                {paragraph(c.empty)}
                {paragraph(c.emptyHint)}
              </Card>
            )}
            {tickets.map((t) => (
              <Card
                key={t.id}
                direction={direction}
                onPress={() =>
                  router.push({
                    pathname: "/member/support-ticket/[ticketId]",
                    params: { ticketId: t.id },
                  })
                }
              >
                <Text style={[styles.subtitle, text]}>{t.subject}</Text>
                {paragraph(supportStatusLabels[language][t.status])}
                {paragraph(`${c.activity}: ${stamp(t.last_activity_at)}`)}
              </Card>
            ))}
            {cursor && (
              <Button
                variant="ghost"
                disabled={loading}
                label={c.older}
                onPress={() => void load(cursor)}
              />
            )}
          </>
        )}
        {mode === "detail" && detail && (
          <>
            {paragraph(supportStatusLabels[language][detail.ticket.status])}
            <Button
              variant="ghost"
              disabled={loading}
              label={c.refresh}
              onPress={() => void load()}
            />
            {detail.older_cursor && (
              <Button
                variant="ghost"
                disabled={loading}
                label={c.older}
                onPress={() => void load(detail.older_cursor!)}
              />
            )}
            {detail.messages.map((m) => (
              <Card
                key={m.id}
                direction={direction}
                style={m.sender_role === "admin" ? styles.admin : undefined}
              >
                <Text style={[styles.subtitle, text]}>
                  {m.sender_role === "admin" ? c.admin : c.member}
                </Text>
                {paragraph(stamp(m.created_at))}
                <Text
                  style={[styles.text, { writingDirection: "auto" }]}
                  selectable
                >
                  {m.body}
                </Text>
              </Card>
            ))}
            {detail.ticket.status === "closed" && paragraph(c.closed)}
            {detail.ticket.status === "resolved" && paragraph(c.resolved)}
          </>
        )}
        {(mode === "new" ||
          (mode === "detail" &&
            detail &&
            detail.ticket.status !== "closed")) && (
          <>
            {mode === "new" && (
              <>
                <Text style={[styles.subtitle, text]}>{c.category}</Text>
                <View style={[styles.row, { direction }]}>
                  {supportCategories.map((id) => (
                    <Button
                      key={id}
                      disabled={busy}
                      variant={category === id ? "secondary" : "ghost"}
                      accessibilityState={{ selected: category === id }}
                      label={supportCategoryLabels[language][id]}
                      onPress={() => setCategory(id)}
                    />
                  ))}
                </View>
                <TextField
                  labelDirection={direction}
                  label={c.subject}
                  value={subject}
                  onChangeText={setSubject}
                  maxLength={160}
                  editable={!busy}
                  textDirection={direction}
                />
              </>
            )}
            <TextField
              labelDirection={direction}
              label={mode === "new" ? c.description : c.message}
              value={body}
              onChangeText={setBody}
              multiline
              maxLength={4000}
              editable={!busy}
              textDirection={direction}
              style={styles.composer}
            />
            {paragraph(c.privacy)}
            <Button
              label={mode === "new" ? c.create : c.send}
              loading={busy}
              disabled={!body.trim() || (mode === "new" && !subject.trim())}
              onPress={() => void send()}
            />
          </>
        )}
      </View>
    </Screen>
  );
}
const styles = StyleSheet.create({
  stack: { gap: 16, paddingBottom: 24 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  title: {
    color: tokens.colors.ink,
    fontSize: 26,
    fontWeight: "800",
    fontFamily: tokens.typography.fontFamily.bodyPersian,
  },
  subtitle: {
    color: tokens.colors.ink,
    fontSize: 16,
    fontWeight: "700",
    fontFamily: tokens.typography.fontFamily.bodyPersian,
  },
  text: {
    color: tokens.colors.muted,
    fontSize: 14,
    lineHeight: 25,
    fontFamily: tokens.typography.fontFamily.bodyPersian,
  },
  article: { minHeight: 44, justifyContent: "center" },
  composer: { minHeight: 140, textAlignVertical: "top" },
  admin: { borderColor: tokens.colors.aqua },
});
