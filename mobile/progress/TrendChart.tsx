import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import Svg, { Circle, Line, Polyline, Text as SvgText } from "react-native-svg";
import { chartGeometry, type ChartDatum } from "@fitician/core";
import { fiticianTokens as tokens } from "../ui/tokens";
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
    chart = chartGeometry(series, width, 200, valueLabels ? [1, 3] : undefined),
    colors = [tokens.colors.aqua, tokens.colors.coral],
    number = (v: number) =>
      valueLabels?.[v] ??
      new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(v),
    date = (v: number) =>
      new Intl.DateTimeFormat(language, {
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      }).format(v);
  return (
    <View
      onLayout={(e) => {
        if (e.nativeEvent.layout.width > 0)
          setWidth(e.nativeEvent.layout.width);
      }}
      style={styles.chart}
    >
      <Svg
        width="100%"
        height={200}
        viewBox={`0 0 ${width} 200`}
        accessibilityLabel={labels.join(" / ")}
      >
        {(valueLabels
          ? Object.keys(valueLabels)
              .map(Number)
              .map((v) => (chart.maxY - v) / (chart.maxY - chart.minY))
          : [0, 0.5, 1]
        ).map((f) => {
          const y =
            chart.padding.top +
            f * (chart.height - chart.padding.top - chart.padding.bottom);
          return (
            <ViewSvgGrid
              key={f}
              y={y}
              width={width}
              value={number(
                valueLabels
                  ? Math.round(chart.maxY - f * (chart.maxY - chart.minY))
                  : chart.maxY - f * (chart.maxY - chart.minY),
              )}
            />
          );
        })}
        <SvgText
          x={chart.padding.left}
          y={194}
          fill={tokens.colors.muted}
          fontSize={10}
        >
          {date(chart.minX)}
        </SvgText>
        <SvgText
          x={width - chart.padding.right}
          y={194}
          textAnchor="end"
          fill={tokens.colors.muted}
          fontSize={10}
        >
          {date(chart.maxX)}
        </SvgText>
        {chart.lines.flatMap((line, i) => [
          ...line.segments.map((points, j) => (
            <Polyline
              key={`line-${i}-${j}`}
              points={points.map((p) => `${p.x},${p.y}`).join(" ")}
              fill="none"
              stroke={colors[i]}
              strokeWidth={2}
              strokeDasharray={series.length > 1 && i === 0 ? "6 5" : undefined}
            />
          )),
          ...line.points.map((p) => (
            <Circle
              key={`point-${i}-${p.index}`}
              cx={p.x}
              cy={p.y}
              r={4}
              fill={colors[i]}
              onPress={() => onSelect?.(p.index)}
              accessibilityLabel={`${labels[i]} ${date(Date.parse(p.date))}: ${number(p.value)} ${unit}`}
            />
          )),
        ])}
      </Svg>
      <View style={styles.legend}>
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
function ViewSvgGrid({
  y,
  width,
  value,
}: {
  y: number;
  width: number;
  value: string;
}) {
  return (
    <>
      <Line x1={48} x2={width - 14} y1={y} y2={y} stroke={tokens.colors.line} />
      <SvgText
        x={40}
        y={y + 4}
        textAnchor="end"
        fill={tokens.colors.muted}
        fontSize={11}
      >
        {value}
      </SvgText>
    </>
  );
}
const styles = StyleSheet.create({
  chart: { gap: 10, width: "100%" },
  legend: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  swatch: { width: 16, height: 3 },
  label: {
    fontSize: 11,
    color: tokens.colors.muted,
    fontFamily: tokens.typography.fontFamily.bodyPersian,
  },
});
