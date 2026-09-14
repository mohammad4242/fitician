import {
  formatPersianDate,
  formatTehranDateTime,
  reviewDisclosureDefaultExpanded,
  reviewDisclosureKeys,
  type components,
} from "@fitician/core";
import { StyleSheet, Text, View } from "react-native";

import { Card, DisclosureCard, MetricStrip } from "./components";
import { formatPersianNumber } from "./locale";
import { RTL_LAYOUT, RTL_TEXT } from "./rtl";
import { fiticianTokens } from "./tokens";

type ReviewProfileSummary = components["schemas"]["ReviewProfileSummary"];
type ReviewProfileNutrition = NonNullable<ReviewProfileSummary["nutrition"]>;
type ReviewProfileMedical = NonNullable<ReviewProfileSummary["medical"]>;

const valueLabels: Record<string, string> = {
  advanced: "پیشرفته",
  allergy: "حساسیت",
  both: "هر دو مسیر",
  build_muscle: "عضله‌سازی",
  controlled_hypertension: "فشار خون کنترل‌شده",
  female: "زن",
  favourite: "محبوب",
  gym: "باشگاه",
  home: "خانه",
  intermediate: "متوسط",
  intolerance: "عدم تحمل",
  male: "مرد",
  moderate: "متوسط",
  resistance: "مقاومتی",
};

const medicalFlagLabels: Record<string, string> = {
  breastfeeding: "شیردهی",
  complex_medication_food_interaction: "تداخل پیچیده دارو و غذا",
  dangerous_food_reaction_history: "سابقه واکنش شدید غذایی",
  eating_disorder_active_symptoms: "علائم فعال اختلال خوردن",
  eating_disorder_diagnosed: "تشخیص اختلال خوردن",
  emergency_or_danger_symptoms: "علائم خطر فوری",
  pregnant: "بارداری",
};

export function ReviewProfileSummaryCard({
  summary,
}: {
  readonly summary: ReviewProfileSummary | null | undefined;
}) {
  if (summary === null || summary === undefined) return null;
  const cautions = summary.training_cautions ?? [];
  const limitation = summary.physical_limitations?.trim();

  return (
    <View style={styles.container}>
      <Card style={styles.highlightCard} variant="hero">
        <View style={[styles.header, RTL_LAYOUT]}>
          <View style={styles.headerCopy}>
            <Text style={styles.eyebrow}>اطلاعات جاری پرونده</Text>
            <Text accessibilityRole="header" style={styles.title}>خلاصهٔ کاربر</Text>
          </View>
          <Text style={styles.star} accessibilityElementsHidden>✦</Text>
        </View>
        <MetricStrip
          items={[
            { label: "قد", value: measurement(summary.height_cm, "سانتی‌متر") },
            { label: "وزن فعلی", value: measurement(summary.weight_kg, "کیلوگرم") },
            { label: "هدف", value: humanize(summary.fitness_goal) },
            { label: "تمرین", value: summary.training_days_per_week === null ? "ثبت نشده" : `${number(summary.training_days_per_week)} روز` },
          ]}
        />
        {limitation || cautions.length > 0 ? (
          <View style={styles.alert}>
            {limitation ? <Text style={styles.alertText}><Text style={styles.alertLabel}>محدودیت فعلی: </Text>{limitation}</Text> : null}
            {cautions.length > 0 ? <Text style={styles.alertText}><Text style={styles.alertLabel}>احتیاط‌های تمرینی: </Text>{cautions.map(humanize).join("، ")}</Text> : null}
          </View>
        ) : null}
      </Card>

      <DisclosureCard
        defaultExpanded={reviewDisclosureDefaultExpanded(reviewDisclosureKeys.profileBodyTraining)}
        icon="profile"
        summary="مشخصات، هدف و سابقه تمرین"
        title="مشخصات بدنی و تمرین"
      >
        <View style={styles.section}>
          <SummaryGrid entries={[
            ["نام", summary.display_name],
            ["سن", summary.age === null ? null : number(summary.age)],
            ["تاریخ تولد", date(summary.birth_date)],
            ["جنسیت", humanize(summary.sex)],
            ["حالت محصول", humanize(summary.product_mode)],
            ["منطقه زمانی", summary.timezone],
            ["قد", measurement(summary.height_cm, "سانتی‌متر")],
            ["وزن فعلی", measurement(summary.weight_kg, "کیلوگرم")],
            ["تاریخ وزن", dateTime(summary.weight_measured_at)],
            ["دور شانه", measurement(summary.shoulder_circumference_cm, "سانتی‌متر")],
            ["دور کمر", measurement(summary.waist_circumference_cm, "سانتی‌متر")],
            ["دور باسن", measurement(summary.hip_circumference_cm, "سانتی‌متر")],
            ["تاریخ اندازه‌گیری", dateTime(summary.measurements_measured_at)],
            ["هدف تناسب اندام", humanize(summary.fitness_goal)],
            ["سطح تجربه", humanize(summary.experience_level)],
            ["سن تمرینی", summary.training_age_months === null ? null : `${number(summary.training_age_months)} ماه`],
            ["روزهای ترجیحی", weekdays(summary.preferred_weekdays)],
            ["عضلات اولویت‌دار", list(summary.priority_muscles)],
            ["روزهای تمرین در هفته", summary.training_days_per_week === null ? null : number(summary.training_days_per_week)],
            ["محل تمرین", humanize(summary.training_location)],
            ["تجهیزات خانه", summary.home_training_setup],
            ["تجهیزات در دسترس", list(summary.available_equipment)],
            ["مدت هر جلسه", summary.session_duration_minutes === null ? null : `${number(summary.session_duration_minutes)} دقیقه`],
            ["شدت تمرین", humanize(summary.training_intensity)],
            ["مدت برنامه", summary.plan_duration_weeks === null ? null : `${number(summary.plan_duration_weeks)} هفته`],
            ["روش ساخت برنامه", humanize(summary.workout_generation_method)],
            ["زمان ثبت پروفایل", dateTime(summary.profile_created_at)],
            ["آخرین به‌روزرسانی پروفایل", dateTime(summary.profile_updated_at)],
          ]} />
          {limitation ? <Text style={styles.bodyText}>محدودیت‌های جسمی: {limitation}</Text> : null}
          {cautions.length > 0 ? <Text style={styles.bodyText}>احتیاط‌های تمرینی: {cautions.map(humanize).join("، ")}</Text> : null}
        </View>
      </DisclosureCard>
      {summary.nutrition ? (
        <DisclosureCard
          defaultExpanded={reviewDisclosureDefaultExpanded(reviewDisclosureKeys.profileNutrition)}
          icon="nutrition"
          summary="الگوی غذایی، غذاهای ترجیحی و آشپزی"
          title="تغذیه و ترجیحات غذایی"
        >
          <NutritionSection nutrition={summary.nutrition} />
        </DisclosureCard>
      ) : null}
      {summary.medical ? (
        <DisclosureCard
          defaultExpanded={reviewDisclosureDefaultExpanded(reviewDisclosureKeys.profileMedical)}
          icon="shield"
          summary="شرایط، داروها و هشدارهای ایمنی"
          title="اطلاعات پزشکی و ایمنی"
        >
          <MedicalSection medical={summary.medical} />
        </DisclosureCard>
      ) : null}
    </View>
  );
}

function NutritionSection({ nutrition }: { readonly nutrition: ReviewProfileNutrition }) {
  return (
    <View style={styles.section}>
      <SummaryGrid entries={[
        ["وضعیت تکمیل", humanize(nutrition.onboarding_status)],
        ["فعالیت روزانه", humanize(nutrition.daily_activity_level)],
        ["مبنای متابولیک", humanize(nutrition.metabolic_basis)],
        ["بودجه ماهانه", `${number(nutrition.individual_monthly_food_budget_irr)} ریال`],
        ["سبک بودجه", humanize(nutrition.budget_style)],
        ["وعده‌ها در روز", number(nutrition.meals_per_day)],
        ["میان‌وعده‌ها در روز", number(nutrition.snacks_per_day)],
        ["شروع ترجیحی برنامه", humanize(nutrition.preferred_plan_start_day)],
        ["سبک برنامه", humanize(nutrition.plan_style)],
        ["مهارت آشپزی", humanize(nutrition.cooking_skill)],
        ["حداکثر زمان آشپزی", `${number(nutrition.maximum_cooking_time_minutes)} دقیقه`],
        ["دفعات آشپزی در هفته", number(nutrition.cooking_frequency_per_week)],
        ["روش آماده‌سازی", humanize(nutrition.meal_preparation_preference)],
        ["یخچال", yesNo(nutrition.refrigerator_access)],
        ["فریزر", yesNo(nutrition.freezer_access)],
        ["وعده تأمین‌شده در هفته", number(nutrition.supplied_meals_per_week)],
        ["منبع وعده تأمین‌شده", nutrition.supplied_meal_source],
        ["الگوی غذایی", humanize(nutrition.dietary_pattern)],
        ["تنوع مطلوب", humanize(nutrition.preferred_variety)],
        ["حداکثر تکرار غذا", `${number(nutrition.maximum_meal_repetition_per_week)} بار در هفته`],
        ["باقی‌مانده غذا", yesNo(nutrition.accepts_leftovers)],
        ["پخت دسته‌ای", yesNo(nutrition.accepts_batch_cooking)],
        ["زمینه شیفت کاری", nutrition.work_shift_context],
        ["یادآوری روزانه", yesNo(nutrition.daily_check_in_enabled)],
        ["زمان یادآوری", nutrition.preferred_check_in_time],
        ["تغییر هدف وزن", nutrition.target_weight_change_kg_per_week === null ? null : `${number(nutrition.target_weight_change_kg_per_week)} کیلو در هفته`],
        ["حالت نرخ وزن", humanize(nutrition.weight_rate_mode)],
        ["تجهیزات آشپزی", list(nutrition.cooking_equipment)],
        ["تاریخ ثبت تغذیه", dateTime(nutrition.created_at)],
        ["آخرین به‌روزرسانی تغذیه", dateTime(nutrition.updated_at)],
      ]} />
      {(nutrition.food_items ?? []).length > 0 ? (
        <View style={styles.listGroup}>
          <Text style={styles.subheading}>غذاهای ثبت‌شده</Text>
          {(nutrition.food_items ?? []).map((item) => (
            <Text key={`${item.kind}-${item.name}`} style={styles.bodyText}>
              {humanize(item.kind)}: {item.name}{item.details ? ` · ${item.details}` : ""}
            </Text>
          ))}
        </View>
      ) : null}
      {nutrition.structured_exercise ? (
        <View style={styles.listGroup}>
          <Text style={styles.subheading}>تمرین ساختاریافته</Text>
          <SummaryGrid entries={[
            ["تمرین دارد", yesNo(nutrition.structured_exercise.trains)],
            ["نوع تمرین", humanize(nutrition.structured_exercise.exercise_type)],
            ["روز در هفته", nutrition.structured_exercise.days_per_week === null ? null : number(nutrition.structured_exercise.days_per_week)],
            ["دقیقه هر جلسه", nutrition.structured_exercise.minutes_per_session === null ? null : number(nutrition.structured_exercise.minutes_per_session)],
            ["شدت", humanize(nutrition.structured_exercise.intensity)],
            ["منبع", humanize(nutrition.structured_exercise.source)],
            ["تأیید در", dateTime(nutrition.structured_exercise.confirmed_at)],
          ]} />
        </View>
      ) : null}
    </View>
  );
}

function MedicalSection({ medical }: { readonly medical: ReviewProfileMedical }) {
  const activeFlags = Object.entries(medical.flags ?? {}).filter(([, active]) => active);
  return (
    <View style={styles.section}>
      <SummaryGrid entries={[
        ["نتیجه ایمنی", humanize(medical.safety_outcome)],
        ["محدودیت غذایی پزشک", medical.physician_dietary_restrictions],
        ["شرایط مهم دیگر", medical.other_relevant_condition],
        ["نسخه سیاست پزشکی", medical.medical_condition_policy_version],
        ["تاریخ تصمیم ایمنی", dateTime(medical.safety_decision_created_at)],
        ["تاریخ ثبت پزشکی", dateTime(medical.created_at)],
        ["آخرین به‌روزرسانی پزشکی", dateTime(medical.updated_at)],
      ]} />
      {activeFlags.length > 0 ? (
        <View style={styles.listGroup}>
          <Text style={styles.subheading}>هشدارهای فعال</Text>
          {activeFlags.map(([key]) => <Text key={key} style={styles.warningText}>{medicalFlagLabels[key] ?? humanize(key)}</Text>)}
        </View>
      ) : null}
      {(medical.conditions ?? []).length > 0 ? (
        <View style={styles.listGroup}>
          <Text style={styles.subheading}>شرایط پزشکی</Text>
          {(medical.conditions ?? []).map((condition) => <Text key={condition.code} style={styles.bodyText}>{humanize(condition.code)}{condition.details ? ` · ${condition.details}` : ""}</Text>)}
        </View>
      ) : null}
      {(medical.medications ?? []).length > 0 ? (
        <View style={styles.listGroup}>
          <Text style={styles.subheading}>داروها</Text>
          {(medical.medications ?? []).map((medication) => <Text key={medication.name} style={styles.bodyText}>{medication.name}{medication.dosage ? ` · ${medication.dosage}` : ""}{medication.notes ? ` · ${medication.notes}` : ""}</Text>)}
        </View>
      ) : null}
      {(medical.safety_reason_codes ?? []).length > 0 ? <Text style={styles.warningText}>کدهای ایمنی: {medical.safety_reason_codes.join("، ")}</Text> : null}
    </View>
  );
}

function SummaryGrid({ entries }: { readonly entries: readonly (readonly [string, string | null | undefined])[] }) {
  const visible = entries.filter(([, value]) => value !== null && value !== undefined && value !== "");
  return (
    <View style={styles.grid}>
      {visible.map(([label, value]) => (
        <View key={label} style={styles.gridItem}>
          <Text style={styles.gridLabel}>{label}</Text>
          <Text style={styles.gridValue}>{value}</Text>
        </View>
      ))}
    </View>
  );
}

function humanize(value: string | null | undefined): string {
  if (!value) return "ثبت نشده";
  return valueLabels[value] ?? value.replaceAll("_", " ");
}

function number(value: number | string): string {
  const numeric = Number(value);
  return Number.isFinite(numeric)
    ? formatPersianNumber(numeric, { maximumFractionDigits: 2 })
    : String(value);
}

function measurement(value: number | string | null, unit: string): string {
  return value === null ? "ثبت نشده" : `${number(value)} ${unit}`;
}

function date(value: string | null): string {
  if (!value) return "ثبت نشده";
  try {
    return formatPersianDate(value);
  } catch {
    return value;
  }
}

function dateTime(value: string | null): string {
  if (!value) return "ثبت نشده";
  try {
    return formatTehranDateTime(value);
  } catch {
    return value;
  }
}

function list(value: readonly string[] | null | undefined): string {
  return value === null || value === undefined || value.length === 0 ? "ثبت نشده" : value.map(humanize).join("، ");
}

function weekdays(value: readonly number[] | null | undefined): string {
  return value === null || value === undefined || value.length === 0
    ? "ثبت نشده"
    : value.map((item) => number(item + 1)).join("، ");
}

function yesNo(value: boolean): string {
  return value ? "بله" : "خیر";
}

const styles = StyleSheet.create({
  alert: {
    backgroundColor: fiticianTokens.colors.warningSurface,
    borderColor: fiticianTokens.colors.amber,
    borderRadius: fiticianTokens.radii.medium,
    borderWidth: 1,
    gap: fiticianTokens.spacing[2],
    marginTop: fiticianTokens.spacing[3],
    padding: fiticianTokens.spacing[3],
  },
  alertLabel: {
    color: fiticianTokens.colors.amber,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  alertText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    lineHeight: fiticianTokens.typography.lineHeight.body,
  },
  bodyText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    lineHeight: fiticianTokens.typography.lineHeight.body,
  },
  container: {
    gap: fiticianTokens.spacing[3],
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: fiticianTokens.spacing[2],
  },
  gridItem: {
    backgroundColor: fiticianTokens.colors.surfaceSubtle,
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.small,
    borderWidth: 1,
    flexGrow: 1,
    minWidth: "46%",
    padding: fiticianTokens.spacing[2],
  },
  gridLabel: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  gridValue: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    marginTop: fiticianTokens.spacing[1],
  },
  header: {
    alignItems: "center",
    gap: fiticianTokens.spacing[2],
    justifyContent: "space-between",
    marginBottom: fiticianTokens.spacing[3],
  },
  headerCopy: {
    flex: 1,
    gap: fiticianTokens.spacing[1],
  },
  eyebrow: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  highlightCard: {
    gap: fiticianTokens.spacing[2],
  },
  listGroup: {
    gap: fiticianTokens.spacing[2],
    marginTop: fiticianTokens.spacing[3],
  },
  section: {
    gap: fiticianTokens.spacing[2],
  },
  sectionTitle: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.lg,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  star: {
    color: fiticianTokens.colors.aqua,
    fontSize: fiticianTokens.typography.fontSize.h2,
  },
  subheading: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  title: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.h2,
    lineHeight: 32,
  },
  warningText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.amber,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
  },
});
