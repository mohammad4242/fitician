import { createNutritionProgressApi, formatPersianDate, nutritionProgressCopy, type NutritionProgressReview as Review } from "@fitician/core";
import { useEffect, useMemo, useRef, useState } from "react";
import { Switch, Text, View } from "react-native";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { Button, Card } from "../ui/components";
import { languageForDirection } from "../ui/rtl";
import { fiticianTokens } from "../ui/tokens";
export function NutritionProgressReview() {
  const auth = useMobileAuth();
  const identity = auth.user?.id;
  const api = useMemo(() => createNutritionProgressApi(auth.request), [auth.request]);
  const queryClient = useQueryClient();
  const router = useRouter();
  const en = languageForDirection() === "en";
  const l = (fa: string, english: string) => en ? english : fa;
  const [review, setReview] = useState<Review | null>(null);
  const [owner, setOwner] = useState<string | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const epoch = useRef(0);
  const pending = useRef(false);
  useEffect(() => {
    const current = ++epoch.current;
    setReview(null); setOwner(null); setAgreed(false); setSaved(false); setBusy(false); setError(""); pending.current = false;
    return () => { epoch.current = current + 1; };
  }, [identity]);
  const visible = owner === identity ? review : null;
  const number = (value: number | null | undefined) => value == null ? l("ثبت نشده", "Not recorded") : value.toLocaleString(en ? "en-US" : "fa-IR", { maximumFractionDigits: 3 });
  async function load() {
    if (!identity || pending.current) return;
    const current = epoch.current;
    pending.current = true; setBusy(true); setError(""); setReview(null); setAgreed(false); setSaved(false);
    try {
      const result = await api.review();
      if (epoch.current === current) { setReview(result); setOwner(identity); }
    } catch { if (epoch.current === current) setError(l("بازبینی دریافت نشد؛ دوباره تلاش کن.", "Could not load review; retry.")); }
    finally { if (epoch.current === current) { pending.current = false; setBusy(false); } }
  }
  async function confirm() {
    if (!visible?.can_confirm || !agreed || pending.current) return;
    const current = epoch.current;
    pending.current = true; setBusy(true); setError("");
    try {
      await api.confirm(visible);
      if (epoch.current === current) {
        setSaved(true); setAgreed(false);
        void queryClient.invalidateQueries({ queryKey: ["nutrition"] });
      }
    } catch { if (epoch.current === current) setError(l("تأیید انجام نشد؛ ممکن است داده‌ها یا برنامه تغییر کرده باشند. بازبینی را به‌روز کن یا دوباره تلاش کن.", "Confirmation failed; the data or plan may have changed. Refresh the review or retry.")); }
    finally { if (epoch.current === current) { pending.current = false; setBusy(false); } }
  }
  if (!identity) return null;
  const textStyle = { color: fiticianTokens.colors.ink };
  return <Card><View style={{ gap: fiticianTokens.spacing[2] }}>
    <Text accessibilityRole="header" style={textStyle}>{l("آیا برنامه نیاز به اصلاح دارد؟", "Does your plan need an adjustment?")}</Text>
    <Text style={textStyle}>{l("روند وزن و ثبت‌های تغذیه را کنار هم بررسی کن. بازبینی، روزهای کامل‌شده تا دیروز را می‌سنجد؛ دادهٔ کم باعث تغییر هدف نمی‌شود.", "Review weight and nutrition records together. Only completed days through yesterday are assessed; insufficient data does not change targets.")}</Text>
    <Button disabled={busy} label={busy ? l("در حال بررسی…", "Reviewing…") : l("بازبینی روند تغذیه", "Review nutrition progress")} onPress={() => void load()} />
    {error && <Text accessibilityRole="alert" style={{ color: fiticianTokens.colors.danger }}>{error}</Text>}
    {visible && <>
      <Text style={textStyle}>{en ? `${visible.start} – ${visible.end}` : `${formatPersianDate(visible.start)} تا ${formatPersianDate(visible.end)}`}</Text>
      <Text style={textStyle}>{nutritionProgressCopy(visible.status, en)}</Text>
      <Text style={textStyle}>{l("روزهای ثبت وضعیت / ثبت غذا / ثبت قابل اتکا", "Checked-in / food-logged / reliable days")}: {number(visible.checked_in_days)} / {number(visible.logged_days)} / {number(visible.reliable_logged_days)}</Text>
      <Text style={textStyle}>{l("رعایت گزارش‌شدهٔ برنامه", "Reported adherence")}: {visible.adherence_percent == null ? l("ثبت نشده", "Not recorded") : `${number(visible.adherence_percent)}%`}</Text>
      <Text style={textStyle}>{l("میانگین کالری روزهای دارای ثبت", "Average calories on logged days")}: {number(visible.average_logged_kcal)}</Text>
      <Text style={textStyle}>{l("روزهای اندازه‌گیری وزن", "Weighing days")}: {number(visible.weighing_days)}</Text>
      <Text style={textStyle}>{l("روند مشاهده‌شدهٔ وزن، کیلوگرم در هفته", "Observed weight trend, kg/week")}: {number(visible.observed_kg_per_week)}</Text>
      {visible.target_kg_per_week != null && <Text style={textStyle}>{l("نرخ هدف محاسبه‌شده، کیلوگرم در هفته", "Calculated target rate, kg/week")}: {number(visible.target_kg_per_week)}</Text>}
      <Text style={textStyle}>{l("روند وزن، تغییر چربی یا عضله را ثابت نمی‌کند؛ علامت منفی یعنی کاهش وزن و مثبت یعنی افزایش.", "Scale-weight trends do not establish fat or muscle changes; negative means weight loss and positive means gain.")}</Text>
      {visible.can_confirm && !saved && <>
        <Text style={textStyle}>{l("هدف کالری فعلی", "Current calorie target")}: {number(visible.current_calories)} → {l("پیشنهاد جدید", "Proposed target")}: {number(visible.proposed_calories)}</Text>
        <Text style={textStyle}>{l("اصلاح هدف را تأیید می‌کنم؛ برای تغییر وعده‌ها برنامهٔ جدید می‌گیرم.", "I confirm the target adjustment and will request a new plan to update meals.")}</Text>
        <Text style={textStyle}>{l("نرخ درخواستی جدید برای تغییر وزن", "New requested weight-change rate")}: {visible.proposed_rate_kg_per_week == null ? l("پیش‌فرض ایمن موتور", "Engine safe default") : `${number(visible.proposed_rate_kg_per_week)} ${l("کیلوگرم در هفته", "kg/week")}`}</Text>
        <Switch accessibilityLabel={l("تأیید تغییر هدف", "Agree to target adjustment")} disabled={busy} value={agreed} onValueChange={setAgreed} />
        <Button disabled={busy || !agreed} label={l("تأیید اصلاح هدف", "Confirm target adjustment")} onPress={() => void confirm()} />
      </>}
      {saved && <><Text accessibilityRole="alert" style={textStyle}>{l("هدف به‌روز شد. وعده‌های برنامهٔ فعلی تغییر نکرده‌اند؛ برای اعمال هدف جدید، برنامهٔ جدید بگیر و شروع آن را تأیید کن.", "Targets updated. Current meals are unchanged; request a new plan and confirm its start to apply the new targets.")}</Text><Button label={l("دریافت برنامه با هدف جدید", "Get a plan with updated targets")} onPress={() => router.push("/member/nutrition")} /></>}
      {(visible.status === "specialist_review" || visible.status === "new_plan_required") && <Button variant="secondary" label={l("پیگیری از بخش برنامه و نظارت پزشک", "Open program and doctor supervision")} onPress={() => router.push("/member/nutrition")} />}
    </>}
  </View></Card>;
}
