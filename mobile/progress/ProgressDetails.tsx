import { useThemeTokens, useThemeStyles } from "../ui/theme/ThemeProvider";
import type { FiticianTokens } from "../ui/tokens";
import { useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import {
  calorieSeries,
  difficultyLabels,
  progressCopy,
  progressCount,
  progressDate,
  progressMetrics,
  progressNumber,
  progressQuantity,
  progressPresentationCopy,
  recoveryLabels,
  recoverySeries,
  selfReportedProgressLabels,
  type BodyMetric,
  type createProgressApi,
  type ProgressOverview,
  type ProgressTab,
} from "@fitician/core";
import { Button } from "../ui/components/Button";
import { Card } from "../ui/components/Card";
import { DisclosureCard } from "../ui/components/DisclosureCard";
import { getTextDirectionStyle } from "../ui/rtl";
import { TrendChart } from "./TrendChart";
import { MeasurementForm } from "./MeasurementForm";
type Props = {
  tab: ProgressTab;
  data: ProgressOverview;
  language: "fa" | "en";
  api: ReturnType<typeof createProgressApi>;
  onSaved: () => void;
};
export default function ProgressDetails({
  tab,
  data,
  language,
  api,
  onSaved,
}: Props) {
  const t = useThemeTokens();
  const styles = useThemeStyles(createStyles);

  const c = progressCopy[language],
    p = progressPresentationCopy[language],
    n = (v: number | null | undefined, signed = false) =>
      progressNumber(v, language, signed),
    date = (v: string) => progressDate(v, language, data.context.timezone),
    direction = language === "fa" ? "rtl" : "ltr",
    text = {
      ...getTextDirectionStyle(direction),
      fontFamily:
        language === "fa"
          ? t.typography.fontFamily.bodyPersian
          : t.typography.fontFamily.bodyEnglish,
    };
  const [metric, setMetric] = useState<BodyMetric>("weight"),
    [bodyIndex, setBodyIndex] = useState<number | null>(null),
    [dayIndex, setDayIndex] = useState<number | null>(null),
    [recording, setRecording] = useState(false);
  const line = (v: string) => <Text style={[styles.text, text]}>{v}</Text>;
  const heading = (v: string) => (
    <Text accessibilityRole="header" style={[styles.heading, text]}>
      {v}
    </Text>
  );
  const stat = (label: string, value: string) => (
    <View style={styles.stat}>
      {line(label)}
      <Text style={[styles.value, text]}>{value}</Text>
    </View>
  );
  if (tab === "body") {
    const body = data.body_measurements[metric],
      point = body.points[bodyIndex ?? body.points.length - 1];
    return (
      <Card direction={direction}>
        <View style={styles.stack}>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={[styles.metricRow, { direction }]}
          >
            {progressMetrics.map((key) => (
              <Button
                key={key}
                label={c[key]}
                variant={metric === key ? "secondary" : "ghost"}
                accessibilityState={{ selected: metric === key }}
                onPress={() => {
                  setMetric(key);
                  setBodyIndex(null);
                }}
              />
            ))}
          </ScrollView>
          {heading(c[metric])}
          {body.points.length ? (
            <>
              <Text style={[styles.mainValue, text]}>
                {progressQuantity(body.latest_value, body.unit, language)}
              </Text>
              {body.points.length > 1 &&
                body.delta !== null &&
                line(
                  `${progressQuantity(body.delta, body.unit, language, true)} · ${c[data.context.preset]}`,
                )}
              {body.points.length > 1 ? (
                <TrendChart
                  key={metric}
                  series={[
                    body.points.map((p) => ({
                      date: p.recorded_at,
                      value: p.value,
                    })),
                  ]}
                  labels={[c[metric]]}
                  unit={body.unit}
                  language={language}
                  onSelect={setBodyIndex}
                />
              ) : (
                line(c.onePoint)
              )}
              {point && (
                <View style={styles.point}>
                  {line(
                    `${date(point.recorded_at)} · ${n(point.value)} ${body.unit} · ${point.source === "manual" ? c.manual : c.legacy}`,
                  )}
                </View>
              )}
            </>
          ) : (
            line(c.noBody)
          )}
          <Button
            variant="secondary"
            label={recording ? c.close : c.record}
            onPress={() => setRecording(!recording)}
          />
          {recording && (
            <MeasurementForm
              language={language}
              api={api}
              onSaved={() => {
                setRecording(false);
                onSaved();
              }}
            />
          )}
          <DisclosureCard direction={direction} title={c.details}>
            {line(c.legacyBody)}
          </DisclosureCard>
        </View>
      </Card>
    );
  }
  if (tab === "calories" && data.nutrition) {
    const nutrition = data.nutrition,
      day =
        nutrition.series[
          dayIndex ??
            Math.max(
              0,
              nutrition.series.findLastIndex(
                (p) => p.date <= data.context.today,
              ),
            )
        ];
    return (
      <Card direction={direction}>
        <View style={styles.stack}>
          {heading(p.caloriesTitle)}
          {stat(
            c.coverage,
            progressCount(
              nutrition.logged_days,
              nutrition.elapsed_days,
              language,
              "days",
            ),
          )}
          <View style={styles.row}>
            {stat(c.alignment, n(nutrition.adherent_days))}
            {stat(
              p.averageDifference,
              `${n(nutrition.average_difference_kcal, true)} kcal`,
            )}
          </View>
          <TrendChart
            series={calorieSeries(nutrition)}
            labels={[c.target, c.actual]}
            unit="kcal"
            language={language}
            onSelect={setDayIndex}
          />
          {day && (
            <View style={styles.point} accessibilityLiveRegion="polite">
              {line(
                date(day.date) + (day.in_progress ? " · " + c.inProgress : ""),
              )}
              {line(
                `${c.target}: ${day.target_kcal == null ? c.missingTarget : n(day.target_kcal) + " kcal"}`,
              )}
              {line(
                day.actual_kcal == null
                  ? day.logging_state === "invalid"
                    ? c.invalidIntake
                    : c.noIntake
                  : `${c.actual}: ${n(day.actual_kcal)} kcal`,
              )}
              {day.target_kcal != null &&
                day.actual_kcal != null &&
                line(`${n(day.actual_kcal - day.target_kcal, true)} kcal`)}
            </View>
          )}
          <DisclosureCard direction={direction} title={c.details}>
            {line(c.nutritionRule)}
          </DisclosureCard>
        </View>
      </Card>
    );
  }
  if (tab === "training" && data.training) {
    const training = data.training,
      max = Math.max(
        1,
        ...training.weeks.flatMap((w) => [w.planned, w.completed]),
      );
    return (
      <Card direction={direction}>
        <View style={styles.stack}>
          {heading(c.training)}
          <View style={styles.row}>
            {stat(
              p.completed,
              progressCount(
                training.completed_sessions,
                training.due_sessions,
                language,
                "sessions",
              ),
            )}
            {stat(
              p.adherence,
              training.adherence_percent == null
                ? "—"
                : n(training.adherence_percent) + "%",
            )}
          </View>
          {!training.planned_sessions ? (
            line(c.noTraining)
          ) : (
            <>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.trainingChart}
              >
                {training.weeks.map((w) => (
                  <View
                    key={w.start_date}
                    style={styles.week}
                    accessible
                    accessibilityLabel={`${date(w.start_date)}: ${p.planned} ${n(w.planned)}, ${p.completed} ${n(w.completed)}`}
                  >
                    <View style={styles.bars}>
                      <View
                        style={[
                          styles.plannedBar,
                          { height: (w.planned / max) * 125 },
                        ]}
                      />
                      <View
                        style={[
                          styles.completedBar,
                          { height: (w.completed / max) * 125 },
                        ]}
                      />
                    </View>
                    {line(`${n(w.completed)} / ${n(w.planned)}`)}
                    {line(date(w.start_date))}
                  </View>
                ))}
              </ScrollView>
              <View style={styles.row}>
                {line(`▥ ${p.planned}`)}
                <Text style={[styles.text, text, { color: t.colors.accentInk }]}>
                  ▥ {p.completed}
                </Text>
              </View>
            </>
          )}
          <View style={styles.row}>
            {line(`${p.skipped} ${n(training.skipped_sessions)}`)}
            {line(`${p.rescheduled} ${n(training.rescheduled_sessions)}`)}
            {line(`${p.overdue} ${n(training.overdue_sessions)}`)}
          </View>
          <DisclosureCard direction={direction} title={c.details}>
            {line(c.trainingRule)}
            {training.self_reported_cycle_progress &&
              line(
                `${c.selfReported}: ${selfReportedProgressLabels[language][training.self_reported_cycle_progress]}`,
              )}
          </DisclosureCard>
        </View>
      </Card>
    );
  }
  if (tab === "recovery") {
    const latest = data.recovery.at(-1);
    return (
      <Card direction={direction}>
        <View style={styles.stack}>
          {heading(c.recovery)}
          {latest ? (
            <>
              <View style={styles.row}>
                {stat(c.recovery, recoveryLabels[language][latest.recovery])}
                {stat(
                  p.difficulty,
                  difficultyLabels[language][latest.difficulty],
                )}
              </View>
              {data.recovery.length > 1 && (
                <TrendChart
                  series={recoverySeries(data)}
                  labels={[c.recovery]}
                  unit=""
                  language={language}
                  valueLabels={{
                    1: recoveryLabels[language].poor,
                    2: recoveryLabels[language].average,
                    3: recoveryLabels[language].good,
                  }}
                />
              )}
              {data.recovery
                .slice()
                .reverse()
                .map((r, i) => (
                  <View key={r.recorded_at + i} style={styles.historyRow}>
                    {line(date(r.recorded_at))}
                    {line(recoveryLabels[language][r.recovery])}
                    {line(difficultyLabels[language][r.difficulty])}
                  </View>
                ))}
            </>
          ) : (
            line(p.noRecovery)
          )}
        </View>
      </Card>
    );
  }
  return line(p.notAvailable);
}
const createStyles = (t: FiticianTokens) => (StyleSheet.create({
  stack: { gap: 16 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 16 },
  metricRow: { flexDirection: "row", gap: 4 },
  stat: { flexGrow: 1, gap: 6 },
  heading: {
    color: t.colors.ink,
    fontSize: 17,
    fontWeight: "700",
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  text: {
    color: t.colors.muted,
    fontSize: 12,
    lineHeight: 22,
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  value: {
    color: t.colors.ink,
    fontSize: 22,
    fontWeight: "800",
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  mainValue: {
    color: t.colors.ink,
    fontSize: 30,
    fontWeight: "800",
    fontFamily: t.typography.fontFamily.bodyPersian,
  },
  point: {
    backgroundColor: t.colors.surfaceRaised,
    borderRadius: 12,
    padding: 12,
    gap: 4,
  },
  trainingChart: {
    flexDirection: "row",
    direction: "ltr",
    gap: 24,
    paddingVertical: 12,
  },
  week: { alignItems: "center", minWidth: 85, gap: 8 },
  bars: {
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "center",
    gap: 6,
    height: 125,
    borderBottomWidth: 1,
    borderBottomColor: t.colors.line,
    width: "100%",
  },
  plannedBar: {
    width: 22,
    borderTopLeftRadius: 7,
    borderTopRightRadius: 7,
    backgroundColor: t.colors.line,
  },
  completedBar: {
    width: 22,
    borderTopLeftRadius: 7,
    borderTopRightRadius: 7,
    backgroundColor: t.colors.aqua,
  },
  historyRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: t.colors.line,
  },
}));
