import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";
import {
  createMessageRequestId,
  createProgressApi,
  progressCopy,
  progressMetrics,
  progressSummary,
  goalLabels,
  recoveryLabels,
  difficultyLabels,
  resolvedIanaTimeZone,
  type BodyMetric,
  type ProgressOverview,
  type ProgressPreset,
  type MeasurementInput,
} from "@fitician/core";
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { useMobileEntitlements } from "../entitlements/EntitlementProvider";
import { Button } from "../ui/components/Button";
import { Card } from "../ui/components/Card";
import { DisclosureCard } from "../ui/components/DisclosureCard";
import { TextField } from "../ui/components/Input";
import { Screen } from "../ui/layout";
import { getTextDirectionStyle, languageForDirection } from "../ui/rtl";
import { fiticianTokens as tokens } from "../ui/tokens";
import { TrendChart } from "./TrendChart";
const AnalysisDetails = lazy(() =>
  import("../bodyAnalysis/BodyAnalysisHistoryScreen").then((m) => ({
    default: m.BodyAnalysisHistoryScreen,
  })),
);
export function ProgressScreen() {
  const auth = useMobileAuth(),
    access = useMobileEntitlements(),
    router = useRouter(),
    api = useMemo(() => createProgressApi(auth.request), [auth.request]),
    language = languageForDirection(),
    c = progressCopy[language],
    direction = language === "fa" ? "rtl" : "ltr",
    textStyle = getTextDirectionStyle(direction),
    identity = auth.user?.id;
  const [preset, setPreset] = useState<ProgressPreset>("week"),
    [data, setData] = useState<ProgressOverview | null>(null),
    [error, setError] = useState(false),
    [metric, setMetric] = useState<BodyMetric>("weight"),
    [dayIndex, setDayIndex] = useState<number | null>(null),
    [bodyIndex, setBodyIndex] = useState<number | null>(null),
    [recording, setRecording] = useState(false),
    [analysisOpen, setAnalysisOpen] = useState(false);
  const epoch = useRef(0);
  const load = useCallback(async () => {
    const current = ++epoch.current;
    setData(null);
    setError(false);
    if (!identity) return;
    try {
      const next = await api.overview(preset, resolvedIanaTimeZone());
      if (epoch.current === current) {
        setData(next);
        setDayIndex(null);
        setBodyIndex(null);
      }
    } catch {
      if (epoch.current === current) setError(true);
    }
  }, [api, preset, identity]);
  useEffect(() => {
    void load();
    return () => {
      epoch.current++;
    };
  }, [load]);
  const number = (v: number | null | undefined, signed = false) =>
    v == null
      ? "—"
      : new Intl.NumberFormat(language, {
          maximumFractionDigits: 1,
          signDisplay: signed ? "exceptZero" : "auto",
        }).format(v);
  const date = (v: string) =>
    new Intl.DateTimeFormat(language, {
      dateStyle: "medium",
      timeZone: v.length === 10 ? "UTC" : data?.context.timezone,
    }).format(new Date(v.length === 10 ? v + "T12:00:00Z" : v));
  const line = (value: string, key?: string) => (
    <Text key={key} style={[styles.text, textStyle]}>
      {value}
    </Text>
  );
  const heading = (value: string) => (
    <Text accessibilityRole="header" style={[styles.subtitle, textStyle]}>
      {value}
    </Text>
  );
  const nutrition = data?.nutrition,
    training = data?.training,
    body = data?.body_measurements[metric],
    latest = data?.recovery.at(-1);
  const chosenDay =
      dayIndex ??
      Math.max(
        0,
        nutrition?.series.findLastIndex((p) => p.date <= data!.context.today) ??
          0,
      ),
    calorieDay = nutrition?.series[chosenDay],
    bodyPoint = body?.points[bodyIndex ?? Math.max(0, body.points.length - 1)];
  const canAnalyze =
    !access.loading &&
    access.hasEntitlement("body_analysis.run") &&
    access.quotaFor("body_analysis.run")?.remaining !== 0;
  return (
    <Screen
      contentWidth="reading"
      keyboardAware
      contentContainerStyle={{ direction }}
    >
      <View style={styles.stack}>
        <Text accessibilityRole="header" style={[styles.title, textStyle]}>
          {c.title}
        </Text>
        <View style={[styles.row, { direction }]}>
          {(["week", "four_weeks", "current_program"] as const).map((range) => (
            <Button
              key={range}
              variant="ghost"
              label={c[range]}
              accessibilityState={{ selected: preset === range }}
              onPress={() => setPreset(range)}
            />
          ))}
        </View>
        {error ? (
          <Card direction={direction}>
            <Text accessibilityRole="alert" style={[styles.text, textStyle]}>
              {c.error}
            </Text>
            <Button label={c.retry} onPress={() => void load()} />
          </Card>
        ) : !data ? (
          <ActivityIndicator
            accessibilityLabel={c.loading}
            color={tokens.colors.aqua}
          />
        ) : (
          <>
            <Card variant="hero" direction={direction}>
              {line(
                data.context.goal
                  ? `${c.goal}: ${goalLabels[language][data.context.goal] ?? "—"}`
                  : c.title,
              )}
              {heading(c.hero)}
              {progressSummary(data, language)
                .slice(0, 2)
                .map((value) => line(value, value))}
              {data.context.week_number != null &&
                line(`${c.programWeek} ${number(data.context.week_number)}`)}
              {line(
                `${date(data.context.start_date)} — ${date(data.context.end_date)}`,
              )}
              {data.context.range_clipped && line(c.clipped)}
            </Card>
            <View style={[styles.metrics, { direction }]}>
              {training && (
                <Card style={styles.metric} direction={direction}>
                  {heading(c.training)}
                  <Text style={[styles.value, textStyle]}>
                    {number(training.completed_sessions)} /{" "}
                    {number(training.due_sessions)}
                  </Text>
                  {line(c.completed + " / " + c.due)}
                  {line(
                    c.adherence +
                      ": " +
                      (training.adherence_percent == null
                        ? "—"
                        : number(training.adherence_percent) + "%"),
                  )}
                </Card>
              )}
              {nutrition && (
                <Card style={styles.metric} direction={direction}>
                  {heading(c.nutrition)}
                  <Text style={[styles.value, textStyle]}>
                    {number(nutrition.logged_days)} /{" "}
                    {number(nutrition.elapsed_days)}
                  </Text>
                  {line(c.coverage)}
                  {line(
                    `${c.alignment}: ${number(nutrition.adherent_days)} / ${number(nutrition.comparable_days)}`,
                  )}
                </Card>
              )}
              <Card style={styles.metric} direction={direction}>
                {heading(c.weight)}
                <Text style={[styles.value, textStyle]}>
                  {number(data.body_measurements.weight.delta, true)} kg
                </Text>
                {line(
                  data.body_measurements.weight.delta == null
                    ? c.onePoint
                    : c.bodyTrend,
                )}
              </Card>
              {data.context.training_enabled && (
                <Card style={styles.metric} direction={direction}>
                  {heading(c.recovery)}
                  <Text style={[styles.value, textStyle]}>
                    {latest ? recoveryLabels[language][latest.recovery] : "—"}
                  </Text>
                  {line(latest ? date(latest.recorded_at) : c.noRecovery)}
                </Card>
              )}
            </View>
            <Card direction={direction}>
              {heading(c.bodyTrend)}
              <View style={[styles.row, { direction }]}>
                {progressMetrics.map((key) => (
                  <Button
                    key={key}
                    variant="ghost"
                    label={c[key]}
                    accessibilityState={{ selected: metric === key }}
                    onPress={() => {
                      setMetric(key);
                      setBodyIndex(null);
                    }}
                  />
                ))}
              </View>
              {body?.points.length ? (
                <>
                  <Text style={[styles.value, textStyle]}>
                    {number(body.start_value)} → {number(body.latest_value)}{" "}
                    {body.unit}
                  </Text>
                  {body.delta !== null &&
                    line(`${number(body.delta, true)} ${body.unit}`)}
                  <TrendChart
                    key={metric + preset}
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
                  {bodyPoint &&
                    line(
                      `${date(bodyPoint.recorded_at)} · ${number(bodyPoint.value)} ${body.unit} · ${bodyPoint.source === "manual" ? c.manual : c.legacy}`,
                    )}
                  {body.points.length === 1 && line(c.onePoint)}
                  <View style={[styles.row, { direction }]}>
                    <Button
                      variant="ghost"
                      label={language === "fa" ? "ثبت قبلی" : "Previous record"}
                      disabled={(bodyIndex ?? body.points.length - 1) <= 0}
                      onPress={() =>
                        setBodyIndex(
                          Math.max(
                            0,
                            (bodyIndex ?? body.points.length - 1) - 1,
                          ),
                        )
                      }
                    />
                    <Button
                      variant="ghost"
                      label={language === "fa" ? "ثبت بعدی" : "Next record"}
                      disabled={
                        (bodyIndex ?? body.points.length - 1) >=
                        body.points.length - 1
                      }
                      onPress={() =>
                        setBodyIndex(
                          Math.min(
                            body.points.length - 1,
                            (bodyIndex ?? body.points.length - 1) + 1,
                          ),
                        )
                      }
                    />
                  </View>
                </>
              ) : (
                line(
                  metric === "weight"
                    ? c.noBody
                    : language === "fa"
                      ? `هنوز اندازه‌ای برای ${c[metric]} ثبت نشده است.`
                      : `No ${c[metric].toLowerCase()} records yet.`,
                )
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
                    void load();
                  }}
                />
              )}
            </Card>
            {nutrition && (
              <Card direction={direction}>
                {heading(c.calories)}
                {line(
                  `${c.coverage}: ${number(nutrition.logged_days)} / ${number(nutrition.elapsed_days)}`,
                )}
                {line(
                  `${c.alignment}: ${number(nutrition.adherent_days)} / ${number(nutrition.comparable_days)}`,
                )}
                {line(
                  `${c.averageDifference}: ${number(nutrition.average_difference_kcal, true)} kcal`,
                )}
                {!nutrition.series.some((p) => p.actual_kcal !== null) &&
                  line(c.noNutrition)}
                <TrendChart
                  key={preset}
                  series={[
                    nutrition.series.map((p) => ({
                      date: p.date,
                      value: p.target_kcal,
                    })),
                    nutrition.series.map((p) => ({
                      date: p.date,
                      value: p.actual_kcal,
                    })),
                  ]}
                  labels={[c.target, c.actual]}
                  unit="kcal"
                  language={language}
                  onSelect={setDayIndex}
                />
                {calorieDay && (
                  <View style={styles.point}>
                    {heading(date(calorieDay.date))}
                    {calorieDay.in_progress && line(c.inProgress)}
                    {line(
                      `${c.target}: ${calorieDay.target_kcal == null ? c.missingTarget : number(calorieDay.target_kcal) + " kcal"}`,
                    )}
                    {line(
                      calorieDay.actual_kcal == null
                        ? c.noIntake
                        : `${c.actual}: ${number(calorieDay.actual_kcal)} kcal`,
                    )}
                    {calorieDay.actual_kcal != null &&
                      calorieDay.target_kcal != null &&
                      line(
                        `${c.difference}: ${number(calorieDay.actual_kcal - calorieDay.target_kcal, true)} kcal`,
                      )}
                  </View>
                )}
                <View style={[styles.row, { direction }]}>
                  <Button
                    variant="ghost"
                    disabled={chosenDay <= 0}
                    label={language === "fa" ? "روز قبل" : "Previous day"}
                    onPress={() => setDayIndex(Math.max(0, chosenDay - 1))}
                  />
                  <Button
                    variant="ghost"
                    disabled={chosenDay >= nutrition.series.length - 1}
                    label={language === "fa" ? "روز بعد" : "Next day"}
                    onPress={() =>
                      setDayIndex(
                        Math.min(nutrition.series.length - 1, chosenDay + 1),
                      )
                    }
                  />
                </View>
                <DisclosureCard direction={direction} title={c.details}>
                  {line(c.nutritionRule)}
                </DisclosureCard>
              </Card>
            )}
            {training && (
              <DisclosureCard
                direction={direction}
                title={c.training}
                summary={`${c.completed}: ${number(training.completed_sessions)} / ${number(training.due_sessions)}`}
              >
                {line(c.trainingRule)}
                {line(
                  `${c.planned}: ${number(training.planned_sessions)} · ${c.skipped}: ${number(training.skipped_sessions)} · ${c.overdue}: ${number(training.overdue_sessions)}`,
                )}
                {training.rescheduled_sessions != null &&
                  line(
                    `${c.rescheduled}: ${number(training.rescheduled_sessions)}`,
                  )}
                {training.weeks.map((w) => (
                  <View key={w.start_date} style={styles.stack}>
                    {line(
                      `${date(w.start_date)} · ${number(w.completed)} / ${number(w.planned)} ${c.completed} / ${c.planned}`,
                    )}
                    <View style={styles.bar}>
                      <View
                        style={[
                          styles.barComplete,
                          {
                            width: `${(w.completed / Math.max(w.planned, 1)) * 100}%`,
                          },
                        ]}
                      />
                    </View>
                  </View>
                ))}
                {!training.planned_sessions && line(c.noTraining)}
              </DisclosureCard>
            )}
            {data.context.training_enabled && (
              <DisclosureCard
                direction={direction}
                title={c.recovery}
                summary={
                  latest
                    ? recoveryLabels[language][latest.recovery]
                    : c.noRecovery
                }
              >
                {!latest ? (
                  line(c.noRecovery)
                ) : (
                  <>
                    {line(
                      `${c.difficulty}: ${difficultyLabels[language][latest.difficulty]}`,
                    )}
                    {data.recovery.length > 1 && (
                      <TrendChart
                        series={[
                          data.recovery.map((p) => ({
                            date: p.recorded_at,
                            value: { poor: 1, average: 2, good: 3 }[p.recovery],
                          })),
                        ]}
                        labels={[c.recovery]}
                        unit=""
                        language={language}
                      />
                    )}
                    {data.recovery.map((p) =>
                      line(
                        `${date(p.recorded_at)} · ${recoveryLabels[language][p.recovery]} · ${difficultyLabels[language][p.difficulty]}`,
                        p.recorded_at,
                      ),
                    )}
                  </>
                )}
              </DisclosureCard>
            )}
            <Card direction={direction}>
              {heading(c.analysis)}
              {line(
                data.body_analysis?.latest_at
                  ? date(data.body_analysis.latest_at)
                  : c.noAnalysis,
              )}
              <Button
                variant="secondary"
                label={c.analysisHistory}
                onPress={() => router.push("/member/body-analysis-history")}
              />
              <Button
                variant="ghost"
                label={c.newAnalysis}
                onPress={() =>
                  router.push(
                    canAnalyze
                      ? "/member/body-analysis-capture"
                      : "/member/plans",
                  )
                }
              />
              <DisclosureCard
                direction={direction}
                title={c.analysisHistory}
                onExpandedChange={setAnalysisOpen}
              >
                {analysisOpen && (
                  <Suspense
                    fallback={<ActivityIndicator color={tokens.colors.aqua} />}
                  >
                    <AnalysisDetails embedded />
                  </Suspense>
                )}
              </DisclosureCard>
            </Card>
            <DisclosureCard direction={direction} title={c.insights}>
              {progressSummary(data, language).map((value) =>
                line(value, value),
              )}
              {line(c.legacyBody)}
            </DisclosureCard>
          </>
        )}
      </View>
    </Screen>
  );
}
function MeasurementForm({
  language,
  api,
  onSaved,
}: {
  language: "fa" | "en";
  api: ReturnType<typeof createProgressApi>;
  onSaved: () => void;
}) {
  const c = progressCopy[language],
    [values, setValues] = useState<Record<BodyMetric, string>>({
      weight: "",
      waist: "",
      hip: "",
      shoulder_width: "",
    }),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(false),
    pending = useRef<{ key: string; id: string } | null>(null),
    sending = useRef(false);
  async function save() {
    if (sending.current) return;
    const fields = {
      weight: "weight_kg",
      waist: "waist_circumference_cm",
      hip: "hip_circumference_cm",
      shoulder_width: "shoulder_width_cm",
    } as const;
    const entered = Object.fromEntries(
      progressMetrics
        .filter((k) => values[k].trim() !== "")
        .map((k) => [
          fields[k],
          Number(
            values[k]
              .replace(/[۰-۹]/g, (x) => String(x.charCodeAt(0) - 1776))
              .replace(/[٠-٩]/g, (x) => String(x.charCodeAt(0) - 1632))
              .replace("٫", "."),
          ),
        ]),
    );
    if (
      !Object.keys(entered).length ||
      Object.values(entered).some((v) => !Number.isFinite(v))
    ) {
      setError(true);
      return;
    }
    const key = JSON.stringify(entered);
    if (pending.current?.key !== key)
      pending.current = { key, id: createMessageRequestId() };
    sending.current = true;
    setBusy(true);
    setError(false);
    try {
      await api.recordMeasurement({
        ...entered,
        request_id: pending.current.id,
      } as MeasurementInput);
      onSaved();
    } catch {
      setError(true);
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  return (
    <View style={styles.stack}>
      <Text style={styles.text}>{c.measurementHint}</Text>
      {progressMetrics.map((metric) => (
        <TextField
          key={metric}
          label={`${c[metric]} (${metric === "weight" ? "kg" : "cm"})`}
          keyboardType="decimal-pad"
          value={values[metric]}
          editable={!busy}
          onChangeText={(value) =>
            setValues((prev) => ({ ...prev, [metric]: value }))
          }
        />
      ))}
      {error && (
        <Text accessibilityRole="alert" style={styles.text}>
          {c.recordError}
        </Text>
      )}
      <Button
        label={c.save}
        loading={busy}
        disabled={!Object.values(values).some(Boolean)}
        onPress={() => void save()}
      />
    </View>
  );
}
const styles = StyleSheet.create({
  stack: { gap: 16, paddingBottom: 16 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  metrics: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  metric: { flexGrow: 1, flexBasis: "45%", minWidth: 120 },
  title: {
    color: tokens.colors.ink,
    fontSize: 25,
    fontWeight: "800",
    fontFamily: tokens.typography.fontFamily.bodyPersian,
  },
  subtitle: {
    color: tokens.colors.ink,
    fontSize: 17,
    fontWeight: "700",
    fontFamily: tokens.typography.fontFamily.bodyPersian,
  },
  value: {
    color: tokens.colors.ink,
    fontSize: 23,
    fontWeight: "800",
    fontFamily: tokens.typography.fontFamily.bodyPersian,
  },
  text: {
    color: tokens.colors.muted,
    fontSize: 13,
    lineHeight: 24,
    fontFamily: tokens.typography.fontFamily.bodyPersian,
  },
  point: {
    backgroundColor: tokens.colors.surfaceSubtle,
    padding: 14,
    borderRadius: tokens.radii.medium,
    gap: 6,
  },
  bar: {
    height: 10,
    borderRadius: 5,
    backgroundColor: tokens.colors.lineStrong,
    direction: "ltr",
  },
  barComplete: {
    height: 10,
    borderRadius: 5,
    backgroundColor: tokens.colors.aqua,
  },
});
