export function workoutGuidance(item: { warmup_sets?: number; rir?: number | null; load_guidance?: string; progression_rule?: string }, locale: "fa" | "en"): string[] {
  const en = locale === "en";
  const number = (value: number) => value.toLocaleString(en ? "en-US" : "fa-IR");
  const lines: string[] = [];
  if (item.warmup_sets && item.warmup_sets > 0) lines.push(en ? `${number(item.warmup_sets)} warm-up sets before working sets; gradually increase the load.` : `${number(item.warmup_sets)} ست گرم‌کردن پیش از ست‌های اصلی؛ وزنه را تدریجی افزایش بده.`);
  if (item.rir != null) lines.push(en ? `Finish each set with about ${number(item.rir)} repetitions still possible with good technique (RIR).` : `هر ست را وقتی تمام کن که حدود ${number(item.rir)} تکرار دیگر با فرم درست می‌توانی انجام بدهی (RIR).`);
  if (item.load_guidance) lines.push(item.load_guidance === "Select a load that preserves the target RIR." ? (en ? "Choose a weight that lets you reach the prescribed repetitions while keeping the stated repetitions in reserve." : "وزنه‌ای انتخاب کن که تکرارهای برنامه را با تعداد تکرار ذخیرهٔ مشخص‌شده انجام بدهی.") : item.load_guidance);
  if (item.progression_rule === "double_progression_v1") lines.push(en ? "When all working sets reach the top of the rep range with the prescribed reserve and good technique for two sessions, increase the weight by the smallest available increment." : "وقتی در دو جلسه همهٔ ست‌های اصلی را تا بالای بازهٔ تکرار، با فرم درست و تکرار ذخیرهٔ تعیین‌شده انجام دادی، وزنه را به اندازهٔ کوچک‌ترین افزایش موجود بالا ببر.");
  else if (item.progression_rule && item.progression_rule !== "legacy") lines.push(item.progression_rule);
  return lines;
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
