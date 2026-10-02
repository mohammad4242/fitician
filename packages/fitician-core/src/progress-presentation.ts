import {
  progressCopy,
  recoveryLabels,
  type ChartDatum,
  type ProgressOverview,
} from "./progress.js";
export type ProgressTab =
  | "overview"
  | "calories"
  | "body"
  | "training"
  | "recovery"
  | "analysis";
export type ProgressLanguage = "fa" | "en";
export const progressPresentationCopy = {
  fa: {
    overview: "نمای کلی",
    calories: "کالری",
    bodyTitle: "وزن و اندازه‌های بدن",
    caloriesTitle: "کالری و پایبندی",
    currentWeight: "وزن فعلی",
    start: "شروع",
    current: "فعلی",
    change: "تغییر",
    adherence: "پایبندی",
    averageDifference: "میانگین اختلاف",
    difficulty: "سختی تمرین",
    latestCheckIn: "آخرین چک‌این",
    skipped: "رد شده",
    rescheduled: "جابه‌جا شده",
    overdue: "عقب‌افتاده",
    planned: "برنامه‌ریزی‌شده",
    completed: "انجام‌شده",
    period: "بازه زمانی",
    noRecovery: "بعد از اولین چک‌این، ریکاوری اینجا نمایش داده می‌شود.",
    latestAnalysis: "آخرین تحلیل",
    notAvailable: "برای این مسیر فعال نیست",
    analysisRecorded: "ثبت شده",
    queued: "در صف",
    validating: "در حال بررسی",
    analyzing: "در حال تحلیل",
    review_pending: "در انتظار بازبینی",
    completedStatus: "تکمیل شده",
    failed: "ناموفق",
  },
  en: {
    overview: "Overview",
    calories: "Calories",
    bodyTitle: "Weight & measurements",
    caloriesTitle: "Calories & adherence",
    currentWeight: "Current weight",
    start: "Start",
    current: "Current",
    change: "Change",
    adherence: "Adherence",
    averageDifference: "Average difference",
    difficulty: "Workout difficulty",
    latestCheckIn: "Latest check-in",
    skipped: "Skipped",
    rescheduled: "Rescheduled",
    overdue: "Overdue",
    planned: "Planned",
    completed: "Completed",
    period: "Time range",
    noRecovery: "Recovery appears after your first check-in.",
    latestAnalysis: "Latest analysis",
    notAvailable: "Not enabled for this plan",
    analysisRecorded: "Recorded",
    queued: "Queued",
    validating: "Validating",
    analyzing: "Analyzing",
    review_pending: "Awaiting review",
    completedStatus: "Completed",
    failed: "Failed",
  },
} as const;
export function progressNumber(
  value: number | null | undefined,
  language: ProgressLanguage,
  signed = false,
) {
  return value == null
    ? "—"
    : new Intl.NumberFormat(language, {
        maximumFractionDigits: 2,
        signDisplay: signed ? "exceptZero" : "auto",
      }).format(value);
}
export function progressDate(
  value: string,
  language: ProgressLanguage,
  timezone?: string,
) {
  return new Intl.DateTimeFormat(language, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: value.length === 10 ? "UTC" : timezone,
  }).format(new Date(value.length === 10 ? value + "T12:00:00Z" : value));
}
export function progressCount(
  value: number,
  total: number,
  language: ProgressLanguage,
  kind: "days" | "sessions",
) {
  const n = (v: number) => progressNumber(v, language);
  return language === "fa"
    ? `${n(value)} از ${n(total)} ${kind === "days" ? "روز ثبت شده" : "جلسه"}`
    : `${n(value)} of ${n(total)} ${kind === "days" ? "days recorded" : "sessions"}`;
}
export function progressTabs(data: ProgressOverview | null) {
  return (
    [
      "overview",
      "calories",
      "body",
      "training",
      "recovery",
      "analysis",
    ] as const
  ).map((id) => ({
    id,
    disabled:
      !!data &&
      (id === "calories"
        ? !data.context.nutrition_enabled
        : id === "training" || id === "recovery"
          ? !data.context.training_enabled
          : false),
  }));
}
export function progressTabLabel(id: ProgressTab, language: ProgressLanguage) {
  return id === "overview" || id === "calories"
    ? progressPresentationCopy[language][id]
    : progressCopy[language][id];
}
export function calorieSeries(
  nutrition: NonNullable<ProgressOverview["nutrition"]>,
): ChartDatum[][] {
  return [
    nutrition.series.map((p) => ({ date: p.date, value: p.target_kcal })),
    nutrition.series.map((p) => ({ date: p.date, value: p.actual_kcal })),
  ];
}
export function recoverySeries(data: ProgressOverview): ChartDatum[][] {
  return [
    data.recovery.map((p) => ({
      date: p.recorded_at,
      value: { poor: 1, average: 2, good: 3 }[p.recovery],
    })),
  ];
}
export function analysisStatus(
  status: string | null | undefined,
  language: ProgressLanguage,
) {
  const c = progressPresentationCopy[language];
  switch (status) {
    case "queued":
      return c.queued;
    case "validating":
      return c.validating;
    case "analyzing":
      return c.analyzing;
    case "review_pending":
      return c.review_pending;
    case "completed":
      return c.completedStatus;
    case "failed":
      return c.failed;
    default:
      return c.analysisRecorded;
  }
}
export interface OverviewCard {
  tab: Exclude<ProgressTab, "overview">;
  title: string;
  value: string;
  support: string;
  extra?: string;
  series: ChartDatum[][];
  bars?: { planned: number; completed: number }[];
  status?: "good" | "average" | "poor";
}
export function overviewCards(
  data: ProgressOverview,
  language: ProgressLanguage,
): OverviewCard[] {
  const c = progressCopy[language],
    p = progressPresentationCopy[language],
    n = (v: number | null | undefined, signed = false) =>
      progressNumber(v, language, signed);
  const cards: OverviewCard[] = [];
  if (data.context.nutrition_enabled && data.nutrition) {
    const t = data.nutrition;
    // Preview at most seven days through today, preserving both historical series and gaps.
    const recent = {
      ...t,
      series: t.series.filter((d) => d.date <= data.context.today).slice(-7),
    };
    cards.push({
      tab: "calories",
      title: p.caloriesTitle,
      value: progressCount(t.logged_days, t.elapsed_days, language, "days"),
      support: `${c.alignment}: ${n(t.adherent_days)}`,
      series: calorieSeries(recent),
    });
  }
  const weight = data.body_measurements.weight;
  const comparable = weight.points.length > 1 && weight.delta !== null;
  cards.push({
    tab: "body",
    title: p.bodyTitle,
    value:
      weight.latest_value == null
        ? "—"
        : progressQuantity(weight.latest_value, weight.unit, language),
    support: comparable
      ? `${p.change}: ${progressQuantity(weight.delta, weight.unit, language, true)}`
      : p.currentWeight,
    extra: comparable
      ? `${p.start}: ${progressQuantity(weight.start_value, weight.unit, language)}`
      : weight.points.length
        ? c.onePoint
        : c.noBody,
    series: comparable
      ? [weight.points.map((p) => ({ date: p.recorded_at, value: p.value }))]
      : [],
  });
  if (data.context.training_enabled) {
    if (data.training) {
      const t = data.training;
      cards.push({
        tab: "training",
        title: c.training,
        value: progressCount(
          t.completed_sessions,
          t.due_sessions,
          language,
          "sessions",
        ),
        support: `${p.adherence}: ${t.adherence_percent == null ? "—" : n(t.adherence_percent) + "%"}`,
        extra: !t.planned_sessions ? c.noTraining : undefined,
        series: [],
        bars: t.weeks,
      });
    }
    const latest = data.recovery.at(-1);
    cards.push({
      tab: "recovery",
      title: c.recovery,
      value: latest ? recoveryLabels[language][latest.recovery] : "—",
      support: latest
        ? `${p.latestCheckIn}: ${progressDate(latest.recorded_at, language, data.context.timezone)}`
        : p.noRecovery,
      series: data.recovery.length > 1 ? recoverySeries(data) : [],
      status: latest?.recovery,
    });
  }
  const analysis = data.body_analysis;
  cards.push({
    tab: "analysis",
    title: c.analysis,
    value: analysis?.latest_at
      ? analysisStatus(analysis.latest_status, language)
      : "—",
    support: analysis?.latest_at
      ? progressDate(analysis.latest_at, language, data.context.timezone)
      : c.noAnalysis,
    series: [],
  });
  return cards;
}

/** Isolate numbers and Latin units from surrounding Persian labels. */
export function progressQuantity(
  value: number | null | undefined,
  unit: string,
  language: ProgressLanguage,
  signed = false,
) {
  const text = `${progressNumber(value, language, signed)} ${unit}`;
  return language === "fa" ? `\u2066${text}\u2069` : text;
}
