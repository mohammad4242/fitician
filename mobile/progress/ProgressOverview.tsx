import { useThemeTokens, useThemeStyles } from "../ui/theme/ThemeProvider";
import type { FiticianTokens } from "../ui/tokens";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, G, Line, Polyline, Rect } from "react-native-svg";
import {
  chartGeometry,
  overviewCards,
  type OverviewCard,
  type ProgressOverview,
  type ProgressTab,
} from "@fitician/core";
import { Card } from "../ui/components/Card";
import { getTextDirectionStyle } from "../ui/rtl";
import { fiticianTokens as t } from "../ui/tokens";
export function MiniTrend({ card }: { card: OverviewCard }) {
  const t = useThemeTokens();

  const maxCal = Math.max(
    1,
    ...card.series.flatMap((s) =>
      s.flatMap((p) => (p.value == null ? [] : [p.value])),
    ),
  );
  const chart = chartGeometry(
    card.series,
    220,
    115,
    card.tab === "calories"
      ? [0, maxCal * 1.1]
      : card.tab === "recovery"
        ? [1, 3]
        : undefined,
  );
  const max = Math.max(
    1,
    ...(card.bars ?? []).flatMap((w) => [w.planned, w.completed]),
  );
  return (
    <Svg
      width={100}
      height={80}
      viewBox="40 10 180 88"
      accessible={false}
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    >
      {card.series.length > 0 && (
        <>
          <Line x1={48} x2={206} y1={83} y2={83} stroke={t.colors.line} />
          {chart.lines.flatMap((line, i) =>
            card.tab === "calories"
              ? line.points.map((p) => (
                  <Line
                    key={`${i}-${p.index}`}
                    x1={p.x + (i ? 3 : -3)}
                    x2={p.x + (i ? 3 : -3)}
                    y1={83}
                    y2={p.y}
                    stroke={i ? t.colors.coral : t.colors.accentInk}
                    strokeWidth={4}
                    strokeLinecap="round"
                  />
                ))
              : [
                  ...line.segments.map((ps, j) => (
                    <Polyline
                      key={`${i}-line-${j}`}
                      points={ps.map((p) => `${p.x},${p.y}`).join(" ")}
                      fill="none"
                      stroke={t.colors.accentInk}
                      strokeWidth={2.5}
                      strokeLinejoin="round"
                    />
                  )),
                  ...line.points.map((p) => (
                    <Circle
                      key={`${i}-point-${p.index}`}
                      cx={p.x}
                      cy={p.y}
                      r={3}
                      fill={t.colors.accentInk}
                    />
                  )),
                ],
          )}
        </>
      )}
      {card.bars?.slice(-7).map((w, i, rows) => {
        const x = 55 + i * (148 / rows.length);
        return (
          <G key={i}>
            <Rect
              x={x}
              y={83 - (w.planned / max) * 58}
              width={12}
              height={(w.planned / max) * 58}
              rx={4}
              fill={t.colors.line}
            />
            <Rect
              x={x + 2}
              y={83 - (w.completed / max) * 58}
              width={8}
              height={(w.completed / max) * 58}
              rx={3}
              fill={t.colors.accentInk}
            />
          </G>
        );
      })}
      {!card.series.length &&
        !card.bars?.length &&
        (card.status ? (
          (["poor", "average", "good"] as const).map((s, i) => (
            <Rect
              key={s}
              x={65 + i * 40}
              y={45 - i * 9}
              width={25}
              height={20 + i * 9}
              rx={7}
              fill={card.status === s ? t.colors.accentInk : t.colors.line}
            />
          ))
        ) : card.tab === "analysis" ? (
          <>
            <Rect
              x={85}
              y={25}
              width={58}
              height={51}
              rx={13}
              stroke={t.colors.muted}
              strokeWidth={1.5}
              fill="none"
              opacity={0.5}
            />
            <Circle
              cx={114}
              cy={50}
              r={13}
              stroke={t.colors.muted}
              strokeWidth={1.5}
              fill="none"
              opacity={0.5}
            />
          </>
        ) : (
          <>
            <Rect
              x={85}
              y={25}
              width={58}
              height={51}
              rx={13}
              stroke={t.colors.muted}
              strokeWidth={1.5}
              fill="none"
              opacity={0.5}
            />
            <Line
              x1={104}
              y1={50}
              x2={124}
              y2={50}
              stroke={t.colors.muted}
              opacity={0.5}
            />
          </>
        ))}
    </Svg>
  );
}
export function ProgressOverview({
  data,
  language,
  onSelect,
}: {
  data: ProgressOverview;
  language: "fa" | "en";
  onSelect: (tab: ProgressTab) => void;
}) {
  const styles = useThemeStyles(createStyles);

  const direction = language === "fa" ? "rtl" : "ltr",
    text = {
      ...getTextDirectionStyle(direction),
      fontFamily:
        language === "fa"
          ? t.typography.fontFamily.bodyPersian
          : t.typography.fontFamily.bodyEnglish,
    };
  return (
    <View style={styles.stack}>
      {overviewCards(data, language).map((card) => (
        <Card
          key={card.tab}
          direction={direction}
          onPress={() => onSelect(card.tab)}
          accessibilityLabel={`${card.title} · ${card.value} · ${card.support}${card.extra ? " · " + card.extra : ""}`}
          style={styles.card}
        >
          <View style={styles.heading}>
            <Text style={[styles.title, text]}>{card.title}</Text>
            <Text style={styles.chevron}>{language === "fa" ? "‹" : "›"}</Text>
          </View>
          <View style={styles.row}>
            <View style={styles.copy}>
              <Text style={[styles.value, text]}>{card.value}</Text>
              <Text style={[styles.support, text]}>{card.support}</Text>
              {card.extra && (
                <Text style={[styles.extra, text]}>{card.extra}</Text>
              )}
            </View>
            <MiniTrend card={card} />
          </View>
        </Card>
      ))}
    </View>
  );
}
const createStyles = (t: FiticianTokens) => (StyleSheet.create({
  stack: { gap: 12 },
  card: { borderRadius: 22, padding: 18, backgroundColor: t.colors.surface },
  heading: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
    marginBottom: 10,
  },
  title: {
    color: t.colors.ink,
    fontSize: 15,
    fontWeight: "700",
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  chevron: {
    color: t.colors.muted,
    fontSize: 26,
    direction: "ltr",
    writingDirection: "ltr",
  },
  row: { flexDirection: "row", alignItems: "center", gap: 12 },
  copy: { flex: 1, gap: 6 },
  value: {
    color: t.colors.ink,
    fontSize: 21,
    fontWeight: "800",
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  support: {
    color: t.colors.muted,
    fontSize: 12,
    lineHeight: 20,
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  extra: {
    color: t.colors.muted,
    fontSize: 11,
    lineHeight: 19,
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
}));
