import { useState } from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import Svg, {
  Circle,
  G,
  Line,
  Polyline,
  Text as SvgText,
} from "react-native-svg";
import { chartGeometry, progressNumber, type ChartDatum } from "@fitician/core";
import { fiticianTokens as t } from "../ui/tokens";
export function TrendChart({
  series,
  labels,
  unit,
  language,
  onSelect,
  valueLabels,
}: {
  series: ChartDatum[][];
  labels: string[];
  unit: string;
  language: "fa" | "en";
  valueLabels?: Record<number, string>;
  onSelect?: (index: number) => void;
}) {
  const [width, setWidth] = useState(300),
    [selected, setSelected] = useState<number | null>(null),
    height = 220,
    chart = chartGeometry(
      series,
      width,
      height,
      valueLabels ? [1, 3] : undefined,
    ),
    colors = [t.colors.aqua, t.colors.coral],
    format = (v: number) => valueLabels?.[v] ?? progressNumber(v, language),
    date = (v: number) =>
      new Intl.DateTimeFormat(language, {
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      }).format(v);
  const dates = series[0] ?? [];
  const xAt = (d: string) =>
    48 +
    (chart.maxX === chart.minX
      ? 0.5
      : (Date.parse(d) - chart.minX) / (chart.maxX - chart.minX)) *
      (width - 62);
  const select = (index: number) => {
    setSelected(index);
    onSelect?.(index);
  };
  const describe = (index: number) =>
    `${date(Date.parse(dates[index].date))}: ${series.map((s, i) => `${labels[i]} ${s[index]?.value == null ? "—" : format(s[index].value!)} ${unit}`).join(", ")}`;
  return (
    <View
      onLayout={(e) => {
        if (e.nativeEvent.layout.width > 0)
          setWidth(e.nativeEvent.layout.width);
      }}
      style={styles.chart}
    >
      <Svg
        testID="progress-trend-plot"
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        accessible={false}
        onPress={(e) => {
          if (!dates.length) return;
          const x = e.nativeEvent.locationX;
          if (!Number.isFinite(x)) return;
          const nearest = dates.reduce(
            (best, p, i) =>
              Math.abs(xAt(p.date) - x) < Math.abs(xAt(dates[best].date) - x)
                ? i
                : best,
            0,
          );
          select(nearest);
        }}
      >
        {(valueLabels
          ? Object.keys(valueLabels)
              .map(Number)
              .map((v) => (chart.maxY - v) / (chart.maxY - chart.minY))
          : [0, 0.5, 1]
        ).map((f) => {
          const y = 18 + f * (height - 50);
          return (
            <G key={f}>
              <Line
                x1={48}
                x2={width - 14}
                y1={y}
                y2={y}
                stroke={t.colors.line}
                strokeWidth={0.7}
                strokeDasharray="3 5"
              />
              <SvgText
                x={40}
                y={y + 4}
                textAnchor="end"
                fill={t.colors.muted}
                fontSize={11}
              >
                {format(
                  valueLabels
                    ? Math.round(chart.maxY - f * (chart.maxY - chart.minY))
                    : chart.maxY - f * (chart.maxY - chart.minY),
                )}
              </SvgText>
            </G>
          );
        })}
        {dates.length > 0 && (
          <>
            <SvgText x={48} y={height - 6} fill={t.colors.muted} fontSize={10}>
              {date(chart.minX)}
            </SvgText>
            <SvgText
              x={width - 14}
              y={height - 6}
              textAnchor="end"
              fill={t.colors.muted}
              fontSize={10}
            >
              {date(chart.maxX)}
            </SvgText>
          </>
        )}
        {selected !== null && dates[selected] && (
          <Line
            x1={xAt(dates[selected].date)}
            x2={xAt(dates[selected].date)}
            y1={14}
            y2={height - 32}
            stroke={t.colors.muted}
            strokeOpacity={0.5}
            strokeDasharray="3 4"
          />
        )}
        {chart.lines.flatMap((line, i) => [
          ...line.segments.map((ps, j) => (
            <Polyline
              key={`line-${i}-${j}`}
              points={ps.map((p) => `${p.x},${p.y}`).join(" ")}
              fill="none"
              stroke={colors[i]}
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray={series.length > 1 && i === 0 ? "6 5" : undefined}
            />
          )),
          ...line.points.map((p) => (
            <Circle
              key={`point-${i}-${p.index}`}
              cx={p.x}
              cy={p.y}
              r={selected === p.index ? 5.5 : 3.5}
              fill={colors[i]}
              stroke={t.colors.surface}
              strokeWidth={2}
            />
          )),
        ])}
      </Svg>
      {/* Native buttons share the chart's date hit regions and expose missing days to screen readers. */}
      <View style={styles.hitLayer} pointerEvents="none">
        {dates.map((p, index) => (
          <Pressable
            key={index}
            accessibilityRole="button"
            accessibilityActions={[{ name: "activate" }]}
            onAccessibilityAction={() => select(index)}
            accessibilityLabel={describe(index)}
            accessibilityState={{ selected: selected === index }}
            onPress={() => select(index)}
            style={[
              styles.hit,
              {
                left: Math.max(0, Math.min(width - 48, xAt(p.date) - 24)),
                width: 48,
              },
            ]}
          />
        ))}
      </View>
      <View
        style={[
          styles.legend,
          { direction: language === "fa" ? "rtl" : "ltr" },
        ]}
      >
        {labels.map((label, i) => (
          <View key={label} style={styles.legendItem}>
            <View style={[styles.swatch, { backgroundColor: colors[i] }]} />
            <Text style={styles.label}>{label}</Text>
          </View>
        ))}
        <Text style={styles.label}>{unit}</Text>
      </View>
    </View>
  );
}
const styles = StyleSheet.create({
  chart: { gap: 10, width: "100%", direction: "ltr" },
  legend: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  swatch: { width: 16, height: 3 },
  label: {
    fontSize: 11,
    color: t.colors.muted,
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  hitLayer: { position: "absolute", top: 14, left: 0, right: 0, height: 174 },
  hit: { position: "absolute", top: 0, height: 174 },
});
