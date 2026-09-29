import { weightTrendPoints } from "@fitician/core";
export function WeightTrend({ measurements, english, timezone }: { measurements: readonly { measured_at: string; weight_kg: number }[]; english: boolean; timezone: string }) {
  const points = weightTrendPoints(measurements);
  const locale = english ? "en-US" : "fa-IR";
  const date = (value: string) => new Intl.DateTimeFormat(locale, { timeZone: timezone, dateStyle: "medium" }).format(new Date(value));
  const delta = points.length > 1 ? points.at(-1)!.weight_kg - points[0]!.weight_kg : null;
  return <section aria-label={english ? "Weight trend" : "روند وزن"}>
    <h3>{english ? "Weight trend" : "روند وزن"}</h3>
    {points.length === 0 ? <p>{english ? "No weight recorded in this range." : "در این بازه وزنی ثبت نشده است."}</p> : <>
      <svg viewBox="-5 0 110 100" role="img" aria-label={english ? "Recorded weights" : "وزن‌های ثبت‌شده"} style={{ width: "100%", height: 140 }}>
        {points.length > 1 && <polyline points={points.map(p => `${p.x},${p.y}`).join(" ")} fill="none" stroke="currentColor" strokeWidth="1" />}
        {points.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="2" fill="currentColor"><title>{date(p.measured_at)}: {p.weight_kg} kg</title></circle>)}
      </svg>
      <p>{delta === null ? (english ? "One measurement; record another to compare." : "یک اندازه‌گیری؛ برای مقایسه وزن دیگری ثبت کن.") : `${english ? "Change from first to last" : "تغییر اولین تا آخرین وزن"}: ${delta > 0 ? "+" : ""}${delta.toLocaleString(locale, { maximumFractionDigits: 2 })} kg`}</p>
      <ul>{points.map((p, i) => <li key={i}>{date(p.measured_at)} — {p.weight_kg.toLocaleString(locale)} kg</li>)}</ul>
      <p>{english ? "Only recorded measurements are shown; weight changes alone do not prove dietary effects." : "فقط اندازه‌گیری‌های ثبت‌شده نمایش داده می‌شوند؛ تغییر وزن به‌تنهایی اثر رژیم را ثابت نمی‌کند."}</p>
    </>}
  </section>;
}
