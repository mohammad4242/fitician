import { weightTrendPoints, resolvedIanaTimeZone } from "@fitician/core";
import { Text, View } from "react-native";
import Svg, { Circle, Polyline } from "react-native-svg";
import { languageForDirection } from "../ui/rtl";
export function WeightTrend({ measurements }: { measurements: readonly { measured_at: string; weight_kg: number }[] }) {
  const points = weightTrendPoints(measurements);
  const en = languageForDirection() === "en";
  const locale = en ? "en-US" : "fa-IR";
  const delta = points.length > 1 ? points.at(-1)!.weight_kg - points[0]!.weight_kg : null;
  return <View accessibilityLabel={en ? "Weight trend" : "روند وزن"}>
    <Text>{en ? "Weight trend" : "روند وزن"}</Text>
    {!points.length ? <Text>{en ? "No weight recorded in this range." : "در این بازه وزنی ثبت نشده است."}</Text> : <>
      <Svg height={140} width="100%" viewBox="-5 0 110 100" accessibilityLabel={en ? "Recorded weights" : "وزن‌های ثبت‌شده"}>
        {points.length > 1 && <Polyline points={points.map(p => `${p.x},${p.y}`).join(" ")} fill="none" stroke="#19c8b5" strokeWidth={1} />}
        {points.map((p, i) => <Circle key={i} cx={p.x} cy={p.y} r={2} fill="#19c8b5" />)}
      </Svg>
      <Text>{delta === null ? (en ? "One measurement; record another to compare." : "یک اندازه‌گیری؛ برای مقایسه وزن دیگری ثبت کن.") : `${en ? "Change from first to last" : "تغییر اولین تا آخرین وزن"}: ${delta > 0 ? "+" : ""}${delta.toLocaleString(locale, { maximumFractionDigits: 2 })} kg`}</Text>
      {points.map((p, i) => <Text key={i}>{new Intl.DateTimeFormat(locale, { timeZone: resolvedIanaTimeZone(), dateStyle: "medium" }).format(new Date(p.measured_at))} — {p.weight_kg.toLocaleString(locale)} kg</Text>)}
      <Text>{en ? "Only recorded measurements are shown; weight changes alone do not prove dietary effects." : "فقط اندازه‌گیری‌های ثبت‌شده نمایش داده می‌شوند؛ تغییر وزن به‌تنهایی اثر رژیم را ثابت نمی‌کند."}</Text>
    </>}
  </View>;
}
