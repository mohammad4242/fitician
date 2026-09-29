import { registerNotifications } from "../notifications/notificationRegistration";
import { prepareNotifications, getNativePushToken } from "../notifications/notificationPermission";
import { createNotificationApi } from "../notifications/notificationApi";
import { createCommunicationApi, resolvedIanaTimeZone, type NotificationInbox, type PersonalNotificationSettings } from "@fitician/core";
import { useEffect, useMemo, useRef, useState } from "react";
import { AppState, Linking, Switch, Text, View } from "react-native";
import { useRouter, type Href } from "expo-router";
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { Button, Card, PageHeading, TextField } from "../ui/components";
import { Screen } from "../ui/layout";
import { fiticianTokens } from "../ui/tokens";
export function NotificationsScreen() {
  const auth = useMobileAuth();
  const identity = auth.user?.id;
  const router = useRouter();
  const api = useMemo(() => createCommunicationApi(auth.request), [auth.request]);
  const [inbox, setInbox] = useState<NotificationInbox | null>(null);
  const [settings, setSettings] = useState<PersonalNotificationSettings | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [registration, setRegistration] = useState("");
  const [attempt, setAttempt] = useState(0);
  const epoch = useRef(0);
  useEffect(() => {
    const current = ++epoch.current;
    setInbox(null); setSettings(null); setError(""); setBusy(false); setSaved(false);
    if (!identity) return;
    void Promise.all([api.inbox(), api.preferences()]).then(([items, preferences]) => {
      if (epoch.current === current) { setInbox(items); setSettings(preferences); }
    }).catch(() => { if (epoch.current === current) setError("دریافت اعلان‌ها ناموفق بود."); });
    const timer = setInterval(() => {
      if (AppState.currentState === "active") void api.inbox().then(page => {
        if (epoch.current === current) setInbox(previous => previous ? { ...page, older_cursor: previous.older_cursor, items: [...page.items, ...previous.items.filter(item => !page.items.some(next => next.id === item.id))] } : page);
      }).catch(() => undefined);
    }, 15000);
    return () => { epoch.current = current + 1; clearInterval(timer); };
  }, [api, identity, attempt]);
  async function enableDevice() {
    const current = epoch.current;
    setRegistration("در حال بررسی مجوز…");
    try {
      const result = await registerNotifications({ prepare: prepareNotifications, getToken: getNativePushToken, register: async token => { await createNotificationApi(auth.request).registerCurrentDevice(token.token, token.provider); } });
      if (epoch.current === current) setRegistration(result === "registered" ? "دستگاه برای دریافت اعلان ثبت شد." : result === "permission_denied" ? "مجوز اعلان داده نشده؛ تنظیمات گوشی را بررسی کن." : "شناسه اعلان دستگاه دریافت نشد.");
    } catch { if (epoch.current === current) setRegistration("فعال‌سازی اعلان گوشی ناموفق بود."); }
  }
  async function save() {
    if (!settings || busy) return;
    const current = epoch.current;
    setBusy(true); setError(""); setSaved(false);
    const { updated_at: _updatedAt, ...input } = settings;
    try {
      const result = await api.savePreferences({ ...input, reminder_timezone: input.reminder_timezone || resolvedIanaTimeZone() });
      if (epoch.current === current) { setSettings(result); setSaved(true); }
    } catch { if (epoch.current === current) setError("ذخیره تنظیمات ناموفق بود؛ ساعت HH:mm و منطقه زمانی معتبر وارد کن."); }
    finally { if (epoch.current === current) setBusy(false); }
  }
  async function read(id: string) {
    const current = epoch.current;
    try {
      await api.readNotification(id);
      if (epoch.current === current) setInbox(previous => previous ? { ...previous, unread_count: Math.max(0, previous.unread_count - (previous.items.find(i => i.id === id)?.read_at ? 0 : 1)), items: previous.items.map(i => i.id === id ? { ...i, read_at: new Date().toISOString() } : i) } : previous);
    } catch { if (epoch.current === current) setError("ثبت خواندن اعلان ناموفق بود."); }
  }
  async function older() {
    if (!inbox?.older_cursor) return;
    const current = epoch.current;
    try { const page = await api.inbox(inbox.older_cursor); if (epoch.current === current) setInbox(previous => previous ? { ...page, items: [...previous.items, ...page.items.filter(i => !previous.items.some(p => p.id === i.id))] } : page); }
    catch { if (epoch.current === current) setError("دریافت اعلان‌های قبلی ناموفق بود."); }
  }
  return <Screen><PageHeading title={`اعلان‌ها و یادآوری‌ها${inbox?.unread_count ? ` (${inbox.unread_count})` : ""}`} />
    {error && <><Text accessibilityRole="alert" style={{ color: fiticianTokens.colors.danger }}>{error}</Text><Button label="تلاش دوباره" onPress={() => setAttempt(value => value + 1)} /></>}
    {!inbox && !error && <Text>در حال دریافت…</Text>}
    {inbox?.items.length === 0 && <Text>اعلانی وجود ندارد.</Text>}
    {inbox?.items.map(item => {
      const data = item.payload.data as Record<string, unknown> | undefined;
      const destination = item.event_type === "program_message" && (data?.kind === "workout" || data?.kind === "nutrition") && typeof data.review_id === "string" ? `/conversation?kind=${data.kind}&reviewId=${encodeURIComponent(data.review_id)}` : item.event_type === "training_reminder" ? "/member/workouts" : item.event_type === "nutrition_reminder" ? "/member/nutrition" : "/member";
      return <Card key={item.id}><Text style={{ color: fiticianTokens.colors.ink }}>{String(item.payload.title ?? "اعلان")}{!item.read_at ? " · خوانده‌نشده" : ""}</Text><Text style={{ color: fiticianTokens.colors.ink }}>{String(item.payload.body ?? "")}</Text><Button label="مشاهده" onPress={() => { void read(item.id); router.push(destination as Href); }} />{!item.read_at && <Button variant="ghost" label="خواندم" onPress={() => void read(item.id)} />}</Card>;
    })}
    {inbox?.older_cursor && <Button label="اعلان‌های قبلی" onPress={() => void older()} />}
    <Button label="فعال‌سازی اعلان گوشی" onPress={() => void enableDevice()} />
    {registration && <Text style={{ color: fiticianTokens.colors.ink }}>{registration}</Text>}
    <Button label="تنظیمات اعلان گوشی" variant="ghost" onPress={() => { void Linking.openSettings().catch(() => setError("باز کردن تنظیمات گوشی ناموفق بود.")); }} />
    {settings && <Card><View style={{ gap: fiticianTokens.spacing[2] }}><Text style={{ color: fiticianTokens.colors.ink }}>تنظیمات یادآوری</Text>
      {([["enabled", "اعلان‌ها فعال باشند"], ["messages", "اعلان پیام متخصص"], ["training_reminders", "یادآوری روزهای تمرین"], ["nutrition_reminders", "یادآوری روزانه تغذیه"], ["return_reminders", "بازگشت پس از هفت روز وقفه؛ حداکثر هفته‌ای یک‌بار"]] as const).map(([field, label]) => <View key={field}><Text style={{ color: fiticianTokens.colors.ink }}>{label}</Text><Switch accessibilityLabel={label} value={Boolean(settings[field])} onValueChange={value => { setSaved(false); setSettings({ ...settings, [field]: value }); }} /></View>)}
      <TextField label="ساعت تمرین" accessibilityLabel="ساعت تمرین" value={settings.training_time ?? "09:00"} onChangeText={value => setSettings({ ...settings, training_time: value || null })} textDirection="ltr" />
      <TextField label="ساعت تغذیه" accessibilityLabel="ساعت تغذیه" value={settings.nutrition_time ?? "09:00"} onChangeText={value => setSettings({ ...settings, nutrition_time: value || null })} textDirection="ltr" />
      <TextField label="منطقه زمانی" accessibilityLabel="منطقه زمانی" value={settings.reminder_timezone ?? resolvedIanaTimeZone()} onChangeText={value => setSettings({ ...settings, reminder_timezone: value })} textDirection="ltr" />
      <Button disabled={busy} label="ذخیره تنظیمات" onPress={() => void save()} />{saved && <Text accessibilityRole="alert">تنظیمات ذخیره شد.</Text>}
      <Text style={{ color: fiticianTokens.colors.ink }}>اعلان بیرون اپ با اجازهٔ سیستم‌عامل و ثبت دستگاه ارسال می‌شود. یادآوری‌های جدید اختیاری هستند.</Text>
    </View></Card>}
  </Screen>;
}
