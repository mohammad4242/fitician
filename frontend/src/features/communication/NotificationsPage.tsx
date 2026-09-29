import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { resolvedIanaTimeZone, type NotificationInbox, type PersonalNotificationSettings } from "@fitician/core";
import { useAuthIdentity } from "../auth/AuthContext";
import { communicationApi as api } from "./api";
export function NotificationsPage() {
  const identity = useAuthIdentity();
  const [inbox, setInbox] = useState<NotificationInbox | null>(null);
  const [settings, setSettings] = useState<PersonalNotificationSettings | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
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
      if (document.visibilityState !== "hidden") void api.inbox().then(page => {
        if (epoch.current === current) setInbox(previous => previous ? { ...page, older_cursor: previous.older_cursor, items: [...page.items, ...previous.items.filter(item => !page.items.some(next => next.id === item.id))] } : page);
      }).catch(() => undefined);
    }, 15000);
    return () => { epoch.current = current + 1; clearInterval(timer); };
  }, [identity, attempt]);
  async function save() {
    if (!settings || busy) return;
    const current = epoch.current;
    setBusy(true); setError(""); setSaved(false);
    const { updated_at: _updatedAt, ...input } = settings;
    try {
      const savedSettings = await api.savePreferences({ ...input, reminder_timezone: input.reminder_timezone || resolvedIanaTimeZone() });
      if (epoch.current === current) { setSettings(savedSettings); setSaved(true); }
    } catch { if (epoch.current === current) setError("ذخیره تنظیمات ناموفق بود؛ ساعت را به صورت HH:mm و منطقه زمانی معتبر وارد کن."); }
    finally { if (epoch.current === current) setBusy(false); }
  }
  async function read(id: string) {
    const current = epoch.current;
    try { await api.readNotification(id); if (epoch.current === current) setInbox(previous => previous ? { ...previous, unread_count: Math.max(0, previous.unread_count - (previous.items.find(i => i.id === id)?.read_at ? 0 : 1)), items: previous.items.map(i => i.id === id ? { ...i, read_at: new Date().toISOString() } : i) } : previous); }
    catch { if (epoch.current === current) setError("ثبت خواندن اعلان ناموفق بود."); }
  }
  async function older() {
    if (!inbox?.older_cursor) return;
    const current = epoch.current;
    try { const page = await api.inbox(inbox.older_cursor); if (epoch.current === current) setInbox(previous => previous ? { ...page, items: [...previous.items, ...page.items.filter(i => !previous.items.some(p => p.id === i.id))] } : page); }
    catch { if (epoch.current === current) setError("دریافت اعلان‌های قبلی ناموفق بود."); }
  }
  return <main className="nutrition-page"><h1>اعلان‌ها و یادآوری‌ها {inbox?.unread_count ? `(${inbox.unread_count})` : ""}</h1>
    {error && <p role="alert">{error} <button type="button" onClick={() => setAttempt(value => value + 1)}>تلاش دوباره</button></p>}
    {!inbox && !error && <p>در حال دریافت…</p>}
    {inbox?.items.length === 0 && <p>اعلانی وجود ندارد.</p>}
    <ul>{inbox?.items.map(item => {
      const data = item.payload.data as Record<string, unknown> | undefined;
      const destination = item.event_type === "program_message" && (data?.kind === "workout" || data?.kind === "nutrition") && typeof data.review_id === "string" ? `/conversation/${data.kind}/${encodeURIComponent(data.review_id)}` : item.event_type === "training_reminder" ? "/workout-plan" : item.event_type === "nutrition_reminder" ? "/nutrition-estimate" : "/dashboard";
      return <li key={item.id}><strong>{String(item.payload.title ?? "اعلان")}{!item.read_at ? " · خوانده‌نشده" : ""}</strong><p>{String(item.payload.body ?? "")}</p><Link to={destination} onClick={() => void read(item.id)}>مشاهده</Link>{!item.read_at && <button type="button" onClick={() => void read(item.id)}>خواندم</button>}</li>;
    })}</ul>
    {inbox?.older_cursor && <button type="button" onClick={() => void older()}>اعلان‌های قبلی</button>}
    {settings && <section><h2>تنظیمات یادآوری</h2>
      {([["enabled", "اعلان‌ها فعال باشند"], ["messages", "اعلان پیام متخصص"], ["training_reminders", "یادآوری روزهای تمرین"], ["nutrition_reminders", "یادآوری روزانه تغذیه"], ["return_reminders", "یادآوری بازگشت پس از هفت روز وقفه؛ حداکثر هفته‌ای یک‌بار"]] as const).map(([field, label]) => <label key={field}><input type="checkbox" checked={Boolean(settings[field])} onChange={event => { setSaved(false); setSettings({ ...settings, [field]: event.target.checked }); }} />{label}</label>)}
      <label>ساعت تمرین<input aria-label="ساعت تمرین" type="time" value={settings.training_time ?? "09:00"} onChange={event => setSettings({ ...settings, training_time: event.target.value || null })} /></label>
      <label>ساعت تغذیه<input aria-label="ساعت تغذیه" type="time" value={settings.nutrition_time ?? "09:00"} onChange={event => setSettings({ ...settings, nutrition_time: event.target.value || null })} /></label>
      <label>منطقه زمانی<input aria-label="منطقه زمانی" value={settings.reminder_timezone ?? resolvedIanaTimeZone()} onChange={event => setSettings({ ...settings, reminder_timezone: event.target.value })} /></label>
      <button type="button" disabled={busy} onClick={() => void save()}>ذخیره تنظیمات</button>{saved && <p role="status">تنظیمات ذخیره شد.</p>}
      <p>اعلان بیرون اپ در موبایل، با اجازهٔ سیستم‌عامل و ثبت دستگاه، ارسال می‌شود. یادآوری‌های جدید اختیاری هستند.</p>
    </section>}
  </main>;
}
