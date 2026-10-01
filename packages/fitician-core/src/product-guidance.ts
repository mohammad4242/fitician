import fa from "./i18n/fa";
import en from "./i18n/en";

type ExecutionGuideExercise = {
  exercise?: { name_fa?: string | null; name_en?: string | null };
  warmup_sets?: number;
  load_guidance?: string;
  progression_rule?: string;
};

/** Shared program guidance; prescriptions and exercise-specific notes remain untouched. */
export function workoutExecutionGuidance(items: readonly ExecutionGuideExercise[], locale: "fa" | "en"): string[] {
  const english = locale === "en";
  const copy = (english ? en : fa).translation.workoutPlan.guidance;
  const lines = [copy.form, copy.warmup, copy.rir, copy.load, copy.progress, copy.recovery, copy.pain];
  const instructions = new Map<string, Set<string>>();
  const add = (text: string, name: string) => {
    const normalized = text.trim().replace(/\s+/g, " ");
    if (!normalized) return;
    const names = instructions.get(normalized) ?? new Set<string>();
    if (name) names.add(name);
    instructions.set(normalized, names);
  };
  let bodyweight = false;
  for (const item of items) {
    const name = (english ? item.exercise?.name_en || item.exercise?.name_fa : item.exercise?.name_fa || item.exercise?.name_en) ?? "";
    if (item.warmup_sets && item.warmup_sets > 0) {
      const count = item.warmup_sets.toLocaleString(english ? "en-US" : "fa-IR");
      add(english ? `${count} warm-up sets before working sets.` : `${count} ست گرم‌کردن پیش از ست‌های اصلی.`, name);
    }
    const load = item.load_guidance?.trim();
    const rule = item.progression_rule?.trim();
    if (load === "Use a bodyweight variation that preserves the target RIR." || rule === "bodyweight_double_progression_v1") bodyweight = true;
    if (load && load !== "Select a load that preserves the target RIR." && load !== "Use a bodyweight variation that preserves the target RIR.") add(load, name);
    if (rule && !["legacy", "double_progression_v1", "bodyweight_double_progression_v1"].includes(rule)) add(rule, name);
  }
  if (bodyweight) lines.push(copy.bodyweight);
  for (const [text, names] of instructions) {
    lines.push(names.size ? `${[...names].join(english ? ", " : "، ")}: ${text}` : text);
  }
  return [...new Set(lines)];
}
export function cardioGuidance(cardio: Record<string, unknown> | null | undefined, locale: "fa" | "en"): string | null {
  if (!cardio || typeof cardio.duration_minutes !== "number" || cardio.duration_minutes <= 0) return null;
  const en = locale === "en";
  const names: Record<string, string> = { "Stationary Bike": "دوچرخه ثابت", "Treadmill": "تردمیل", "Elliptical": "الپتیکال", "Walking": "پیاده‌روی" };
  const name = String(cardio.modality_name ?? cardio.modality ?? (en ? "Cardio" : "هوازی"));
  const intensity = String(cardio.intensity ?? "");
  const intensities: Record<string, string> = { low: "سبک", light: "سبک", moderate: "متوسط", vigorous: "شدید", high: "شدید" };
  return en ? `Cardio after resistance training: ${name}, ${cardio.duration_minutes} minutes${intensity ? `, ${intensity} intensity` : ""}.` : `هوازی پس از تمرین مقاومتی: ${names[name] ?? name}، ${cardio.duration_minutes.toLocaleString("fa-IR")} دقیقه${intensity ? `، شدت ${intensities[intensity] ?? intensity}` : ""}.`;
}
export function weightTrendPoints(measurements: readonly { measured_at: string; weight_kg: number }[]) {
  const values = measurements.filter(p => Number.isFinite(Date.parse(p.measured_at)) && Number.isFinite(p.weight_kg) && p.weight_kg > 0).slice().sort((a, b) => Date.parse(a.measured_at) - Date.parse(b.measured_at));
  const start = Date.parse(values[0]?.measured_at ?? "");
  const span = Date.parse(values.at(-1)?.measured_at ?? "") - start;
  const min = Math.min(...values.map(p => p.weight_kg));
  const max = Math.max(...values.map(p => p.weight_kg));
  return values.map(p => ({ ...p, x: span > 0 ? (Date.parse(p.measured_at) - start) / span * 100 : 50, y: max > min ? 90 - (p.weight_kg - min) / (max - min) * 80 : 50 }));
}
