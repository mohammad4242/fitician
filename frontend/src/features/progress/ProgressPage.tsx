import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  createMessageRequestId,
  progressCopy,
  progressMetrics,
  progressSummary,
  goalLabels,
  recoveryLabels,
  difficultyLabels,
  resolvedIanaTimeZone,
  type BodyMetric,
  type MeasurementInput,
  type ProgressOverview,
  type ProgressPreset,
} from "@fitician/core";
import { useAuth } from "../auth/AuthContext";
import { useEntitlements } from "../entitlements/EntitlementContext";
import { progressApi as api } from "./api";
import { TrendChart } from "./TrendChart";
import "./progress.css";
const AnalysisDetails = lazy(() =>
  import("../bodyPhotos/BodyProgressPage").then((m) => ({
    default: m.BodyProgressPage,
  })),
);
export function ProgressPage() {
  const { i18n, t } = useTranslation(),
    language = i18n.resolvedLanguage === "en" ? "en" : "fa",
    c = progressCopy[language],
    { user } = useAuth(),
    access = useEntitlements();
  const [preset, setPreset] = useState<ProgressPreset>("week"),
    [data, setData] = useState<ProgressOverview | null>(null),
    [error, setError] = useState(false),
    [metric, setMetric] = useState<BodyMetric>("weight"),
    [dayIndex, setDayIndex] = useState<number | null>(null),
    [bodyIndex, setBodyIndex] = useState<number | null>(null),
    [recording, setRecording] = useState(false),
    [analysisOpen, setAnalysisOpen] = useState(false);
  const epoch = useRef(0);
  const identity = user?.id;
  const load = useCallback(async () => {
    const current = ++epoch.current;
    setError(false);
    setData(null);
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
  }, [preset, identity]);
  useEffect(() => {
    void load();
    return () => {
      // Invalidate pending responses after navigation.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      epoch.current++;
    };
  }, [load]);
  const number = (value: number | null | undefined, signed = false) =>
    value == null
      ? "—"
      : new Intl.NumberFormat(language, {
          maximumFractionDigits: 1,
          signDisplay: signed ? "exceptZero" : "auto",
        }).format(value);
  const date = (value: string) =>
    new Intl.DateTimeFormat(language, {
      dateStyle: "medium",
      timeZone: value.length === 10 ? "UTC" : data?.context.timezone,
    }).format(new Date(value.length === 10 ? value + "T12:00:00Z" : value));
  const series = data?.body_measurements[metric],
    nutrition = data?.nutrition,
    training = data?.training,
    latest = data?.recovery.at(-1);
  const calorieDay =
    nutrition?.series[
      dayIndex ??
        Math.max(
          0,
          nutrition.series.findLastIndex((p) => p.date <= data!.context.today),
        )
    ];
  const bodyPoint =
    series?.points[bodyIndex ?? Math.max(0, series.points.length - 1)];
  const canAnalyze =
    !access.loading &&
    access.hasEntitlement("body_analysis.run") &&
    access.quotaFor("body_analysis.run")?.remaining !== 0;
  return (
    <main
      className="progress-page fitician-page"
      dir={language === "fa" ? "rtl" : "ltr"}
    >
      <header className="progress-heading">
        <h1>{c.title}</h1>
        <div className="progress-ranges" aria-label={c.title}>
          {(["week", "four_weeks", "current_program"] as const).map((range) => (
            <button
              key={range}
              aria-pressed={preset === range}
              onClick={() => setPreset(range)}
            >
              {c[range]}
            </button>
          ))}
        </div>
      </header>
      {error ? (
        <div role="alert" className="progress-card">
          <p>{c.error}</p>
          <button onClick={() => void load()}>{c.retry}</button>
        </div>
      ) : !data ? (
        <div role="status" className="progress-skeleton">
          {c.loading}
        </div>
      ) : (
        <>
          <section className="progress-hero">
            <div>
              <span>
                {data.context.goal
                  ? `${c.goal}: ${goalLabels[language][data.context.goal] ?? "—"}`
                  : c.title}
              </span>
              <h2>{c.hero}</h2>
              {progressSummary(data, language)
                .slice(0, 2)
                .map((line) => (
                  <p key={line}>{line}</p>
                ))}
            </div>
            <aside>
              <span>
                {data.context.current_program_id ? c.program : c.title}
              </span>
              {data.context.week_number != null && (
                <strong>
                  {c.programWeek} {number(data.context.week_number)}
                </strong>
              )}
              <time>
                {date(data.context.start_date)} — {date(data.context.end_date)}
              </time>
              {data.context.range_clipped && <small>{c.clipped}</small>}
            </aside>
          </section>
          <section className="progress-metrics" aria-label={c.hero}>
            {training && (
              <article className="progress-card">
                <span>{c.training}</span>
                <strong>
                  {number(training.completed_sessions)} /{" "}
                  {number(training.due_sessions)}
                </strong>
                <small>
                  {c.completed} / {c.due}
                </small>
                <p>
                  {c.adherence}:{" "}
                  {training.adherence_percent == null
                    ? "—"
                    : number(training.adherence_percent) + "%"}
                </p>
              </article>
            )}
            {nutrition && (
              <article className="progress-card">
                <span>{c.nutrition}</span>
                <strong>
                  {number(nutrition.logged_days)} /{" "}
                  {number(nutrition.elapsed_days)}
                </strong>
                <small>
                  {c.coverage} /{" "}
                  {language === "fa" ? "روزهای پایان‌یافته" : "completed days"}
                </small>
                <p>
                  {c.alignment}: {number(nutrition.adherent_days)} /{" "}
                  {number(nutrition.comparable_days)}
                </p>
              </article>
            )}
            <article className="progress-card">
              <span>{c.weight}</span>
              <strong>
                {number(data.body_measurements.weight.delta, true)}{" "}
                <small>kg</small>
              </strong>
              <small>
                {data.body_measurements.weight.delta == null
                  ? c.onePoint
                  : date(data.context.start_date) +
                    " — " +
                    date(data.context.end_date)}
              </small>
            </article>
            {data.context.training_enabled && (
              <article className="progress-card">
                <span>{c.recovery}</span>
                <strong>
                  {latest ? recoveryLabels[language][latest.recovery] : "—"}
                </strong>
                <small>
                  {latest ? date(latest.recorded_at) : c.noRecovery}
                </small>
              </article>
            )}
          </section>
          <section className="progress-card progress-body">
            <div className="progress-section-heading">
              <h2>{c.bodyTrend}</h2>
              <button onClick={() => setRecording(!recording)}>
                {recording ? c.close : c.record}
              </button>
            </div>
            {recording && (
              <MeasurementForm
                language={language}
                onSaved={() => {
                  setRecording(false);
                  void load();
                }}
              />
            )}
            <div className="progress-ranges">
              {progressMetrics.map((key) => (
                <button
                  key={key}
                  aria-pressed={metric === key}
                  onClick={() => {
                    setMetric(key);
                    setBodyIndex(null);
                  }}
                >
                  {c[key]}
                </button>
              ))}
            </div>
            {series && series.points.length ? (
              <>
                <div className="progress-value">
                  <strong>
                    {number(series.start_value)} → {number(series.latest_value)}{" "}
                    <small>{series.unit}</small>
                  </strong>
                  {series.delta !== null && (
                    <span>
                      {number(series.delta, true)} {series.unit}
                    </span>
                  )}
                </div>
                <TrendChart
                  key={metric + preset}
                  series={[
                    series.points.map((p) => ({
                      date: p.recorded_at,
                      value: p.value,
                    })),
                  ]}
                  labels={[c[metric]]}
                  unit={series.unit}
                  language={language}
                  onSelect={setBodyIndex}
                />
                {bodyPoint && (
                  <p className="progress-point" aria-live="polite">
                    {date(bodyPoint.recorded_at)} · {number(bodyPoint.value)}{" "}
                    {series.unit} ·{" "}
                    {bodyPoint.source === "manual" ? c.manual : c.legacy}
                  </p>
                )}
                {series.points.length === 1 && <p>{c.onePoint}</p>}
              </>
            ) : (
              <p className="progress-empty">
                {metric === "weight"
                  ? c.noBody
                  : language === "fa"
                    ? `هنوز اندازه‌ای برای ${c[metric]} ثبت نشده است.`
                    : `No ${c[metric].toLowerCase()} records yet.`}
              </p>
            )}
          </section>
          {nutrition && (
            <section className="progress-card">
              <h2>{c.calories}</h2>
              <div className="progress-nutrition-summary">
                <strong>
                  {c.coverage}: {number(nutrition.logged_days)} /{" "}
                  {number(nutrition.elapsed_days)}
                </strong>
                <span>
                  {c.alignment}: {number(nutrition.adherent_days)} /{" "}
                  {number(nutrition.comparable_days)}
                </span>
                <span>
                  {c.averageDifference}:{" "}
                  {number(nutrition.average_difference_kcal, true)} kcal
                </span>
              </div>
              {!nutrition.series.some((p) => p.actual_kcal !== null) && (
                <p>{c.noNutrition}</p>
              )}
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
                <div className="progress-point" aria-live="polite">
                  <strong>
                    {date(calorieDay.date)}
                    {calorieDay.in_progress ? " · " + c.inProgress : ""}
                  </strong>
                  <span>
                    {c.target}:{" "}
                    {calorieDay.target_kcal == null
                      ? c.missingTarget
                      : number(calorieDay.target_kcal) + " kcal"}
                  </span>
                  <span>
                    {calorieDay.actual_kcal == null
                      ? c.noIntake
                      : `${c.actual}: ${number(calorieDay.actual_kcal)} kcal`}
                  </span>
                  {calorieDay.actual_kcal != null &&
                    calorieDay.target_kcal != null && (
                      <span>
                        {c.difference}:{" "}
                        {number(
                          calorieDay.actual_kcal - calorieDay.target_kcal,
                          true,
                        )}{" "}
                        kcal
                      </span>
                    )}
                </div>
              )}
              <label className="progress-day-selector">
                {language === "fa" ? "انتخاب روز" : "Choose a day"}
                <input
                  type="range"
                  min={0}
                  max={Math.max(0, nutrition.series.length - 1)}
                  value={
                    dayIndex ??
                    Math.max(
                      0,
                      nutrition.series.findLastIndex(
                        (p) => p.date <= data.context.today,
                      ),
                    )
                  }
                  onChange={(e) => setDayIndex(Number(e.target.value))}
                />
              </label>
              <details>
                <summary>{c.details}</summary>
                <p>{c.nutritionRule}</p>
              </details>
            </section>
          )}
          <div className="progress-secondary">
            {training && (
              <section className="progress-card">
                <h2>{c.training}</h2>
                {!training.planned_sessions ? (
                  <p>{c.noTraining}</p>
                ) : (
                  <>
                    <div className="progress-nutrition-summary">
                      <span>
                        {c.planned}: {number(training.planned_sessions)}
                      </span>
                      <span>
                        {c.skipped}: {number(training.skipped_sessions)}
                      </span>
                      <span>
                        {c.overdue}: {number(training.overdue_sessions)}
                      </span>
                      {training.rescheduled_sessions != null && (
                        <span>
                          {c.rescheduled}:{" "}
                          {number(training.rescheduled_sessions)}
                        </span>
                      )}
                    </div>
                    <div className="progress-week-bars">
                      {training.weeks.map((w) => (
                        <div key={w.start_date}>
                          <span>{date(w.start_date)}</span>
                          <div>
                            <span
                              className="progress-week-bars__planned"
                              style={{
                                width: `${(w.planned / Math.max(...training.weeks.map((x) => x.planned), 1)) * 100}%`,
                              }}
                            />
                            <span
                              className="progress-week-bars__completed"
                              style={{
                                width: `${(w.completed / Math.max(...training.weeks.map((x) => x.planned), 1)) * 100}%`,
                              }}
                            />
                          </div>
                          <b>
                            {number(w.completed)} / {number(w.planned)}
                          </b>
                        </div>
                      ))}
                    </div>
                    <p>
                      {c.completed} / {c.planned}
                    </p>
                  </>
                )}
                <details>
                  <summary>{c.details}</summary>
                  <p>{c.trainingRule}</p>
                  {training.self_reported_cycle_progress && (
                    <p>
                      {c.selfReported}:{" "}
                      {t(
                        `workoutCycle.feedbackOptions.progress.${training.self_reported_cycle_progress}`,
                        training.self_reported_cycle_progress,
                      )}
                    </p>
                  )}
                </details>
              </section>
            )}
            {data.context.training_enabled && (
              <section className="progress-card">
                <h2>{c.recovery}</h2>
                {!latest ? (
                  <p>{c.noRecovery}</p>
                ) : (
                  <>
                    <strong>{recoveryLabels[language][latest.recovery]}</strong>
                    <p>
                      {c.difficulty}:{" "}
                      {difficultyLabels[language][latest.difficulty]}
                    </p>
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
                    <details>
                      <summary>{c.details}</summary>
                      {data.recovery.map((p) => (
                        <p key={p.recorded_at}>
                          {date(p.recorded_at)} ·{" "}
                          {recoveryLabels[language][p.recovery]} ·{" "}
                          {difficultyLabels[language][p.difficulty]}
                        </p>
                      ))}
                    </details>
                  </>
                )}
              </section>
            )}
          </div>
          <section className="progress-card">
            <h2>{c.analysis}</h2>
            {data.body_analysis?.latest_at ? (
              <p>
                {date(data.body_analysis.latest_at)} ·{" "}
                {t(
                  `bodyPhotos.results.analysisStatus.${data.body_analysis.latest_status}`,
                  data.body_analysis.latest_status ?? "",
                )}
              </p>
            ) : (
              <p>{c.noAnalysis}</p>
            )}
            <div className="progress-ranges">
              <Link to="/body-progress">{c.analysisHistory}</Link>
              {canAnalyze ? (
                <Link to="/body-progress/new">{c.newAnalysis}</Link>
              ) : (
                <Link to="/plans">{c.newAnalysis}</Link>
              )}
            </div>
            <details onToggle={(e) => setAnalysisOpen(e.currentTarget.open)}>
              <summary>{c.analysisHistory}</summary>
              {analysisOpen && (
                <Suspense fallback={<p>{c.loading}</p>}>
                  <AnalysisDetails embedded />
                </Suspense>
              )}
            </details>
          </section>
          <section className="progress-card">
            <h2>{c.insights}</h2>
            <ul>
              {progressSummary(data, language).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            <details>
              <summary>{c.details}</summary>
              <p>{c.legacyBody}</p>
            </details>
          </section>
        </>
      )}
    </main>
  );
}
function MeasurementForm({
  language,
  onSaved,
}: {
  language: "fa" | "en";
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
        .filter((k) => values[k] !== "")
        .map((k) => [fields[k], Number(values[k])]),
    );
    if (!Object.keys(entered).length) return;
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
    <form
      className="progress-measurement-form"
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <p>{c.measurementHint}</p>
      {progressMetrics.map((metric) => (
        <label key={metric}>
          {c[metric]} ({metric === "weight" ? "kg" : "cm"})
          <input
            type="number"
            inputMode="decimal"
            min={
              metric === "weight" ? 35 : metric === "shoulder_width" ? 20 : 40
            }
            max={
              metric === "weight" ? 300 : metric === "shoulder_width" ? 80 : 250
            }
            step="0.01"
            value={values[metric]}
            disabled={busy}
            onChange={(e) =>
              setValues((prev) => ({ ...prev, [metric]: e.target.value }))
            }
          />
        </label>
      ))}
      {error && <p role="alert">{c.recordError}</p>}
      <button disabled={busy || !Object.values(values).some(Boolean)}>
        {busy ? c.loading : c.save}
      </button>
    </form>
  );
}
