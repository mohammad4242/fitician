import type { components } from "./generated/api.js";
import type { TransportRequest } from "./transport.js";
type OverviewWire = components["schemas"]["ProgressOverview"];
export type ProgressOverview = Omit<
  OverviewWire,
  "body_measurements" | "recovery" | "insights"
> & {
  body_measurements: Record<BodyMetric, BodyTrend>;
  recovery: NonNullable<OverviewWire["recovery"]>;
  insights: NonNullable<OverviewWire["insights"]>;
};
export type ProgressPreset = components["schemas"]["ProgressContext"]["preset"];
export type BodyMetric = "weight" | "waist" | "hip" | "shoulder_width";
type BodySeriesWire = components["schemas"]["BodySeries"];
export type BodyTrend = Omit<
  BodySeriesWire,
  "points" | "start_value" | "latest_value" | "delta"
> & {
  points: NonNullable<BodySeriesWire["points"]>;
  start_value: number | null;
  latest_value: number | null;
  delta: number | null;
};
function normalizeOverview(data: OverviewWire): ProgressOverview {
  if (!data?.context) throw new Error("Invalid progress overview");
  const metrics = {} as Record<BodyMetric, BodyTrend>;
  for (const name of progressMetrics) {
    const series = data.body_measurements?.[name];
    metrics[name] = {
      unit: series?.unit ?? (name === "weight" ? "kg" : "cm"),
      ...series,
      legacy_coverage: series?.legacy_coverage ?? "changed_values_only",
      points: series?.points ?? [],
      start_value: series?.start_value ?? null,
      latest_value: series?.latest_value ?? null,
      delta: series?.delta ?? null,
    };
  }
  return {
    ...data,
    body_measurements: metrics,
    recovery: data.recovery ?? [],
    insights: data.insights ?? [],
  };
}
export type CalorieDay = components["schemas"]["CaloriePoint"];
export type MeasurementInput = components["schemas"]["BodyMeasurementInput"];
export function createProgressApi(
  request: <T>(input: TransportRequest) => Promise<T>,
) {
  return {
    overview: async (preset: ProgressPreset = "week", timezone?: string) =>
      normalizeOverview(
        await request<OverviewWire>({
          path: `/api/v1/progress/overview?preset=${preset}${timezone ? "&timezone=" + encodeURIComponent(timezone) : ""}`,
        }),
      ),
    recordMeasurement: (input: MeasurementInput) =>
      request<components["schemas"]["BodyMeasurementCreated"]>({
        path: "/api/v1/profile/body-measurements",
        method: "POST",
        body: { ...input },
      }),
  };
}
export const progressMetrics: readonly BodyMetric[] = [
  "weight",
  "waist",
  "hip",
  "shoulder_width",
];
export const progressCopy = {
  fa: {
    title: "پیشرفت من",
    hero: "وضعیت مسیرت، در یک نگاه",
    week: "این هفته",
    four_weeks: "۴ هفته اخیر",
    current_program: "دوره فعلی",
    goal: "هدف",
    program: "برنامه فعلی",
    programWeek: "هفته",
    training: "تمرین",
    nutrition: "تغذیه",
    body: "بدن",
    recovery: "ریکاوری",
    bodyTrend: "روند تغییرات بدن",
    calories: "کالری و پایبندی تغذیه",
    target: "کالری هدف",
    actual: "کالری دریافتی",
    weight: "وزن",
    waist: "دور کمر",
    hip: "دور باسن",
    shoulder_width: "پهنای سرشانه",
    record: "ثبت اندازه‌های بدن",
    save: "ثبت اندازه‌ها",
    noBody: "با ثبت اندازه، روند تغییراتت اینجا نمایش داده می‌شود.",
    onePoint: "برای نمایش روند، حداقل یک ثبت دیگر لازم است.",
    noIntake: "برای این روز مصرفی ثبت نشده است.",
    noNutrition:
      "بعد از چند روز ثبت تغذیه، روند کالری و پایبندی اینجا نمایش داده می‌شود.",
    coverage: "روزهای ثبت‌شده",
    alignment: "روزهای نزدیک به هدف",
    comparison: "روزهای قابل مقایسه",
    difference: "اختلاف",
    averageDifference: "میانگین اختلاف با هدف",
    planned: "جلسه برنامه‌ریزی‌شده",
    due: "جلسه موعدرسیده",
    completed: "جلسه انجام‌شده",
    skipped: "انجام‌نشده",
    overdue: "عقب‌افتاده",
    rescheduled: "جلسه جابه‌جاشده",
    adherence: "پایبندی به جلسه‌های موعدرسیده",
    noTraining: "پس از شروع برنامه، وضعیت جلسه‌ها اینجا نمایش داده می‌شود.",
    noRecovery:
      "پس از اولین چک‌این هفتگی، وضعیت ریکاوری اینجا نمایش داده می‌شود.",
    difficulty: "سختی گزارش‌شده",
    analysis: "تحلیل بدن",
    analysisHistory: "تاریخچه و مقایسه تحلیل بدن",
    newAnalysis: "تحلیل جدید",
    noAnalysis: "با ثبت تحلیل بدن، نتیجه و مقایسه‌ها در دسترس قرار می‌گیرند.",
    insights: "آنچه ثبت‌ها نشان می‌دهند",
    loading: "در حال دریافت پیشرفت…",
    error: "دریافت پیشرفت ناموفق بود. دوباره تلاش کن.",
    retry: "تلاش دوباره",
    close: "بستن",
    details: "جزئیات و تعریف شاخص‌ها",
    nutritionRule:
      "نزدیک به هدف: ۸۰ تا ۱۲۰٪ کالری هدف، در روزهای پایان‌یافته با چک‌این معتبر و ثبت‌های تأییدشده با اطمینان بالا. این شرط، ثبت کامل تمام مصرف روز را تضمین نمی‌کند.",
    trainingRule:
      "پایبندی تمرین = جلسه‌های انجام‌شده ÷ جلسه‌های موعدرسیده. جلسه‌های آینده و جلسه‌های باز امروز در مخرج نیستند.",
    legacyBody:
      "ثبت‌های قدیمی فقط هنگام تغییر مقدار نمایش داده می‌شوند؛ مقدارهای کپی‌شده ثبت تازه نیستند.",
    missingTarget: "هدف تاریخی قابل تأیید نیست.",
    manual: "ثبت دستی",
    legacy: "ثبت قدیمی پروفایل",
    inProgress: "امروز · در حال ثبت",
    clipped: "نمایش حداکثر یک سال اخیر این دوره.",
    measurementHint:
      "فقط اندازه‌هایی را وارد کن که همین حالا اندازه گرفته‌ای. پهنای سرشانه فاصله مستقیم دو سر شانه است، نه دور سرشانه.",
    observations: "ثبت واقعی",
    source: "منبع",
    recordError:
      "ثبت اندازه‌ها ناموفق بود. مقدارها را بررسی کن و دوباره تلاش کن.",
    selfReported: "پیشرفت قدرت · گزارش شخصی پایان دوره",
  },
  en: {
    title: "My Progress",
    hero: "Your progress at a glance",
    week: "This week",
    four_weeks: "Last 4 weeks",
    current_program: "Current program",
    goal: "Goal",
    program: "Current program",
    programWeek: "Week",
    training: "Training",
    nutrition: "Nutrition",
    body: "Body",
    recovery: "Recovery",
    bodyTrend: "Body measurement trends",
    calories: "Calories & nutrition adherence",
    target: "Target calories",
    actual: "Recorded calories",
    weight: "Weight",
    waist: "Waist circumference",
    hip: "Hip circumference",
    shoulder_width: "Shoulder width",
    record: "Record body measurements",
    save: "Save measurements",
    noBody: "Record a measurement to see your trend here.",
    onePoint: "One more measurement is needed to show a trend.",
    noIntake: "No intake was recorded for this day.",
    noNutrition:
      "After a few days of tracking, calorie trends and alignment will appear here.",
    coverage: "Recorded days",
    alignment: "Days near target",
    comparison: "Comparable days",
    difference: "Difference",
    averageDifference: "Average difference from target",
    planned: "Scheduled sessions",
    due: "Due sessions",
    completed: "Completed sessions",
    skipped: "Skipped",
    overdue: "Overdue",
    rescheduled: "Rescheduled sessions",
    adherence: "Adherence to due sessions",
    noTraining: "Start a plan to see your session progress.",
    noRecovery: "Your recovery will appear after your first weekly check-in.",
    difficulty: "Reported difficulty",
    analysis: "Body Analysis",
    analysisHistory: "Body Analysis history & comparisons",
    newAnalysis: "New analysis",
    noAnalysis: "Start a Body Analysis to see results and comparisons.",
    insights: "What your records show",
    loading: "Loading your progress…",
    error: "Could not load progress. Please try again.",
    retry: "Try again",
    close: "Close",
    details: "Details & metric definitions",
    nutritionRule:
      "Near target: 80–120% of target calories on completed days with a valid check-in and confirmed high-confidence records. This does not guarantee all daily intake was recorded.",
    trainingRule:
      "Training adherence = completed sessions ÷ due sessions. Future sessions and pending sessions today are excluded.",
    legacyBody:
      "Older records appear only when values changed. Copied values are not new observations.",
    missingTarget: "Historical target cannot be verified.",
    manual: "Manual entry",
    legacy: "Older profile record",
    inProgress: "Today · in progress",
    clipped: "Showing at most the last year of this program.",
    measurementHint:
      "Enter only measurements you have just taken. Shoulder width is the straight distance between the shoulders, not shoulder circumference.",
    observations: "Actual records",
    source: "Source",
    recordError: "Could not save measurements. Check the values and try again.",
    selfReported: "Strength progress · self-reported at cycle end",
  },
} as const;
export const recoveryLabels = {
  fa: { good: "خوب", average: "متوسط", poor: "ضعیف" },
  en: { good: "Good", average: "Average", poor: "Poor" },
} as const;
export const difficultyLabels = {
  fa: {
    too_easy: "خیلی آسان",
    easy: "آسان",
    appropriate: "مناسب",
    hard: "سخت",
    too_hard: "خیلی سخت",
  },
  en: {
    too_easy: "Too easy",
    easy: "Easy",
    appropriate: "Appropriate",
    hard: "Hard",
    too_hard: "Too hard",
  },
} as const;
export const goalLabels: Record<"fa" | "en", Record<string, string>> = {
  fa: {
    lose_weight: "کاهش وزن",
    gain_weight: "افزایش وزن",
    fat_loss: "کاهش چربی",
    build_muscle: "عضله‌سازی",
    body_recomposition: "بازترکیب بدن",
    strength: "قدرت",
    improve_fitness: "بهبود آمادگی",
    maintain_weight: "حفظ وزن",
  },
  en: {
    lose_weight: "Lose weight",
    gain_weight: "Gain weight",
    fat_loss: "Fat loss",
    build_muscle: "Build muscle",
    body_recomposition: "Body recomposition",
    strength: "Strength",
    improve_fitness: "Improve fitness",
    maintain_weight: "Maintain weight",
  },
};
export function progressSummary(
  data: ProgressOverview,
  language: "fa" | "en",
): string[] {
  const lines: string[] = [];
  const c = progressCopy[language],
    n = (v: number) =>
      new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(v);
  if (data.training)
    lines.push(
      language === "fa"
        ? `${n(data.training.completed_sessions)} جلسه از ${n(data.training.due_sessions)} جلسه موعدرسیده را انجام داده‌ای.`
        : `You completed ${n(data.training.completed_sessions)} of ${n(data.training.due_sessions)} due sessions.`,
    );
  if (data.nutrition) {
    lines.push(
      language === "fa"
        ? `${n(data.nutrition.logged_days)} روز از ${n(data.nutrition.elapsed_days)} روز پایان‌یافته، تغذیه ثبت شده است.`
        : `Nutrition was recorded on ${n(data.nutrition.logged_days)} of ${n(data.nutrition.elapsed_days)} completed days.`,
    );
    if (data.nutrition.comparable_days)
      lines.push(
        `${c.alignment}: ${n(data.nutrition.adherent_days)} / ${n(data.nutrition.comparable_days)}`,
      );
  }
  for (const metric of progressMetrics) {
    const series = data.body_measurements[metric];
    if (series.delta !== null)
      lines.push(
        `${c[metric]}: ${new Intl.NumberFormat(language, { signDisplay: "exceptZero", maximumFractionDigits: 2 }).format(series.delta)} ${series.unit}`,
      );
  }
  return lines;
}
export interface ChartDatum {
  date: string;
  value: number | null;
}
export interface ChartPoint {
  x: number;
  y: number;
  index: number;
  value: number;
  date: string;
}
/** Only recorded points; segmented paths preserve gaps. No smoothing or synthetic points. */
export function chartGeometry(
  series: readonly (readonly ChartDatum[])[],
  width: number,
  height: number,
) {
  const padding = { left: 48, right: 14, top: 18, bottom: 32 };
  const times = series
    .flatMap((line) => line.map((p) => Date.parse(p.date)))
    .filter(Number.isFinite);
  const values = series.flatMap((line) =>
    line.flatMap((p) =>
      p.value !== null && Number.isFinite(p.value) ? [p.value] : [],
    ),
  );
  const minX = times.length ? Math.min(...times) : 0,
    maxX = times.length ? Math.max(...times) : 1;
  const low = values.length ? Math.min(...values) : 0,
    high = values.length ? Math.max(...values) : 1;
  const margin = Math.max((high - low) * 0.15, high * 0.02, 1),
    minY = Math.max(0, low - margin),
    maxY = high + margin;
  const lines = series.map((line) => {
    const points: ChartPoint[] = [],
      segments: ChartPoint[][] = [];
    let segment: ChartPoint[] = [];
    for (const [index, p] of line.entries()) {
      if (
        p.value === null ||
        !Number.isFinite(p.value) ||
        !Number.isFinite(Date.parse(p.date))
      ) {
        if (segment.length) segments.push(segment);
        segment = [];
        continue;
      }
      const point = {
        index,
        date: p.date,
        value: p.value,
        x:
          padding.left +
          (maxX === minX ? 0.5 : (Date.parse(p.date) - minX) / (maxX - minX)) *
            (width - padding.left - padding.right),
        y:
          padding.top +
          ((maxY - p.value) / (maxY - minY)) *
            (height - padding.top - padding.bottom),
      };
      points.push(point);
      segment.push(point);
    }
    if (segment.length) segments.push(segment);
    return { points, segments };
  });
  return { lines, minX, maxX, minY, maxY, padding, width, height };
}
