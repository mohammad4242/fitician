import type { ReviewProfileSummary } from "@fitician/core/workout-reviews";
import {
  formatIsoDate,
  formatPersianDate,
  formatTehranDateTimeForLocale,
} from "@fitician/core";

import { ReviewDisclosure } from "./ReviewDisclosure";
import "./reviewProfileSummary.css";

type NutritionSummary = NonNullable<ReviewProfileSummary["nutrition"]>;
type MedicalSummary = NonNullable<ReviewProfileSummary["medical"]>;

const valueLabels: Record<string, [string, string]> = {
  both: ["هر دو مسیر", "Both paths"],
  build_muscle: ["عضله‌سازی", "Build muscle"],
  body_recomposition: ["بازترکیب بدنی", "Body recomposition"],
  beginner: ["مبتدی", "Beginner"],
  intermediate: ["متوسط", "Intermediate"],
  advanced: ["پیشرفته", "Advanced"],
  gym: ["باشگاه", "Gym"],
  home: ["خانه", "Home"],
  moderate: ["متوسط", "Moderate"],
  female: ["زن", "Female"],
  male: ["مرد", "Male"],
  resistance: ["مقاومتی", "Resistance"],
  favourite: ["محبوب", "Favourite"],
  allergy: ["حساسیت", "Allergy"],
  intolerance: ["عدم تحمل", "Intolerance"],
  controlled_hypertension: ["فشار خون کنترل‌شده", "Controlled hypertension"],
};

const medicalFlagLabels: Record<string, [string, string]> = {
  dangerous_food_reaction_history: ["سابقه واکنش شدید غذایی", "Severe food reaction history"],
  pregnant: ["بارداری", "Pregnancy"],
  breastfeeding: ["شیردهی", "Breastfeeding"],
  eating_disorder_diagnosed: ["تشخیص اختلال خوردن", "Diagnosed eating disorder"],
  eating_disorder_active_symptoms: ["علائم فعال اختلال خوردن", "Active eating-disorder symptoms"],
  emergency_or_danger_symptoms: ["علائم خطر فوری", "Emergency or danger symptoms"],
  complex_medication_food_interaction: ["تداخل پیچیده دارو و غذا", "Complex medication-food interaction"],
};

export function ReviewProfileSummaryCard({
  summary,
  fa,
}: {
  summary: ReviewProfileSummary | null | undefined;
  fa: boolean;
}) {
  if (!summary) return null;
  const l = (persian: string, english: string) => fa ? persian : english;
  const limitations = summary.physical_limitations?.trim();
  const trainingCautions = summary.training_cautions ?? [];

  return (
    <section className="review-profile-summary" aria-labelledby="review-profile-summary-title">
      <header className="review-profile-summary-header">
        <div>
          <small>{l("اطلاعات جاری پرونده", "Current case profile")}</small>
          <h3 id="review-profile-summary-title">{l("خلاصهٔ کاربر", "Member profile summary")}</h3>
        </div>
        <span aria-hidden="true">✦</span>
      </header>
      <div className="review-profile-highlights">
        <Highlight label={l("قد", "Height")} value={summary.height_cm === null ? null : `${formatNumber(summary.height_cm, fa)} ${l("سانتی‌متر", "cm")}`} />
        <Highlight label={l("وزن فعلی", "Current weight")} value={summary.weight_kg === null ? null : `${formatNumber(summary.weight_kg, fa)} ${l("کیلوگرم", "kg")}`} />
        <Highlight label={l("هدف", "Goal")} value={humanize(summary.fitness_goal, fa)} />
        <Highlight label={l("تمرین", "Training")} value={summary.training_days_per_week === null ? null : `${formatNumber(summary.training_days_per_week, fa)} ${l("روز در هفته", "days/week")}`} />
      </div>
      {(limitations || trainingCautions.length > 0) && (
        <div className="review-profile-alert">
          {limitations && <p><strong>{l("محدودیت فعلی", "Current limitation")}</strong>{limitations}</p>}
          {trainingCautions.length > 0 && <p><strong>{l("احتیاط‌های تمرینی", "Training cautions")}</strong>{trainingCautions.map((item) => humanize(item, fa)).join("، ")}</p>}
        </div>
      )}
      <div className="review-profile-details">
        <ReviewDisclosure
          section="profile-body-training"
          summary={l("مشخصات بدنی، هدف و سابقه تمرین", "Body, goals, and training history")}
          title={l("مشخصات بدنی و تمرین", "Body and training")}
        >
          <InfoGrid entries={[
            [l("نام", "Name"), summary.display_name],
            [l("سن", "Age"), summary.age === null ? null : formatNumber(summary.age, fa)],
            [l("تاریخ تولد", "Birth date"), dateLabel(summary.birth_date, fa)],
            [l("جنسیت", "Sex"), humanize(summary.sex, fa)],
            [l("تاریخ اندازه‌گیری", "Measurement date"), dateTimeLabel(summary.measurements_measured_at, fa)],
            [l("دور شانه", "Shoulder circumference"), measurementLabel(summary.shoulder_circumference_cm, fa)],
            [l("دور کمر", "Waist circumference"), measurementLabel(summary.waist_circumference_cm, fa)],
            [l("دور باسن", "Hip circumference"), measurementLabel(summary.hip_circumference_cm, fa)],
            [l("سطح تجربه", "Experience"), humanize(summary.experience_level, fa)],
            [l("سن تمرینی", "Training age"), summary.training_age_months === null ? null : `${formatNumber(summary.training_age_months, fa)} ${l("ماه", "months")}`],
            [l("محل تمرین", "Training location"), humanize(summary.training_location, fa)],
            [l("شدت تمرین", "Training intensity"), humanize(summary.training_intensity, fa)],
            [l("مدت هر جلسه", "Session duration"), summary.session_duration_minutes === null ? null : `${formatNumber(summary.session_duration_minutes, fa)} ${l("دقیقه", "minutes")}`],
            [l("طول برنامه", "Plan duration"), summary.plan_duration_weeks === null ? null : `${formatNumber(summary.plan_duration_weeks, fa)} ${l("هفته", "weeks")}`],
            [l("روزهای ترجیحی", "Preferred weekdays"), summary.preferred_weekdays?.map((item) => String(item + 1)).join("، ")],
            [l("عضلات اولویت‌دار", "Priority muscles"), summary.priority_muscles?.map((item) => humanize(item, fa)).join("، ")],
            [l("تجهیزات", "Equipment"), summary.available_equipment?.map((item) => humanize(item, fa)).join("، ")],
            [l("روش ساخت برنامه", "Plan generation method"), humanize(summary.workout_generation_method, fa)],
          ]} />
        </ReviewDisclosure>
        {summary.nutrition && (
          <ReviewDisclosure
            section="profile-nutrition"
            summary={l("الگوی غذایی، غذاهای ترجیحی و آشپزی", "Diet pattern, food preferences, and cooking")}
            title={l("تغذیه و ترجیحات غذایی", "Nutrition and food preferences")}
          >
            <NutritionSection nutrition={summary.nutrition} fa={fa} l={l} />
          </ReviewDisclosure>
        )}
        {summary.medical && (
          <ReviewDisclosure
            section="profile-medical"
            summary={l("شرایط، داروها و هشدارهای ایمنی", "Conditions, medications, and safety flags")}
            title={l("اطلاعات پزشکی و ایمنی", "Medical and safety information")}
          >
            <MedicalSection medical={summary.medical} fa={fa} l={l} />
          </ReviewDisclosure>
        )}
      </div>
    </section>
  );
}

function NutritionSection({
  nutrition,
  fa,
  l,
}: {
  nutrition: NutritionSummary;
  fa: boolean;
  l: (persian: string, english: string) => string;
}) {
  return (
    <section>
      <InfoGrid entries={[
        [l("وضعیت تکمیل", "Onboarding status"), humanize(nutrition.onboarding_status, fa)],
        [l("فعالیت روزانه", "Daily activity"), humanize(nutrition.daily_activity_level, fa)],
        [l("بودجه ماهانه", "Monthly food budget"), nutrition.individual_monthly_food_budget_irr === undefined ? null : `${formatNumber(nutrition.individual_monthly_food_budget_irr, fa)} ${l("ریال", "IRR")}`],
        [l("سبک برنامه", "Plan style"), humanize(nutrition.plan_style, fa)],
        [l("تعداد وعده", "Meals"), formatNumber(nutrition.meals_per_day, fa)],
        [l("تعداد میان‌وعده", "Snacks"), formatNumber(nutrition.snacks_per_day, fa)],
        [l("مهارت آشپزی", "Cooking skill"), humanize(nutrition.cooking_skill, fa)],
        [l("زمان آشپزی", "Cooking time"), `${formatNumber(nutrition.maximum_cooking_time_minutes, fa)} ${l("دقیقه", "minutes")}`],
        [l("الگوی غذایی", "Dietary pattern"), humanize(nutrition.dietary_pattern, fa)],
        [l("تنوع مطلوب", "Preferred variety"), humanize(nutrition.preferred_variety, fa)],
        [l("غذای تأمین‌شده در هفته", "Supplied meals/week"), formatNumber(nutrition.supplied_meals_per_week, fa)],
        [l("تغییر هدف وزن", "Target weight change"), nutrition.target_weight_change_kg_per_week ? `${formatNumber(nutrition.target_weight_change_kg_per_week, fa)} ${l("کیلو در هفته", "kg/week")}` : null],
        [l("زمینه شیفت کاری", "Work shift"), nutrition.work_shift_context],
      ]} />
      {(nutrition.food_items ?? []).length > 0 && (
        <ul className="review-profile-list">
          {(nutrition.food_items ?? []).map((item) => <li key={`${item.kind}-${item.name}`}><strong>{humanize(item.kind, fa)}</strong><span>{item.name}{item.details ? ` · ${item.details}` : ""}</span></li>)}
        </ul>
      )}
      {nutrition.structured_exercise && <InfoGrid entries={[
        [l("تمرین ساختاریافته", "Structured exercise"), nutrition.structured_exercise.trains ? l("دارد", "Yes") : l("ندارد", "No")],
        [l("نوع تمرین", "Exercise type"), humanize(nutrition.structured_exercise.exercise_type, fa)],
        [l("روزهای تمرین", "Exercise days"), nutrition.structured_exercise.days_per_week === null ? null : formatNumber(nutrition.structured_exercise.days_per_week, fa)],
        [l("دقیقه هر جلسه", "Minutes/session"), nutrition.structured_exercise.minutes_per_session === null ? null : formatNumber(nutrition.structured_exercise.minutes_per_session, fa)],
      ]} />}
    </section>
  );
}

function MedicalSection({
  medical,
  fa,
  l,
}: {
  medical: MedicalSummary;
  fa: boolean;
  l: (persian: string, english: string) => string;
}) {
  return (
    <section>
      <InfoGrid entries={[
        [l("نتیجه ایمنی", "Safety outcome"), humanize(medical.safety_outcome, fa)],
        [l("محدودیت غذایی پزشک", "Physician dietary restrictions"), medical.physician_dietary_restrictions],
        [l("شرایط مهم دیگر", "Other relevant condition"), medical.other_relevant_condition],
      ]} />
      <ul className="review-profile-list">
        {Object.entries(medical.flags ?? {}).filter(([, active]) => active).map(([key]) => <li key={key}><strong>{l("هشدار", "Flag")}</strong><span>{medicalFlagLabels[key]?.[fa ? 0 : 1] ?? humanize(key, fa)}</span></li>)}
        {(medical.conditions ?? []).map((condition) => <li key={`condition-${condition.code}`}><strong>{l("بیماری", "Condition")}</strong><span>{humanize(condition.code, fa)}{condition.details ? ` · ${condition.details}` : ""}</span></li>)}
        {(medical.medications ?? []).map((medication) => <li key={`medication-${medication.name}`}><strong>{l("دارو", "Medication")}</strong><span>{medication.name}{medication.dosage ? ` · ${medication.dosage}` : ""}{medication.notes ? ` · ${medication.notes}` : ""}</span></li>)}
        {(medical.safety_reason_codes ?? []).map((code) => <li key={`reason-${code}`}><strong>{l("کد ایمنی", "Safety code")}</strong><span>{code}</span></li>)}
      </ul>
    </section>
  );
}

function Highlight({ label, value }: { label: string; value: string | null | undefined }) {
  return <div><span>{label}</span><strong>{value || "—"}</strong></div>;
}

function InfoGrid({ entries }: { entries: ReadonlyArray<readonly [string, string | null | undefined]> }) {
  return <dl className="review-profile-info-grid">{entries.filter(([, value]) => value !== null && value !== undefined && value !== "").map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function humanize(value: string | null | undefined, fa: boolean): string | null {
  if (!value) return null;
  return valueLabels[value]?.[fa ? 0 : 1] ?? value.replaceAll("_", " ");
}

function formatNumber(value: number | string, fa: boolean): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return new Intl.NumberFormat(fa ? "fa-IR" : "en-US", { maximumFractionDigits: 2 }).format(numeric);
}

function measurementLabel(value: string | null, fa: boolean): string | null {
  return value === null ? null : `${formatNumber(value, fa)} ${fa ? "سانتی‌متر" : "cm"}`;
}

function dateLabel(value: string | null, fa: boolean): string | null {
  if (!value) return null;
  return fa ? formatPersianDate(value) : formatIsoDate(value, "en-US");
}

function dateTimeLabel(value: string | null, fa: boolean): string | null {
  if (!value) return null;
  return formatTehranDateTimeForLocale(value, fa ? "fa-IR" : "en-US");
}
