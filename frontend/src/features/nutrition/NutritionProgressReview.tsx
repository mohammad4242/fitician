import { createNutritionProgressApi, formatPersianDate, nutritionProgressCopy, type NutritionProgressReview as Review, type NutritionProgressRequest } from "@fitician/core";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useAuthIdentity } from "../auth/AuthContext";
import { request } from "../../shared/apiClient";
const transport: NutritionProgressRequest = input => request(input.path, { method: input.method, body: input.body === undefined ? undefined : JSON.stringify(input.body) });
const api = createNutritionProgressApi(transport);
export function NutritionProgressReview() {
  const identity = useAuthIdentity();
  const en = useTranslation().i18n.resolvedLanguage === "en";
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
    setReview(null); setOwner(null); setAgreed(false); setSaved(false); setError(""); setBusy(false); pending.current = false;
    return () => { epoch.current = current + 1; };
  }, [identity]);
  const visible = owner === identity ? review : null;
  const number = (value: number | null | undefined) => value == null ? l("ثبت نشده", "Not recorded") : value.toLocaleString(en ? "en-US" : "fa-IR", { maximumFractionDigits: 3 });
  async function load() {
    if (!identity || pending.current) return;
    const current = epoch.current;
    pending.current = true; setBusy(true); setError(""); setAgreed(false); setReview(null); setSaved(false);
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
      if (epoch.current === current) { setSaved(true); setAgreed(false); }
    } catch { if (epoch.current === current) setError(l("تأیید انجام نشد؛ ممکن است داده‌ها یا برنامه تغییر کرده باشند. بازبینی را به‌روز کن یا دوباره تلاش کن.", "Confirmation failed; the data or plan may have changed. Refresh the review or retry.")); }
    finally { if (epoch.current === current) { pending.current = false; setBusy(false); } }
  }
  if (!identity) return null;
  return <section className="nutrition-checkin" aria-label={l("بازبینی نتیجهٔ تغذیه", "Nutrition progress review")}>
    <h3>{l("آیا برنامه نیاز به اصلاح دارد؟", "Does your plan need an adjustment?")}</h3>
    <p>{l("روند وزن و ثبت‌های تغذیه را کنار هم بررسی کن. بازبینی، روزهای کامل‌شده تا دیروز را می‌سنجد؛ دادهٔ کم باعث تغییر هدف نمی‌شود.", "Review weight and nutrition records together. Only completed days through yesterday are assessed; insufficient data does not change targets.")}</p>
    <button type="button" disabled={busy} onClick={() => void load()}>{busy ? l("در حال بررسی…", "Reviewing…") : l("بازبینی روند تغذیه", "Review nutrition progress")}</button>
    {error && <p role="alert">{error}</p>}
    {visible && <>
      <p>{en ? `${visible.start} – ${visible.end}` : `${formatPersianDate(visible.start)} تا ${formatPersianDate(visible.end)}`}</p>
      <p role="status">{nutritionProgressCopy(visible.status, en)}</p>
      <dl><dt>{l("روزهای ثبت وضعیت / ثبت غذا / ثبت قابل اتکا", "Checked-in / food-logged / reliable days")}</dt><dd>{number(visible.checked_in_days)} / {number(visible.logged_days)} / {number(visible.reliable_logged_days)}</dd>
        <dt>{l("رعایت گزارش‌شدهٔ برنامه", "Reported adherence")}</dt><dd>{visible.adherence_percent == null ? l("ثبت نشده", "Not recorded") : `${number(visible.adherence_percent)}%`}</dd>
        <dt>{l("میانگین کالری روزهای دارای ثبت", "Average calories on logged days")}</dt><dd>{number(visible.average_logged_kcal)}</dd>
        <dt>{l("روزهای اندازه‌گیری وزن", "Weighing days")}</dt><dd>{number(visible.weighing_days)}</dd>
        <dt>{l("روند مشاهده‌شدهٔ وزن، کیلوگرم در هفته", "Observed weight trend, kg/week")}</dt><dd>{number(visible.observed_kg_per_week)}</dd>
        {visible.target_kg_per_week != null && <><dt>{l("نرخ هدف محاسبه‌شده، کیلوگرم در هفته", "Calculated target rate, kg/week")}</dt><dd>{number(visible.target_kg_per_week)}</dd></>}
      </dl>
      <p>{l("روند وزن، تغییر چربی یا عضله را ثابت نمی‌کند؛ علامت منفی یعنی کاهش وزن و مثبت یعنی افزایش.", "Scale-weight trends do not establish fat or muscle changes; negative means weight loss and positive means gain.")}</p>
      {visible.can_confirm && !saved && <>
        <p>{l("هدف کالری فعلی", "Current calorie target")}: {number(visible.current_calories)} → {l("پیشنهاد جدید", "Proposed target")}: {number(visible.proposed_calories)}</p>
        <p>{l("نرخ درخواستی جدید برای تغییر وزن", "New requested weight-change rate")}: {visible.proposed_rate_kg_per_week == null ? l("پیش‌فرض ایمن موتور", "Engine safe default") : `${number(visible.proposed_rate_kg_per_week)} ${l("کیلوگرم در هفته", "kg/week")}`}</p>
        <label><input type="checkbox" checked={agreed} disabled={busy} onChange={event => setAgreed(event.target.checked)} />{l("اصلاح هدف را تأیید می‌کنم؛ برای تغییر وعده‌ها برنامهٔ جدید می‌گیرم.", "I confirm the target adjustment and will request a new plan to update meals.")}</label>
        <button type="button" disabled={busy || !agreed} onClick={() => void confirm()}>{l("تأیید اصلاح هدف", "Confirm target adjustment")}</button>
      </>}
      {saved && <><p role="status">{l("هدف به‌روز شد. وعده‌های برنامهٔ فعلی تغییر نکرده‌اند؛ برای اعمال هدف جدید، برنامهٔ جدید بگیر و شروع آن را تأیید کن.", "Targets updated. Current meals are unchanged; request a new plan and confirm its start to apply the new targets.")}</p><Link to="/nutrition-estimate">{l("دریافت برنامه با هدف جدید", "Get a plan with updated targets")}</Link></>}
      {(visible.status === "specialist_review" || visible.status === "new_plan_required") && <Link to="/nutrition-estimate">{l("پیگیری از بخش برنامه و نظارت پزشک", "Open program and doctor supervision")}</Link>}
    </>}
  </section>;
}
